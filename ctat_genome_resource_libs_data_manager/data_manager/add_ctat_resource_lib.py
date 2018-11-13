#!/usr/bin/env python
# ref: https://galaxyproject.org/admin/tools/data-managers/how-to/define/

# Written by H.E. Cicada Brokaw Dennis of Indiana University for the Broad Institute.
# Initial starting point was some code downloaded from the toolshed and
# other example code on the web.
# That code has however been extensively modified and augmented.

# This is part of Data Manager code to be used within a Galaxy.
# This Data Manager allows users to add entries to the ctat_genome_resource_libs table.

# This code allows downloading of a user selected Genome Reference Library
# from the CTAT Genome Resource Library website.
# It also provides for building libraries from source, doing a gmap_build over,
# and/or integrating mutation resources with, a Genome Reference Library.
# For more information on CTAT Genome Resource Libraries, 
# see https://github.com/FusionFilter/FusionFilter/wiki
# Users can create or download their own libraries and use this Data Manger to add them 
# if they don't want to add them by hand.

import sys
# The many calls to sys.stdout.flush() are done in order to get the output to be synchronized.
# Otherwise output from subprocesses can get streamed to stdout in a disjunct manner from 
# the output of the process running this code.
# This is particularly evident in the stdout stream when running within a Galaxy instance.
import argparse
import os
import shutil
import tarfile
import hashlib
import urllib
import urlparse
import contextlib
import subprocess

# One can comment out the following line when testing without galaxy package.
# In that case, also comment out the last line in main(). That is, the line that uses to_json_string.
from galaxy.util.json import to_json_string

# The following is not being used, but leaving here as info
# in case one ever wants to get input values using json.
# from galaxy.util.json import from_json_string
# However in this datamanager, the command line arguments are used instead.

# datetime.now() is used to create the unique_id
from datetime import datetime

# The Data Manager uses a subclass of HTMLParser to look through a web page's html 
# searching for the filenames within anchor tags.
import urllib2
from HTMLParser import HTMLParser

_CTAT_ResourceLib_URL = 'https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/'
_CTAT_Mutation_URL = 'https://data.broadinstitute.org/Trinity/CTAT/mutation/'
_CTAT_Build_dirname = 'ctat_genome_lib_build_dir'
_CTAT_MutationLibDirname = 'ctat_mutation_lib'
_CTAT_ResourceLib_DisplayNamePrefix = 'CTAT_GenomeResourceLib_'
_CTAT_ResourceLib_DefaultGenome = 'Unspecified_Genome'
_CTAT_HumanFusionLib_FilenamePrefix = 'CTAT_HumanFusionLib'
_CTAT_RefGenome_Filename = 'ref_genome.fa'
_CTAT_MouseGenome_Prefix = 'Mouse'
_CTAT_HumanGenome_Prefix = 'GRCh'
_COSMIC_Mutant_Filename = 'CosmicMutantExport.tsv.gz'
_COSMIC_Coding_Filename = 'CosmicCodingMuts.vcf.gz'

# FIX - The following numbers need to be checked and other numbers for gmap, etc. need to be determined.
# Values for each genome should be determined, so we can get more precise values for each genome.
_NumBytesNeededForSourceDataExtraction = 10737418240 # 10 Gigabytes. FIX - Not checked - Largest archive is currently 2.5GB.
_NumBytesNeededForPlugNPlayExtraction = 48318382080 # 45 Gigabytes. Largest archive is currently 28GB and extracts to 43GB.
# Built Human Genome archive (GRCh38_v27_CTAT_lib_Feb092018) with mutation lib is 46GB.
# Fix - double check what amount needed when the library is gmap'ed.
_NumBytesNeededForBuild = 66571993088 # 62 Gigabytes. FIX - This might not be correct.
_NumBytesNeededForMutationResources = 4294967296 # 4 Gigabytes. Actually need about 3.8GB.
# Once built the downloaded archive could be deleted to reduce the amount used, but with the archive
# there and the Cosmic files and the built ctat_mutation_library, 3.8GB is needed.
# If the archive files are deleted after the integration of the library, only 1.8GB would be used at that point.
# This program does not currently provide a method for deleting the mutation resource archive files.
_Write_TestFile = 'write_testfile.txt'
_DownloadSuccessFile = 'download_succeeded.txt'
_ExtractionSuccessFile = 'extraction_succeeded.txt'
_LibBuiltSuccessFile = 'build_succeeded.txt'
_GmapSuccessFile = 'gmap_succeeded.txt'
_MutationDownloadSuccessFile = 'mutation_download_succeeded.txt'
_MutationIntegrationSuccessFile = 'mutation_integration_succeeded.txt'
_LIBTYPE_SOURCE_DATA = 'source_data'
_LIBTYPE_PLUG_N_PLAY = 'plug-n-play'

class resumable_URL_opener(urllib.FancyURLopener):
    # This class is used to do downloads that can restart a download from
    # the point where it left off after a partial download was interupted.
    # This class and code using it was found online:
    # http://code.activestate.com/recipes/83208-resuming-download-of-a-file/
    # A sub-class is created in order to overide error 206. 
    # This error means a partial file is being sent,
    # which is ok in this case.  Do nothing with this error.
    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        pass
# End of class resumable_URL_opener

class FileListParser(HTMLParser):
    # The FileListParser object is used by get_ctat_genome_urls() and get_mutation_resource_urls(),
    # which can be called by the Data Manager interface (.xml file) to get
    # the filenames that are available online at broadinstitute.org
    # Apparently creating dynamic option lists this way is deprecated, but no
    # other method exists by which I can get the options dynamically from the web.
    # I believe that it is considered a security risk.

    # This HTMLParser facilitates getting url's of tar.gz links in an HTML page.
    # These are assumed to be files that can be downloaded and are the files we
    # are particularly interested in this Data Manager.
    def __init__(self):
        # Have to use direct call to super class rather than using super():
        # super(FileListParser, self).__init__()
        # because HTMLParser is an "old style" class and its inheritance chain does not include object.
        HTMLParser.__init__(self)
        self.urls = set()
    def handle_starttag(self, tag, attrs):
        # Look for filename references in anchor tags and add them to urls.
        if tag == "a":
            # The tag is an anchor tag.
            for attribute in attrs:
                # print "Checking: {:s}".format(str(attribute))
                if attribute[0] == "href":
                    # Does the href have a tar.gz in it?
                    if ("tar.gz" in attribute[1]) and ("md5" not in attribute[1]):
                        # Add the value to urls.
                        self.urls.add(attribute[1])            
# End of class FileListParser

def get_ctat_genome_urls():
    # open the url and retrieve the urls of the files in the directory.
    # If we can't get the list, send a default list.

    build_default_list = False
    default_url_filename = "GRCh38_v27_CTAT_lib_Feb092018.plug-n-play.tar.gz"
    resource = urllib2.urlopen(_CTAT_ResourceLib_URL)
    if resource is None:
        build_default_list = True
    else:
        theHTML = resource.read()
        if (theHTML is None) or (theHTML == ""):
            build_default_list = True
    if build_default_list:
        # These are the filenames for what was there at least until 2018/10/09.
        urls_to_return = set()
        urls_to_return.add("GRCh37_v19_CTAT_lib_Feb092018.plug-n-play.tar.gz")
        urls_to_return.add("GRCh37_v19_CTAT_lib_Feb092018.source_data.tar.gz")
        urls_to_return.add("GRCh38_v27_CTAT_lib_Feb092018.plug-n-play.tar.gz")
        urls_to_return.add("GRCh38_v27_CTAT_lib_Feb092018.source_data.tar.gz")
        urls_to_return.add("Mouse_M16_CTAT_lib_Feb202018.plug-n-play.tar.gz")
        urls_to_return.add("Mouse_M16_CTAT_lib_Feb202018.source_data.tar.gz")
    else:
        filelist_parser = FileListParser()
        filelist_parser.feed(theHTML)
        urls_to_return = filelist_parser.urls
        
    # For dynamic options need to return an itterable with contents that are tuples with 3 items.
    # Item one is a string that is the display name put into the option list.
    # Item two is the value that is put into the parameter associated with the option list.
    # Item three is a True or False value, indicating whether the item is selected.
    options = []
    found_default_url = False
    if len([item for item in urls_to_return if default_url_filename in item]) > 0:
        found_default_url = True
    for i, url in enumerate(filelist_parser.urls):
        # The urls should look like: 
        # https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/GRCh37_v19_CTAT_lib_Feb092018.plug-n-play.tar.gz
        # https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/Mouse_M16_CTAT_lib_Feb202018.source_data.tar.gz
        # But in actuality, they are coming in looking like:
        # GRCh37_v19_CTAT_lib_Feb092018.plug-n-play.tar.gz
        # Mouse_M16_CTAT_lib_Feb202018.source_data.tar.gz
        # Write code to handle both situations, or an ftp: url.
        url_parts = urlparse.urlparse(url)
        if (url_parts.scheme != ""):
            full_url_path = url
        else:
            # Assume the path is relative to the page location.
            full_url_path = os.path.join(_CTAT_ResourceLib_URL, url)
        filename = os.path.basename(url)
        if (found_default_url and (filename == default_url_filename)) or ((not found_default_url) and (i == 0)):
            # This should be the default option chosen.
            options.append((filename, full_url_path, True))
        else:
            options.append((filename, full_url_path, False))
    options.sort() # So the list will be in alphabetical order.
    # return a tuple of the urls
    print "The list being returned as options is:"
    print "{:s}\n".format(str(options))
    sys.stdout.flush()
    return options

def get_mutation_resource_urls():
    # FIX - Perhaps rather than letting the user choose a mutation resource url, 
    # should we download the correct one for the chosen library?
    # Not sure about this.
    # In that case we wouldn't provide a pull down interface that would call this.
    # FIX - 
    build_default_list = False
    resource = urllib2.urlopen(_CTAT_Mutation_URL)
    if resource is None:
        build_default_list = True
    else:
        theHTML = resource.read()
        if (theHTML is None) or (theHTML == ""):
            build_default_list = True
    if build_default_list:
        # These are the filenames for what was there at least until 2018/10/09.
        urls_to_return = set()
        urls_to_return.add("mutation_lib.hg19.tar.gz")
        urls_to_return.add("mutation_lib.hg38.tar.gz")
    else:
        filelist_parser = FileListParser()
        filelist_parser.feed(theHTML)
        urls_to_return = filelist_parser.urls
        
    # For dynamic options need to return an itterable with contents that are tuples with 3 items.
    # Item one is a string that is the display name put into the option list.
    # Item two is the value that is put into the parameter associated with the option list.
    # Item three is a True or False value, indicating whether the item is selected.
    options = []
    for i, url in enumerate(filelist_parser.urls):
        # The urls should look like: 
        # https://data.broadinstitute.org/Trinity/CTAT/mutation/mc7.tar.gz
        # https://data.broadinstitute.org/Trinity/CTAT/mutation/hg19.tar.gz
        # But in actuality, they are coming in looking like:
        # hg19.tar.gz
        # mc7.tar.gz
        #
        # On 2018/10/06, the following tar.gz files were present:
        # mutation_lib.hg19.tar.gz
        # mutation_lib.hg38.tar.gz
        # mc-7.tar.gz
        # ctat_mutation_demo.tar.gz	
        #
        # Write code to handle both situations, or an ftp: url.
        url_parts = urlparse.urlparse(url)
        if (url_parts.scheme != ""):
            full_url_path = url
        else:
            # Assume the path is relative to the page location.
            full_url_path = os.path.join(_CTAT_Mutation_URL, url)
        filename = os.path.basename(url)
        if (filename.split(".")[0] == "mutation_lib"):
            # As of 2018_10_09, the only ones supported have mutation_lib as the first part of the name.
            options.append((filename, full_url_path, i == 0))
    options.sort() # So the list will be in alphabetical order.
    # return a tuple of the urls
    print "The list being returned as options is:"
    print "{:s}\n".format(str(options))
    sys.stdout.flush()
    return options

# The following was used by the example program to get input parameters through the json.
# Just leaving here for reference.
# We are getting all of our parameter values through command line arguments.
#def get_reference_id_name(params):
#    genome_id = params['param_dict']['genome_id']
#    genome_name = params['param_dict']['genome_name']
#    return genome_id, genome_name
#
#def get_url(params):
#    trained_url = params['param_dict']['trained_url']
#    return trained_url

def print_directory_contents(dir_path, num_levels):
    # This procedure is used to help with debugging and for user information.
    if num_levels > 0:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print "\nDirectory {:s}:".format(dir_path)
            sys.stdout.flush()
            subprocess.call("ls -la {:s} 2>&1".format(dir_path), shell=True)
        else:
            print "Path either does not exist, or is not a directory:\n\t{:s}.".format(dir_path)
            sys.stdout.flush()
    if num_levels > 1:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            for filename in os.listdir(dir_path):
                filename_path = os.path.join(dir_path, filename)
                if os.path.exists(filename_path) and os.path.isdir(filename_path):
                    print_directory_contents(filename_path, num_levels-1)
        else:
            print "Path either does not exist, or is not a directory:\n\t{:s}.".format(dir_path)
            sys.stdout.flush()

def which(file):
    # This procedure is similar to the linux "which" command. 
    # It is used to find the location of an executable program that is in the PATH.
    # However this implementation does not check whether the program's file is executable.
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
            return os.path.join(path, file)
    return None

def size_of_file_at(file_url):
    # Returns the size of the file at file_url.
    # We have to open the file, in order to find out how big it is.
    file_retriever = resumable_URL_opener()
    with contextlib.closing(file_retriever.open(file_url)) as filelike_object:
       filesize = int(filelike_object.headers['Content-Length'])
    return filesize

def md5sum_for(filename, blocksize=2**20):
    # I got this code for this function off the web, but don't remember where.
    m = hashlib.md5()
    finished = False
    with open(filename, "rb" ) as f:
        while not finished:
            buf = f.read(blocksize)
            if buf:
                m.update( buf )
            else:
                finished = True
    return m.hexdigest()

def ctat_library_type(filepath):
    # This function pulls out the string indicating the library type of the file.
    # If the filename indicates source_data, as opposed to plug-n-play, 
    # then the library will have to be built after it is downloaded.
    base_filename = os.path.basename(filepath)
    library_type = base_filename.split(".")[1]
    #print "The file {:s}".format(base_filename)
    #print "is of type {:s}".format(library_type)
    return library_type

def find_genome_name_in_path(path, raise_error=False):
    # The form of the genome name in directory names (if present in the path) looks like:
    # GRCh37_v19_CTAT_lib_Feb092018
    # GRCh38_v27_CTAT_lib_Feb092018
    # Mouse_M16_CTAT_lib_Feb202018
    # When raise_error is True, a ValueError will be raised if there is no genome name in the given path.
    genome_name = None
    if (path is not None) and (path != ""):
        for element in path.split(os.sep):
            # print "Looking for genome name in {:s}.".format(element)
            if (element[0:len(_CTAT_MouseGenome_Prefix)] == _CTAT_MouseGenome_Prefix) \
                or (element[0:len(_CTAT_HumanGenome_Prefix)] == _CTAT_HumanGenome_Prefix):
                # Remove any extension that might be in the filename.
                genome_name = element.split(".")[0]
    if ((genome_name is None) or (genome_name == "")) and raise_error:
        raise ValueError("Cannnot find genome name in the given filename path:\n\t".format(path))
    return genome_name

def bytes_needed_to_extract(archive_filepath):
    # FIX -- The following should be replaced by a series of statements that return the right value for each archive.
    # The numbers used now estimates for the human genome, and so are big enough for the mouse genome, so ok for now.
    # FIX --
    bytes_needed = _NumBytesNeededForPlugNPlayExtraction
    if (ctat_library_type(archive_filepath) == _LIBTYPE_SOURCE_DATA):
        bytes_needed = _NumBytesNeededForSourceDataExtraction
    else:  # assume otherwise that it is a plug-n-play archive.
        bytes_needed = _NumBytesNeededForPlugNPlayExtraction
    return bytes_needed

def bytes_needed_to_build(source_data_filepath):
    # FIX - The following should be replaced by a series of statements that return the right value for each archive.
    # The numbers used now estimates that largest size needed. Also, it is probably not correct.
    return _NumBytesNeededForBuild

def create_success_file(full_file_path, contents=None):
    # full_file_path is the path to the file to write.
    #     It should not exist before calling this function,
    #     but if it does, it will be overwritten.
    # contents is some text that will be written into the file. 
    #     It can be empty and nothing will be written.
    try:
        with open(full_file_path,"w") as success_file:
            if contents is not None:
                success_file.write(contents)
            # else nothing is written into it, but we still will have created the file.
    except IOError:
        print "The success indication file could not be created: " + \
                    "{:s}".format(full_file_path)
        sys.stdout.flush()
        raise

def download_file_from_url(file_url, dest_dir, resume_download=True):
    # Some of the code used in this procedure was downloaded and modified for our needs.
    # That code was at: http://code.activestate.com/recipes/83208-resuming-download-of-a-file/
    # Given a file_url, downloads that file to dest_dir.
    # The url must specify a file to download, so I can grab the filename from the end of the url's path.
    # It is best to fully specify dest_dir. Otherwise the dest_dir will be opened relative to whatever cwd is.
    # If resume_download is True (the default), the function will attempt to resume the download where it left off,
    # if, for example, a previous download was interupted.
    # If resume_download is False, any existing download of the file is deleted and a new download is started.
    
    # DOWNLOAD_BLOCK_SIZE = 65536 # 64KB. Old number was 8192 or 8KB.
    DOWNLOAD_BLOCK_SIZE = 1048576 # 1 MB
    download_complete = False
    existing_size = 0
    bytes_read = 0
    file_retriever = resumable_URL_opener()
    dest_filename = os.path.basename(file_url)
    dest_fullpath = os.path.join(dest_dir, dest_filename)
    source_filesize = size_of_file_at(file_url)
    print "Downloading {:s}\nSize of the file is {:d}".format(file_url, source_filesize)
    print "Destination file for the download is {:s}".format(dest_fullpath)
    sys.stdout.flush()

    # If the file exists and resume_download is requested, then only download the remainder
    if resume_download and os.path.exists(dest_fullpath):
        existing_size = os.path.getsize(dest_fullpath)
        #If the file exists, but we already have the whole thing, don't download again
        print "The destination file exists and is {:d} bytes in size.".format(existing_size)
        if (source_filesize == existing_size):
            print "The file has already been completely downloaded:\n\t{:s}".format(dest_fullpath)
            download_complete = True
        else:
            header = "Range","bytes={:s}-".format(str(existing_size))
            print "Adding header to resume download:\n\t{:s}".format(header)
            file_retriever.addheader("Range","bytes={:s}-".format(str(existing_size)))
        # We open even if download is complete, to avoid adding code to determine whether to close.
        output_file = open(dest_fullpath,"ab")
    else:
        if os.path.exists(dest_fullpath):
            print "The destination file exists:\n\t{:s}".format(dest_fullpath)
            print "However a new download has been requested."
            print "The download will overwrite the existing file."
        else:
            print "The destination file does not exist yet."
        existing_size = 0
        output_file = open(dest_fullpath,"wb")
    sys.stdout.flush()

    try:
        # Check whether there is enough space on the device for the rest of the file to download.
        statvfs = os.statvfs(dest_dir)
        num_avail_bytes = statvfs.f_frsize * statvfs.f_bavail    
        # num_avail_bytes is the number of free bytes that ordinary users
        # are allowed to use (excl. reserved space)
        # Perhaps should subtract some padding amount from num_avail_bytes
        # rather than raising only if there is less than exactly what is needed.
        if (num_avail_bytes < (source_filesize-existing_size)):
            raise OSError("There is insufficient space ({:s} bytes)".format(str(num_avail_bytes)) + \
                          " on the device of the destination directory for the download: " + \
                          "{:s}".format(cannonical_destination))
        
        source_file = file_retriever.open(file_url)
        while not download_complete:
            data = source_file.read(DOWNLOAD_BLOCK_SIZE)
            if data:
                output_file.write(data)
                bytes_read = bytes_read + len(data)
            else:
                download_complete = True
        source_file.close()
    except IOError:
        print "Error while attempting to download {:s}".format(file_url)
        sys.stdout.flush()
        raise
    finally:
        output_file.close()
    
    for k,v in source_file.headers.items():
        print k, "=",v
    print "Downloaded {:s} bytes from {:s}".format(str(bytes_read), str(file_url))
    dest_filesize = os.path.getsize(dest_fullpath)
    print "{:s} {:s}".format(str(dest_filesize), str(dest_fullpath))
    sys.stdout.flush()
    if source_filesize != dest_filesize:
        raise IOError("Download error:\n\t" + \
            "The source file\n\t\t{:d}\t{:s}\n\t".format(source_filesize, file_url) + \
            "and the destination file\n\t\t{:d}\t{:s}\n\t".format(dest_filesize, dest_fullpath) + \
            "are different sizes.")
    return dest_fullpath

def ensure_we_can_write_numbytes_to(destination, numbytes):
    # Attempts to create the destination directory if it does not exist.
    # Tests whether a file can be written to that directory.
    # Tests whether there is numbytes space on the device of the destination.
    # Raises errors if it cannot do any of the above.
    #
    # Returns the full specification of the destination path. 
    # We want to make sure that destination is an absolute fully specified path.
    cannonical_destination = os.path.realpath(destination)
    if os.path.exists(cannonical_destination):
        if not os.path.isdir(cannonical_destination):
            raise ValueError("The destination is not a directory: " + \
                             "{:s}".format(cannonical_destination))
        # else all is good. It is a directory.
    else:
        # We need to create it since it does not exist.
        try:
            os.makedirs(cannonical_destination)
        except os.error:
            print "ERROR: Trying to create the following directory path:"
            print "\t{:s}".format(cannonical_destination)
            sys.stdout.flush()
            raise
    # Make sure the directory now exists and we can write to it.
    if not os.path.exists(cannonical_destination):
        # It should have been created, but if it doesn't exist at this point
        # in the code, something is wrong. Raise an error.
        raise OSError("The destination directory could not be created: " + \
                      "{:s}".format(cannonical_destination))
    test_writing_filename = "{:s}.{:s}".format(os.path.basename(cannonical_destination), _Write_TestFile)
    test_writing_filepath = os.path.join(cannonical_destination, test_writing_filename)
    try:
        with open(test_writing_filepath, "w") as test_writing_file:
            test_writing_file.write("Testing writing to this file.")
        if os.path.exists(test_writing_filepath):
            os.remove(test_writing_filepath)
    except IOError:
        print "The destination directory could not be written into:\n\t" + \
              "{:s}".format(cannonical_destination)
        sys.stdout.flush()
        raise
    # Check whether there are numbytes available on cannonical_destination's device.
    statvfs = os.statvfs(cannonical_destination)
    # fs_size = statvfs.f_frsize * statvfs.f_blocks          # Size of filesystem in bytes
    # num_free_bytes = statvfs.f_frsize * statvfs.f_bfree    # Actual number of free bytes
    num_avail_bytes = statvfs.f_frsize * statvfs.f_bavail    # Number of free bytes that ordinary users
                                                             # are allowed to use (excl. reserved space)
    if (num_avail_bytes < numbytes):
        raise OSError("There is insufficient space ({:s} bytes)".format(str(num_avail_bytes)) + \
                        " on the device of the destination directory:\n\t" + \
                        "{:s}\n\t{:d} bytes are needed.".format(cannonical_destination, numbytes))

    return cannonical_destination

def download_genome_archive(source_url, destination, force_new_download=False):
    # This function downloads but does not extract the archive at source_url.
    # This function can be called on a file whose download was interrupted, and if force_new_download
    # is False, the download will proceed where it left off.
    # If download does not succeed, an IOError is raised.
    # The function checks whether there is enough space at the destination for the expanded library.
    # It raises an OSError if not.
    # ValueError can also be raised by this function.
    
    # Input Parameters
    # source_url is the full URL of the file we want to download.
    #     It should look something like:
    #     https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/GRCh37_v19_CTAT_lib_Feb092018.plug-n-play.tar.gz
    #     If only the filename is given, it is assumed to reside at _CTAT_ResourceLib_URL.
    # destination is the location (directory) where a copy of the source file will be placed.
    #     Relative paths are expanded using the current working directory, so within Galaxy,
    #     it is best to send in absolute fully specified path names so you know to where
    #     the source file is going to be copied.
    # force_new_download if True, will cause a new download to occur, even if the file has been downloaded previously.
    #
    # Returns the canonical path to the file that was downloaded.
    
    dest_fullpath = None
    url_parts = urlparse.urlparse(source_url)
    source_filename = os.path.basename(url_parts.path)
    if url_parts.scheme == "":
        # Then we were given a source_url without a leading https: or similar.
        # Assume we only were given the filename and that it exists at _CTAT_ResourceLib_URL.
        source_url = urlparse.urljoin(_CTAT_ResourceLib_URL, source_url)
    # FIX - We might want to otherwise check if we have a valid url and/or if we can reach it.
    
    print "Downloading:\n\t{:s}".format(str(source_url))
    print "to:\n\t{:s}".format(destination)
    sys.stdout.flush()
    # The next is done so that if the source_url does not have a genome name in it, an error will be raised.
    find_genome_name_in_path(source_url, raise_error=True)
    cannonical_destination = ensure_we_can_write_numbytes_to(destination, size_of_file_at(source_url))
    
    # Get the list of files in the directory,
    # We use it to check for a previous download.
    orig_files_in_destdir = set(os.listdir(cannonical_destination))
    # See whether the file has been downloaded already.
    download_success_filename = "{:s}.{:s}".format(source_filename, _DownloadSuccessFile)
    download_success_full_file_path = os.path.join(cannonical_destination, download_success_filename)
    if ((download_success_filename not in orig_files_in_destdir) \
        or force_new_download):    
        if (download_success_filename in orig_files_in_destdir):
            # Since we are redoing the download, 
            # the success file needs to be removed
            # until the download has succeeded.
            os.remove(download_success_full_file_path)
        # The following raises an error if the download fails for some reason.
        dest_fullpath = download_file_from_url(source_url, cannonical_destination, \
                                               resume_download=(not force_new_download))
        # Check the md5sum of the cannonical_destination file to ensure the data in the file is correct.
        file_retriever = resumable_URL_opener()
        md5_url = "{:s}.md5".format(source_url)
        print "Checking the md5sum of the downloaded file."
        try:
            md5_file = file_retriever.open(md5_url, "r")
            md5sum_from_web = md5_file.readlines()[0].strip().split()[0]
            md5_file.close()
            md5sum_from_file = md5sum_for(dest_fullpath)
        except IOError:
            print "Error while attempting to check the md5sum for {:s}".format(dest_fullpath)
            sys.stdout.flush()
            raise        
        if md5sum_from_web != md5sum_from_file:
            raise IOError("Download error:\n\t" + \
                          "The md5 sum for\n\t\t({:s})\n\t".format(dest_fullpath) + \
                          "does not match the value read from the web:\n\t\t" + \
                          "({:s} != {:s})".format(md5sum_from_file, md5sum_from_web))
        print "Check of md5sum succeeded."
        create_success_file(download_success_full_file_path, \
                            "Download of:\n\t{:s}\n".format(source_url) + \
                            "to:\n\t{:s}\nsucceeded.".format(dest_fullpath))
    elif download_success_filename in orig_files_in_destdir:
        print "The download success file exists, so no download is being attempted:"
        print "\t{:s}".format(download_success_full_file_path)
        print "Remove the file or set <Force New Download> if you want a new download to occur."
        dest_filename = os.path.basename(source_url)
        dest_fullpath = os.path.join(cannonical_destination, dest_filename)
    else:
        print "download_genome_archive(): This code should never be printed. Something is wrong."
    sys.stdout.flush()

    # Some code to help us if errors occur.
    print "\n*******************************"
    print "*      Finished download.     *"
    sys.stdout.flush()
    print_directory_contents(cannonical_destination, 1)
    print "*******************************\n"
    sys.stdout.flush()
    
    return dest_fullpath

def extract_archive(archive_filepath, destination, force_new_extraction=False):
    # Generic function will use tarfile object to extract the given archive_filepath
    # to the destination. If a file indicating a previous successful extraction exists
    # the file is not extracted again unless force_new_extraction is True.
    # This procedure does not write the extraction success file, because some error checking
    # is dependant on the file being extracted. The calling procedure can/should write the 
    # success file after doing error checking.
    cannonical_destination = ensure_we_can_write_numbytes_to(destination, bytes_needed_to_extract(archive_filepath))
    
    # Create the name of the file used to indicate prior success of the file's extraction.
    extraction_success_filename = "{:s}.{:s}".format(os.path.basename(archive_filepath), _ExtractionSuccessFile)
    extraction_success_full_file_path = os.path.join(cannonical_destination, extraction_success_filename)
    #print "extraction_success_filename is {:s}".format(extraction_success_filename)
    
    orig_files_in_destination = set(os.listdir(cannonical_destination))
    if ((extraction_success_filename not in orig_files_in_destination) \
        or force_new_extraction):
        # Do the extraction.
        if (extraction_success_filename in orig_files_in_destination):
            # Since we are redoing the extraction, 
            # the success file needs to be removed
            # until the extraction has succeeded.
            os.remove(extraction_success_full_file_path)
        with tarfile.open(archive_filepath, mode="r:*") as archive_file:
            archive_file.extractall(path=cannonical_destination)
    elif (extraction_success_filename in orig_files_in_destination):
        # The archive was successfully extracted before so we do not do it again.
        print "The extraction success file exists, so no new extraction was attempted:"
        print "\t{:s}".format(extraction_success_full_file_path)
        print "Remove the success file or set <force new extraction> if you want a new extraction to occur."
    else:
        print "extract_archive(): This code should never be printed. Something is wrong."
    sys.stdout.flush()
    
    # Some code to help us if errors occur.
    print "\n*******************************************************"
    print "* Finished extraction. Destination directory listing. *"
    sys.stdout.flush()
    print_directory_contents(cannonical_destination, 1)
    print "*******************************************************\n"
    sys.stdout.flush()
    return

def extract_genome_file(archive_filepath, destination, force_new_extraction=False, keep_archive=False):
    # Extract a CTAT Genome Reference Library archive file.
    # It is best if archive_filepath is an absolute, fully specified filepath, not a relative one.
    # destination is the directory to which the archive will be extracted.
    # force_new_extraction can be used to cause extraction to occur, even if the file was extracted before.
    #
    # Returns extracted_directory
    #     The full path of the top level directory that is 
    #     created by the extraction of the files from the archive.

    print "Extracting:\n\t {:s}".format(str(archive_filepath))
    print "to:\n\t{:s}".format(destination)
    sys.stdout.flush()
    cannonical_destination = ensure_we_can_write_numbytes_to(destination, bytes_needed_to_extract(archive_filepath))
    # Get the root filename of the Genome Directory from the source file's name. 
    # That should also be the name of the extracted directory.
    genome_dirname = find_genome_name_in_path(archive_filepath, raise_error=True)
        
    orig_files_in_destination = set(os.listdir(cannonical_destination))
    extract_archive(archive_filepath, destination, force_new_extraction)
    newfiles_in_destdir = set(os.listdir(cannonical_destination)) - orig_files_in_destination

    if (genome_dirname not in newfiles_in_destdir):
        # Perhaps it has a different name than what we expect it to be.
        # It will be a sub-directory that was not in the directory
        # before we did the download and extraction.
        found_filename = None
        if len(newfiles_in_destdir) == 1:
            found_filename = newfiles_in_destdir[0]
        else:
            for filename in newfiles_in_destdir:
                # In most cases, there will only be one new file, but some OS's might have created
                # other files in the directory.
                # Look for the directory that was downloaded and extracted.
                # The correct file's name should be a substring of the tar file that was downloaded.
                if filename in src_filename:
                    # make sure it is a directory
                    if os.path.isdir(os.path.join(cannonical_destination,filename)):
                        found_filename = filename
        if found_filename is not None:
            genome_dirname = found_filename

    extracted_directory = os.path.join(cannonical_destination, genome_dirname)
    if (os.path.exists(extracted_directory)):
        # Create the name of the file used to indicate prior success of the file's extraction.
        extraction_success_filename = "{:s}.{:s}".format(os.path.basename(archive_filepath), _ExtractionSuccessFile)
        extraction_success_full_file_path = os.path.join(cannonical_destination, extraction_success_filename)
        create_success_file(extraction_success_full_file_path, \
                            "Extraction of:\n\t{:s}\n".format(archive_filepath) + \
                            "to:\n\t{:s}\nsucceeded.".format(extracted_directory))
    else:
        raise ValueError("ERROR: Could not find the extracted directory in the destination directory:" + \
                             "\n\t{:s}".format(cannonical_destination))
    if not keep_archive:
        # We are done extracting, so remove the archive file.
        if os.path.exists(archive_filepath):
            print "Removing the archive file:\n\t{:s}".format(archive_filepath)
            sys.stdout.flush()
            os.remove(archive_filepath)
        # else: # It was removed previously, so we don't need to remove it again.
    return extracted_directory

def get_gmap_success_filename(genome_build_directory):
    # This function was created because there are two places where the success_filename was being created.
    # Using this function makes sure that the names being used are the same.
    # FIX - We could use a static string like "gmap_build" as the first part of the name, 
    #     rather than the genome name, and maybe that would be more logical. 
    #     The name in that case would not be different in different libraries.
    #     Leaving for now because I don't want to do another round of testing.
    genome_name = find_genome_name_in_path(genome_build_directory)
    if genome_name is None:
        genome_name = os.path.basename(genome_build_directory)
    return "{:s}.{:s}".format(genome_name, _GmapSuccessFile)

def gmap_the_library(genome_build_directory, force_new_gmap=False):
    # This is the processing that needs to happen for the ctat_gmap_fusion tool to work.
    # genome_build_directory should normally be a fully specified path, 
    # though this function should work even if it is relative.
    # The gmap_build command prints messages out to stderr, even when there is not an error,
    # so I route stderr to stdout.
    
    # Create the name of the file used to indicate prior success of gmap.
    gmap_success_filename = get_gmap_success_filename(genome_build_directory)
    gmap_success_full_file_path = os.path.join(genome_build_directory, gmap_success_filename)
	    
    orig_files_in_build_dir = set(os.listdir(genome_build_directory))
    if ((gmap_success_filename not in orig_files_in_build_dir) \
        or force_new_gmap):
        # Do the gmap.
        if (gmap_success_filename in orig_files_in_build_dir):
            # Since we are redoing the gmap, 
            # the success file needs to be removed
            # until the gmap has succeeded.
            os.remove(gmap_success_full_file_path)
        command = "gmap_build -D {:s}/ -d ref_genome.fa.gmap -k 13 {:s}/ref_genome.fa 2>&1".format( \
        	   genome_build_directory, genome_build_directory)
        print "Doing a gmap_build with the following command:\n\t{:s}\n".format(command)
        sys.stdout.flush()
        try: # to send the gmap_build command.
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError:
            print "ERROR: While trying to run the gmap_build command on the library:\n\t{:s}".format(command)
            sys.stdout.flush()
            raise
        finally:
            sys.stdout.flush()
            # Some code to help us if errors occur.
            print "\n*******************************\nAfter running gmap_build."
            sys.stdout.flush()
            print_directory_contents(genome_build_directory, 2)
            print "*******************************\n"
            sys.stdout.flush()
        create_success_file(gmap_success_full_file_path, \
                    "gmap of:\n\t{:s}\nsucceeded.".format(genome_build_directory))
    elif gmap_success_filename in orig_files_in_build_dir:
        print "The gmap success file exists, so no gmap is being attempted:"
        print "\t{:s}".format(gmap_success_full_file_path)
        print "Remove the file or set <force new gmap> if you want a new gmap to occur."
    else:
        print "gmap_the_library(): This code should never be printed. Something is wrong."
    sys.stdout.flush()
    return


def build_the_library(genome_source_directory, \
                      genome_build_directory, force_new_build=False, \
                      gmap_build=False, force_gmap_build=False):
    """ genome_source_directory is the location of the source_data needed to build the library.
        Normally it is fully specified, but could be relative.
        genome_build_directory is the location where the library will be built.
        It can be relative to the current working directory or an absolute path.
        build specifies whether to run prep_genome_lib.pl even if it was run before.
		gmap_build specifies whether to run gmap_build or not.
        The prep_genome_lib.pl command can send messages out to stderr, even when there is not an error,
        so I route stderr to stdout.

		Following was the old way to do it. Before FusionFilter 0.5.0.
		prep_genome_lib.pl \
		   --genome_fa ref_genome.fa \
		   --gtf ref_annot.gtf \
		   --blast_pairs blast_pairs.gene_syms.outfmt6.gz \
		   --fusion_annot_lib fusion_lib.dat.gz
		   --output_dir ctat_genome_lib_build_dir
		index_pfam_domain_info.pl  \
		    --pfam_domains PFAM.domtblout.dat.gz \
		    --genome_lib_dir ctat_genome_lib_build_dir
		gmap_build -D ctat_genome_lib_build_dir -d ref_genome.fa.gmap -k 13 ctat_genome_lib_build_dir/ref_genome.fa"
    """

    if (genome_source_directory is None) or (genome_source_directory == "" ) or not os.path.exists(genome_source_directory):
        raise ValueError("Cannot build the CTAT Genome Resource Library. " + \
                         "The source directory does not exist:\n\t{:s}".format(str(genome_source_directory)))
    cannonical_destination = ensure_we_can_write_numbytes_to(genome_build_directory, \
                                                             bytes_needed_to_build(genome_source_directory))
    print "Building the CTAT Genome Resource Library from source data at:\n\t{:s}".format(str(genome_source_directory))
    print "The Destination directory is at:\n\t{:s}".format(str(cannonical_destination))
    sys.stdout.flush()
    
    # Get the root filename of the Genome Directory.
    src_filename = os.path.basename(genome_source_directory)
    # See whether the library has been built already. The success file is written into the source directory.
    files_in_sourcedir = set(os.listdir(genome_source_directory))
    build_success_filename = "{:s}.{:s}".format(src_filename, _LibBuiltSuccessFile)
    build_success_file_path = os.path.join(genome_source_directory, build_success_filename)
    if (build_success_filename not in files_in_sourcedir) or force_new_build:
        os.chdir(genome_source_directory)
        if (build_success_filename in files_in_sourcedir):
            # Since we are redoing the build, 
            # the success file needs to be removed
            # until the build has succeeded.
            os.remove(build_success_file_path)
        # Create the command that builds the Genome Resource Library form the source data.
        command = "prep_genome_lib.pl --genome_fa ref_genome.fa --gtf ref_annot.gtf " + \
        	   "--pfam_db PFAM.domtblout.dat.gz " + \
        	   "--output_dir {:s} ".format(cannonical_destination)
        found_HumanFusionLib = False
        HumanFusionLib_filename = "NoFileFound"
        for filename in os.listdir(genome_source_directory):
            # At the time this was written, the filename was CTAT_HumanFusionLib.v0.1.0.dat.gz
            # We only check the prefix, in case other versions are used later.
            # I assume there is only one in the directory, but if there are more than one, 
            # the later one, alphabetically, will be used.
            if filename.split(".")[0] == _CTAT_HumanFusionLib_FilenamePrefix:
        	found_HumanFusionLib = True
        	filename_of_HumanFusionLib = filename
        if found_HumanFusionLib:
            # The mouse genomes do not have a fusion_annot_lib
            # so only add the following for Human genomes.
            command += "--fusion_annot_lib {:s} ".format(filename_of_HumanFusionLib) + \
        	       "--annot_filter_rule AnnotFilterRule.pm "
        if gmap_build:
            command += "--gmap_build "
        # Send stderr of the command to stdout, because some functions may write to stderr,
        # even though no error has occurred. We will depend on error code return in order
        # to know if an error occurred.
        command += " 2>&1"
        print "About to run the following command:\n\t{:s}".format(command)
        sys.stdout.flush()
        try: # to send the prep_genome_lib command.
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError:
            print "ERROR: While trying to run the prep_genome_lib.pl command " + \
                  "on the CTAT Genome Resource Library:\n\t{:s}".format(command)
            raise
        finally:
            # Some code to help us if errors occur.
            print "\n*******************************"
            print "Contents of Genome Source Directory {:s}:".format(genome_source_directory)
            sys.stdout.flush()
            print_directory_contents(genome_source_directory, 2)
            print "\nContents of Genome Build Directory {:s}:".format(cannonical_destination)
            sys.stdout.flush()
            print_directory_contents(cannonical_destination, 2)
            print "*******************************\n"
            sys.stdout.flush()
        create_success_file(build_success_file_path, \
                            "Build of:\n\t{:s}\n".format(genome_source_directory) + \
                            "to:\n\t{:s}\nsucceeded.".format(cannonical_destination))
        if gmap_build:
            # Create the gmap success file.
            gmap_success_filename = get_gmap_success_filename(cannonical_destination)
            gmap_success_full_file_path = os.path.join(cannonical_destination, gmap_success_filename)
            create_success_file(gmap_success_full_file_path, \
                                "gmap of:\n\t{:s}\nsucceeded.".format(cannonical_destination))
    elif (build_success_filename in files_in_sourcedir):
        print "The build success file exists, so no build is being attempted:"
        print "\t{:s}".format(build_success_file_path)
        print "Remove the file or set <force new build> if you want a new build to occur."
        # We might still need to do a gmap_build.
        if gmap_build:
            print "Checking if we need to gmap the library."
            sys.stdout.flush()
            gmap_the_library(cannonical_destination, force_gmap_build)
            sys.stdout.flush()
            # gmap_the_library creates a gmap success file if it succeeds.
    else:
        print "build_the_library(): This code should never be printed. Something is wrong."
    sys.stdout.flush()
    return
	# End of build_the_library()

def find_path_to_mutation_lib_integration():
    # We are assuming that we exist inside of a conda environment and that the directory that we want
    # is in the share directory, one level up from the bin directory that contains the ctat_mutations
    # command.
    path_to_mutation_lib_integration = None
    path_to_ctat_mutations = which("ctat_mutations")
    if (path_to_ctat_mutations is None) or (path_to_ctat_mutations == ""):
        raise ValueError("Unable to find ctat_mutations, which is required to do mutation resource processing.")
    conda_root_dir = os.path.dirname(os.path.dirname(path_to_ctat_mutations))
    share_dir = os.path.join(conda_root_dir, "share")
    ctat_mutations_dir = None
    for filename in os.listdir(share_dir):
        if "ctat-mutations" in filename:
            ctat_mutations_dir = filename
    if (ctat_mutations_dir is None) or (ctat_mutations_dir == ""):
        raise ValueError("Unable to find the home of ctat_mutations.\n" + \
                         "It should be in the share directory:\n\t{:s}.".format(share_dir))
    path_to_mutation_lib_integration = os.path.join(share_dir, \
							    ctat_mutations_dir, \
							    "mutation_lib_prep", \
							    "ctat-mutation-lib-integration.py")
    return path_to_mutation_lib_integration

def find_path_to_picard_home():
    picard_home = None
    path_to_ctat_mutations = which("ctat_mutations")
    if (path_to_ctat_mutations is None) or (path_to_ctat_mutations == ""):
        raise ValueError("Unable to find ctat_mutations, which is required to do mutation resources processing.")
    # The ctat_mutations shell script defines PICARD_HOME. We just need to get it out of that file.
    ctat_mutations_file = open(path_to_ctat_mutations, "r")
    for line in ctat_mutations_file:
        if ("export" in line) and ("PICARD_HOME=" in line):
            # Get the value after the equal sign and strip off the newline at the end of string.
            # Then strip off quotes at begin and end if they are there.
            # And then strip off any other whitespace that might have been inside of stripped off quotes.
            picard_home = line.split("=")[1].strip().strip('\"').strip()
    if (picard_home is None) or (picard_home == ""):
        # We didn't find it in the ctat_mutations file. Search for it.
        conda_root_dir = os.path.dirname(os.path.dirname(path_to_ctat_mutations))
        share_dir = os.path.join(conda_root_dir, "share")
        for filename in os.listdir(share_dir):
            if "picard" in filename:
                picard_home = os.path.join(share_dir,filename)
        if (picard_home is None) or (picard_home == ""):
            raise ValueError("Unable to find PICARD_HOME.\n" +
                             "It should be in the share directory:\n\t{:s}.".format(share_dir))
    return picard_home
	    
def download_and_integrate_mutation_resources(source_url, genome_build_directory, cosmic_resources_location=None, \
                                              force_new_download=False, force_new_integration=False):
    # source_url is the url of the mutation resources archive to download.
    # genome_build_dir is the location where the archive will be placed.
    # If cosmic_files_location is set, that is the location where the files are presumed to exist.
    # If cosmic_files_location is not set, the files will be assumed to exist in genome_build_directory.
    # If force_new_download is True, then even if the archive has previously been downloaded,
    # it will be downloaded again.
    # If force_new_integration is True, the resources will be integrated again, even if there has been a
    # a previous successful integration.
    # The ctat-mutation-lib-integration command may print messages out to stderr, even when there is not an error.
    # FIX - However, I forgot to route stderr to stdout as I did with other commands.
    #     I have left it this way for now because I do not want to do another round of testing.
    """
    From https://github.com/NCIP/ctat-mutations/tree/master/mutation_lib_prep
	    
    Step 1 (after CTAT Genome Resource Library is built)
    download mutation_lib.hg38.tar.gz into GRCh38_v27_CTAT_lib_Feb092018
    or 
    download mutation_lib.hg19.tar.gz into GRCh37_v19_CTAT_lib_Feb092018
    (mouse genome is not yet supported)

    Step 2: Cosmic files download - User must perform this step prior to running this code. We check if files are present.

    Next download COSMIC resources required in this directory. Depending on the version of genome you need you can install either COSMIC's hg38 or COSMIC's hg19. You will need to download 2 sets of files: COSMIC Mutation Data (CosmicMutantExport.tsv.gz) and COSMIC Coding Mutation VCF File (CosmicCodingMuts.vcf.gz). Please note, for download to succeed you will need to register and login to their service.

    So is there a way the user can give their credentials through the Data Manager interface as a part of specifying Mutation parameters and then I can programatically use those credentials to download the file, or maybe instead, the interface needs to have the intructions for the user to download the files, then the use needs to specify the absolute path to where those files are.

    Step 3: Mutation lib integration

    Once you have downloaded CosmicMutantExport.tsv.gz AND CosmicCodingMuts.vcf.gz (hg38 or hg19), proceed with mutation lib integration step which will integrate the mutation resource with CTAT_GENOME_LIB (This corresponds to "GRCh37_v19_CTAT_lib_Feb092018" or "GRCh38_v27_CTAT_lib_Feb092018" downloaded in Step 1). You will find this script in ctat-mutations repo in 'src' directory.

    #Keep Picard in PICARD_HOME environmental variable like so
    export PICARD_HOME=/path/to/picard

    #Integrate CTAT mutations lib with CTAT genome library
    python ctat-mutations/mutation_lib_prep/ctat-mutation-lib-integration.py \
		 --CosmicMutantExport CosmicMutantExport.tsv.gz \
		 --CosmicCodingMuts CosmicCodingMuts.vcf.gz \
		 --genome_lib_dir GRCh37_v19_CTAT_lib_Feb092018/ # OR GRCh38_v27_CTAT_lib_Feb092018/

    Now you are all set to run the ctat-mutations pipeline
    """
    print "\n***********************************"
    print "* Integrating Mutation Resources. *"
    print "***********************************\n"
    sys.stdout.flush()
    # It is assumed that this procedure is only called with a valid genome_build_directory.
    url_parts = urlparse.urlparse(source_url)
    source_filename = os.path.basename(url_parts.path)
    if url_parts.scheme == "":
        # Then we were given a source_url without a leading https: or similar.
        # Assume we only were given the filename and that it exists at _CTAT_Mutation_URL.
        source_url = urlparse.urljoin(_CTAT_Mutation_URL, source_url)
    # FIX - We might want to otherwise check if we have a valid url and/or if we can reach it.
    cannonical_destination = ensure_we_can_write_numbytes_to(genome_build_directory, _NumBytesNeededForMutationResources)
    print "Download and Integrate a Mutation Resource Archive."
    print "The source URL is:\n\t{:s}".format(str(source_url))
    print "The destination is:\n\t{:s}".format(str(cannonical_destination))
    sys.stdout.flush()
    # Get the list of files in the directory,
    # We use it to check for a previous download or extraction among other things.
    orig_files_in_destdir = set(os.listdir(cannonical_destination))

    # DOWNLOAD SECTION
    # See whether the index file has been downloaded already.
    download_success_file = "{:s}.{:s}".format(source_filename, _MutationDownloadSuccessFile)
    download_success_file_path = os.path.join(cannonical_destination, download_success_file)
    if ((download_success_file not in orig_files_in_destdir) or force_new_download):
        # DO THE DOWNLOAD
        if (download_success_file in orig_files_in_destdir):
            # Since we are redoing the download, 
            # the success file needs to be removed
            # until the download has succeeded.
            os.remove(download_success_file_path)
        # The following raises an IOError if the download fails for some reason.
        archive_fullpath = download_file_from_url(source_url, cannonical_destination, resume_download=(not force_new_download))
        create_success_file(download_success_file_path, \
                        "Download of the mutation resource archive:\n\t{:s}\n".format(source_url) + \
                        "to:\n\t{:s}\nsucceeded.".format(cannonical_destination))
    elif (download_success_file in orig_files_in_destdir):
        print "The download success file exists, so no download is being attempted:"
        print "\t{:s}".format(download_success_file_path)
        print "Remove the file or set <new_mutation_download> if you want a new download to occur."
    else:
        print "download_and_integrate_mutation_resources() - Download: This code should never be printed. Something is wrong."
    sys.stdout.flush()
    
    # INTEGRATION SECTION
    integration_success_file = "{:s}.{:s}".format(source_filename, _MutationIntegrationSuccessFile)
    integration_success_file_path = os.path.join(cannonical_destination, integration_success_file)
    if ((integration_success_file not in orig_files_in_destdir) or force_new_integration):
        # INTEGRATE THE LIBRARY
        if (integration_success_file in orig_files_in_destdir):
            # Since we are redoing the integration, 
            # the success file needs to be removed
            # until the download has succeeded.
            os.remove(integration_success_file_path)
        mutation_lib_dirpath = os.path.join(cannonical_destination, _CTAT_MutationLibDirname)
        # If we do not remove the directory, then the old files will exist and a new integration does not occur.
        # Also, with the Cosmic files, when the integrated file is created, if there is a previous one, gzip
        # asks a question of the user, and this program is not prepared to respond to a question from a subprocess:
        #     [bgzip] /path/to/ctat_mutation_lib/cosmic.vcf.gz already exists; do you wish to overwrite (y or n)?
        if os.path.exists(mutation_lib_dirpath):
            shutil.rmtree(mutation_lib_dirpath)
        # Check for Cosmic resources. User has to place these files into the correct location.
        if (cosmic_resources_location is None) or (cosmic_resources_location == ""):
            cosmic_resources_loc_full_path = cannonical_destination
            end_err_msg = "These files must be placed into:\n\t{:s}".format(cosmic_resources_loc_full_path)
        else:
            cosmic_resources_loc_full_path = os.path.realpath(cosmic_resources_location)
            end_err_msg = "This function was told they would be placed into:\n\t{:s}".format(cosmic_resources_loc_full_path)
        cosmic_mutant_full_path = os.path.join(cosmic_resources_loc_full_path, _COSMIC_Mutant_Filename)
        cosmic_coding_full_path = os.path.join(cosmic_resources_loc_full_path, _COSMIC_Coding_Filename)
        if not (os.path.exists(cosmic_mutant_full_path) and os.path.exists(cosmic_coding_full_path)):
            raise IOError("Either one or both of Cosmic Resources are missing:\n\t" + \
                          "{:s}\nand/or\n\t{:s}\n".format(cosmic_mutant_full_path, cosmic_coding_full_path) + \
                          "Unable to integrate mutation resources.\n{:s}".format(end_err_msg))
        # Create the integration command. We also must define PICARD_HOME for the command to work.
        picard_home = find_path_to_picard_home()
        integration_command = find_path_to_mutation_lib_integration()
        command = "export PICARD_HOME={:s} && python {:s} ".format(picard_home, integration_command) + \
                  "--CosmicMutantExport {:s} ".format(cosmic_mutant_full_path) + \
                  "--CosmicCodingMuts {:s} ".format(cosmic_coding_full_path) + \
                  "--genome_lib_dir {:s}".format(cannonical_destination)
        try: # to send the ctat-mutation-lib-integration command.
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError:
            print "ERROR: While trying to integrate the mutation resources:\n\t{:s}".format(command)
            sys.stdout.flush()
            raise
        finally:
            # Some code to help us if errors occur.
            print "/n*********************************************************"
            print "* After download and integration of Mutation Resources. *"
            sys.stdout.flush()
            print_directory_contents(cannonical_destination, 2)
            print "*********************************************************\n"
            sys.stdout.flush()
        create_success_file(integration_success_file_path, \
                        "Download and integration of mutation resources:\n\t{:s}\n".format(source_url) + \
                        "to:\n\t{:s}\nsucceeded.".format(genome_build_directory))
    elif (integration_success_file in orig_files_in_destdir):
        print "The mutation resources integration success file exists, so no integration is being attempted:"
        print "\t{:s}".format(integration_success_file_path)
        print "Remove the file or set <new_mutation_integration> if you want a new integration to occur."
    else:
        print "download_and_integrate_mutation_resources() - Integration: This code should never be printed. Something is wrong."
    sys.stdout.flush()
    return

def search_for_genome_build_dir(top_dir_path):
    # If we do not download the directory, the topdir_path could be the
    # location of the genome resource library, but we also want to allow the
    # user to give the same value for top_dir_path that they do when a
    # build happens, so we need to handle all three cases:
    # 1) Is the top_dir_path the build directory,
    # 2) or is it inside of the given directory, 
    # 3) or is it inside a subdirectory of the given directory.
    # The source_data downloads are built to a directory named _CTAT_Build_dirname,
    # and the plug-n-play downloads contain a directory with a single sub-directory named _CTAT_Build_dirname.
    # So the conventional structure has all the library files in .../GenomeName/_CTAT_Build_dirname
    
    top_dir_full_path = os.path.realpath(top_dir_path)
    genome_build_directory = None
    genome_name_from_dirname = None
    print_warning = False

    if not os.path.exists(top_dir_full_path):
        raise ValueError("Cannot find the CTAT Genome Resource Library. " + \
            "The given directory does not exist:\n\t{:s}".format(top_dir_full_path))
    elif not os.path.isdir(top_dir_full_path):
        raise ValueError("Cannot find the CTAT Genome Resource Library. " + \
            "The given directory is not a directory:\n\t{:s}".format(top_dir_full_path))
    if os.path.basename(top_dir_full_path) == _CTAT_Build_dirname:
        print "Build directory is: {:s}".format(top_dir_full_path)
        sys.stdout.flush()
        # The top_dir_path is the path to the genome_build_directory.
        genome_build_directory = top_dir_full_path
    else:
        # Look for it inside of the top_dir_path directory.
        print "Looking inside of: {:s}".format(top_dir_full_path)
        sys.stdout.flush()
        top_dir_contents = os.listdir(top_dir_full_path)
        if (_CTAT_Build_dirname in top_dir_contents):
            # The genome_build_directory is inside of the top_dir_path directory.
            print "1. Found it."
            sys.stdout.flush()
            genome_build_directory = "{:s}/{:s}".format(top_dir_full_path,_CTAT_Build_dirname)
        else:
            # Find all subdirectories containing the _CTAT_Build_dirname or the _CTAT_RefGenome_Filename.
            # Look down the directory tree two levels.
            build_dirs_in_subdirs = list()
            subdirs_with_genome_files = list()
            build_dirs_in_sub_subdirs = list()
            sub_subdirs_with_genome_files = list()
            subdirs = [entry for entry in top_dir_contents if (os.path.isdir("{:s}/{:s}".format(top_dir_full_path,entry)))]
            for subdir in subdirs:
                subdir_path = "{:s}/{:s}".format(top_dir_full_path, subdir)
                subdir_path_contents = os.listdir(subdir_path)
                # print "Is it one of:\n\t" + "\n\t".join(subdir_path_contents)
                if (_CTAT_Build_dirname in subdir_path_contents):
                    # The genome_build_directory is inside of the subdir_path directory.
                    print "2a, Found one."
                    build_dirs_in_subdirs.append("{:s}/{:s}".format(subdir_path, _CTAT_Build_dirname))
                if (_CTAT_RefGenome_Filename in subdir_path_contents):
                    subdirs_with_genome_files.append(subdir_path)
                # Since we are already looping, loop through all dirs one level deeper as well.
                sub_subdirs = [entry for entry in subdir_path_contents if (os.path.isdir("{:s}/{:s}".format(subdir_path,entry)))]
                for sub_subdir in sub_subdirs:
                    sub_subdir_path = "{:s}/{:s}".format(subdir_path, sub_subdir)
                    sub_subdir_path_contents = os.listdir(sub_subdir_path)
                    # print "Is it one of:\n\t" + "\n\t".join(sub_subdir_path_contents)
                    if (_CTAT_Build_dirname in sub_subdir_path_contents):
                        # The genome_build_directory is inside of the sub_subdir_path directory.
                        print "3a. Found one."
                        build_dirs_in_sub_subdirs.append("{:s}/{:s}".format(sub_subdir_path, _CTAT_Build_dirname))
                    if (_CTAT_RefGenome_Filename in sub_subdir_path_contents):
                        sub_subdirs_with_genome_files.append(sub_subdir_path)
            # Hopefully there is one and only one found build directory.
            # If none are found we check for a directory containing the genome reference file,
            # but the build process sometimes causes more than one directory to have a copy,
            # so finding that file is not a sure thing.
            if (len(build_dirs_in_subdirs) + len(build_dirs_in_sub_subdirs)) > 1:
                print "\n***************************************"
                print "Found multiple CTAT Genome Resource Libraries " + \
                    "in the given directory:\n\t{:s}".format(top_dir_full_path)
                sys.stdout.flush()
                print_directory_contents(top_dir_full_path, 2)
                print "***************************************\n"
                sys.stdout.flush()
                raise ValueError("Found multiple CTAT Genome Resource Libraries " + \
                    "in the given directory:\n\t{:s}".format(top_dir_full_path))
            elif len(build_dirs_in_subdirs) == 1:
                # The genome_build_directory is inside of the subdir_path directory.
                print "2b, Found it."
                sys.stdout.flush()
                genome_build_directory = build_dirs_in_subdirs[0]
            elif len(build_dirs_in_sub_subdirs) == 1:
                # The genome_build_directory is inside of the subdir_path directory.
                print "3b, Found it."
                sys.stdout.flush()
                genome_build_directory = build_dirs_in_sub_subdirs[0]
            elif (len(sub_subdirs_with_genome_files) + len(subdirs_with_genome_files)) > 1:
                print "\n***************************************"
                print "Unable to find CTAT Genome Resource Library " + \
                      "in the given directory:\n\t{:s}".format(top_dir_full_path)
                print "And multiple directories contain {:s}".format(_CTAT_RefGenome_Filename)
                sys.stdout.flush()
                print_directory_contents(top_dir_full_path, 2)
                print "***************************************\n"
                sys.stdout.flush()
                raise ValueError("Unable to find CTAT Genome Resource Library " + \
                    "in the given directory:\n\t{:s}".format(top_dir_full_path))
            elif (len(sub_subdirs_with_genome_files) == 1):
                print "3c, Maybe found it."
                sys.stdout.flush()
                genome_build_directory = sub_subdirs_with_genome_files[0]
                print_warning = True
            elif (len(subdirs_with_genome_files) == 1):
                print "2c, Maybe found it."
                sys.stdout.flush()
                genome_build_directory = subdirs_with_genome_files[0]
                print_warning = True
            elif (_CTAT_RefGenome_Filename in top_dir_contents):
                print "1c. Maybe found it."
                sys.stdout.flush()
                genome_build_directory = top_dir_full_path
                print_warning = True
            else:
                print "\n***************************************"
                print "Unable to find CTAT Genome Resource Library " + \
                      "in the given directory:\n\t{:s}".format(top_dir_full_path)
                sys.stdout.flush()
                print_directory_contents(top_dir_full_path, 2)
                print "***************************************\n"
                sys.stdout.flush()
                raise ValueError("Unable to find CTAT Genome Resource Library " + \
                    "in the given directory:\n\t{:s}".format(top_dir_full_path))
        # end else
    # Check if the CTAT Genome Resource Lib has anything in it (and specifically ref_genome.fa).
    if (genome_build_directory is None):
        print "\n***************************************"
        print "Cannot find the CTAT Genome Resource Library " + \
            "in the given directory:\n\t{:s}".format(top_dir_full_path)
        sys.stdout.flush()
        print_directory_contents(top_dir_full_path, 2)
        print "***************************************\n"
        sys.stdout.flush()
        raise ValueError("Cannot find the CTAT Genome Resource Library " + \
            "in the given directory:\n\t{:s}".format(top_dir_full_path))
    else:
        if (_CTAT_RefGenome_Filename not in os.listdir(genome_build_directory)):
            print "\n***************************************"
            print "\nWARNING: Cannot find Genome Reference file {:s} ".format(_CTAT_RefGenome_Filename) + \
                "in the genome build directory:\n\t{:s}".format(genome_build_directory)
            sys.stdout.flush()
            print_directory_contents(genome_build_directory, 2)
            print "***************************************\n"
            sys.stdout.flush()
        if print_warning and genome_build_directory:
            print "\n***************************************"
            print "\nWARNING: Cannot find the CTAT Genome Resource Library, " + \
                "but found a {:s} file, so set its directory as the library.".format(_CTAT_RefGenome_Filename)
            print "This my not be the correct directory:\n\t{:s}".format(genome_build_directory)
            sys.stdout.flush()
            print_directory_contents(genome_build_directory, 2)
            print "***************************************\n"
            sys.stdout.flush()
    return genome_build_directory

def build_directory_from_build_location(src_filename, build_location):
    # This function is used to make sure our builds follow the covention of placing the build in a directory named
    # _CTAT_Build_dirname, which is normally inside of a directory named for the genome name.
    # However, if the user passes a build_location named _CTAT_Build_dirname that directory will be used, 
    # regardless of the name of the enclosing directory.
    build_directory = None
    genome_dir_name = find_genome_name_in_path(src_filename)
    if (genome_dir_name is None) or (genome_dir_name == ""):
        # Maybe it is in the path of the build_location.
        genome_dir_name = find_genome_name_in_path(build_location)
    if os.path.basename(build_location) == genome_dir_name:
        build_directory = os.path.join(build_location, _CTAT_Build_dirname)
    elif os.path.basename(build_location) == _CTAT_Build_dirname:
        build_directory = build_location
    elif genome_dir_name is None:
        # This can be the case if the src_filename does not contain a directory named for the genome.
        build_directory = os.path.join(build_location, _CTAT_Build_dirname)
    else:
        build_directory = os.path.join(build_location, genome_dir_name, _CTAT_Build_dirname)
    return build_directory

def main():
    # Regarding the command line, there are three basic ways to use this tool:
    # 1) Download and Build the CTAT Genome Resource Library from an archive;
    # 2) Build the library from source data files that are already downloaded;
    # 3) Specify the location of an already built library.
    # Any of these methods can incorporate or be followed by a gmap build.
    # Any of these methods can be followed by a mutation resources download and/or integration.
    # Choose arguments for only one method.
    # Do not use arguments in a mixed manner. I am not writing code to handle that at this time.
    parser = argparse.ArgumentParser()
    # Arguments for all methods:
    parser.add_argument('-o', '--output_filename', \
        help='Name of the output file, where the json dictionary will be written.')
    parser.add_argument('-y', '--display_name', 
        default='', \
        help='Is used as the display name for the entry of this Genome Resource Library in the data table.')
    parser.add_argument('-g', '--gmap_build', \
        help='Will do a gmap_build on the Genome Resource Library, if it has not previously been gmapped.',
        action='store_true')
    parser.add_argument('-f', '--force_gmap_build', \
        help='Will force gmap_build of the Genome Resource Library, even if previously gmapped.', 
        action='store_true')
    parser.add_argument('-m', '--download_mutation_resources_url', 
        default='', \
        help='Value should be the url of the zipped up mutation resources. ' + \
             'These are located at: https://data.broadinstitute.org/Trinity/CTAT/mutation/.' + \
             'Will download mutation resources and integrate them into the Genome Resource Library.' + \
             'Cosmic resources must previously have beeen downloaded (https://cancer.sanger.ac.uk/cosmic/download).' + \
             'Cosmic resources can be placed directly into the Genome Resource Library ' + \
             'or you can set the --cosmic_resources_location argument.' + \
             'See https://github.com/NCIP/ctat-mutations/tree/no_sciedpiper/mutation_lib_prep for more info. ' + \
             'If a previous download and integration was not completed, ' + \
             'calling with this option set will attempt to finish the integration.')
    parser.add_argument('-l', '--new_mutation_download', \
        help='Forces the mutation resources to be downloaded, ' + \
             'even if previously downloaded into this Genome Resource Library.', 
        action='store_true')
    parser.add_argument('-i', '--new_mutation_integration', \
        help='Forces the mutation resources to be integrated, ' + \
             'even if previously integrated into this Genome Resource Library.', 
        action='store_true')
    parser.add_argument('-c', '--cosmic_resources_location', 
        default='', \
        help='Specify a non-default location where the Cosmic files reside. ' + \
             'Normally they are assumed to reside in the build directory, ' + \
             'but if that directory has not been created yet when this program ' + \
             'is called, you can specify the full path to the directory where they reside.')
    parser.add_argument('-t', '--cravat_tissues_filepath', 
        default='', \
        help='Specify a non-default location where the Cosmic files reside. ' + \
             'Normally they are assumed to reside in the build directory, ' + \
             'but if that directory has not been created yet when this program ' + \
             'is called, you can specify the full path to the directory where they reside.')
    # Method 1) arguments - Download and Build. 
    # - One can optionally utilize --build_location argument with this group of arguments.
    download_and_build_args = parser.add_argument_group('Download and Build arguments')
    download_and_build_args.add_argument('-u', '--download_url', 
        default='', \
        help='This is the url of an archive file containing the library files. ' + \
            'These are located at https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/. ' + \
            'Works with both source-data and plug-n-play archives.')
    download_and_build_args.add_argument('-d', '--download_location', 
        default='', \
        help='Full path of the CTAT Resource Library download location, where the download will be placed. ' + \
            'If the archive file has already had been successfully downloaded, ' + \
            'it will only be downloaded again if --new_archive_download is selected. ' + \
            'If --build_location is not set, then the archive will be built in place at the download_location. ' + \
            'If a previous download and build was started but not completed at this or a specified build_location, ' + \
            'calling with this and the previous option set, but not --new_archive_download, ' + \
            'will attempt to finish the download and build.')
    download_and_build_args.add_argument('-a', '--new_archive_download', \
        help='Forces a new download (and build if needed) of the Genome Resource Library, ' + \
            'even if previously downloaded and built.',
        action='store_true')
    download_and_build_args.add_argument('-k', '--keep_archive', \
        help='The archive will not be deleted after it is extracted.',
        action='store_true')
    # Method 2) arguments - Specify source and build locations.
    # - One can optionally utilize --build_location argument with this group of arguments.
    specify_source_and_build_args = parser.add_argument_group('Specify Source and Build locations arguments')
    specify_source_and_build_args.add_argument('-s', '--source_location', 
        default='', \
        help='Full path to the directory containing CTAT Resource Library source-data files ' + \
            'or the full path to a CTAT Resource Library archive file (.tar.gz). ' + \
            'If the --build_location option is not set, the reference library will be built in the source_location directory.' + \
            'If a previous download and build was started but not completed at this location, ' + \
            'calling with this option set, but not --new_library_build, ' + \
            'will attempt to finish the build.')
    specify_source_and_build_args.add_argument('-r', '--new_library_build', \
        help='Forces build of the CTAT Genome Resource Library, even if previously built. ' + \
            'The --source_location must be a source-data archive or directory, or this is a no-op.', 
        action='store_true')
    # Method 3) arguments - Specify the location of a built library.
    built_lib_location_arg = parser.add_argument_group('Specify location of built library arguments')
    built_lib_location_arg.add_argument('-b', '--build_location', 
        default='', \
        help='Full path to the location of a built CTAT Genome Resource Library, ' + \
            'either where it is, or where it will be placed.')

    args = parser.parse_args()

    # Apparently, Galaxy writes all of the input parameters to the output file prior to
    # this program being called.
    # But I do not get input values from the json file, but rather from command line.
    # Just leaving the following code as a comment, in case it might be useful to someone later.
    # params = from_json_string(open(filename).read())
    # target_directory = params['output_data'][0]['extra_files_path']
    # os.mkdir(target_directory)
    
    lib_was_built = False
    extracted_directory = None
    source_data_directory = None
    genome_build_directory = None
    download_url_is_set = (args.download_url is not None) and (args.download_url != "")
    download_location_is_set = (args.download_location is not None) and (args.download_location != "")
    source_location_is_set = (args.source_location is not None) and (args.source_location != "")
    build_location_is_set = (args.build_location is not None) and (args.build_location != "")
    mutation_url_is_set = (args.download_mutation_resources_url is not None) \
                               and (args.download_mutation_resources_url != "")
  
    if download_url_is_set:
        print "The value of download_url argument is:\n\t{:s}".format(str(args.download_url))
        sys.stdout.flush()
        if source_location_is_set:
            raise ValueError("Argument --source_location cannot be used in combination with --download_url.")
        if not download_location_is_set:
            raise ValueError("Argument --download_url requires that --download_location be specified.")
        downloaded_filename_full_path = \
            download_genome_archive(source_url=args.download_url, \
                             destination=args.download_location, \
                             force_new_download=args.new_archive_download)
        print "\nThe downloaded file is:\n\t{:s}.\n".format(str(downloaded_filename_full_path))    
        sys.stdout.flush()
        
        if ctat_library_type(downloaded_filename_full_path) == _LIBTYPE_SOURCE_DATA:
            print "It is source data."
            sys.stdout.flush()
            # If it is source_data, extract to download_location (the directory where the download was placed).
            extracted_directory = extract_genome_file(archive_filepath=downloaded_filename_full_path, \
                                                      destination=args.download_location, \
                                                      force_new_extraction=args.new_archive_download, \
                                                      keep_archive=args.keep_archive)
            source_data_directory = extracted_directory
            if build_location_is_set:
                genome_build_directory = build_directory_from_build_location(source_data_directory, args.build_location)
            else:
                # We will build within a subdirectory of the source_data_directory .
                # The name of the build directory will be the default _CTAT_Build_dirname.
                # This _CTAT_Build_dirname directory will not exist until the library is built.
                genome_build_directory = os.path.join(source_data_directory, _CTAT_Build_dirname)
            
        elif ctat_library_type(downloaded_filename_full_path) == _LIBTYPE_PLUG_N_PLAY:
            print "It is plug-n-play data."
            sys.stdout.flush()
            if build_location_is_set:
                # Extract to the build location. The library is already built.
                extracted_directory = extract_genome_file(archive_filepath=downloaded_filename_full_path, \
                                                          destination=args.build_location, \
                                                          force_new_extraction=args.new_archive_download, \
                                                          keep_archive=args.keep_archive)
            else:
                # Extract to the download location.
                extracted_directory = extract_genome_file(archive_filepath=downloaded_filename_full_path, \
                                                          destination=args.download_location, \
                                                          force_new_extraction=args.new_archive_download, \
                                                          keep_archive=args.keep_archive)
            # There is no source_data_directory, so its value stays as None.
            
            # Look for the build directory. It should be inside the extracted_directory
            if len(os.listdir(extracted_directory)) == 1:
                # Then that one file is a subdirectory that should be the build_directory.
                # That is how the plug-n-play directories are structured.
                subdir_filename = os.listdir(extracted_directory)[0]
                genome_build_directory = os.path.join(extracted_directory, subdir_filename)
            else:
                # We need to search for the build directory, since there is more than one file.
                genome_build_directory = search_for_genome_build_dir(extracted_directory)
        else:
            raise ValueError("Unexpected CTAT Library type. Neither plug-n-play nor source_data:\n\t" + \
                "{:s}".format(downloaded_filename_full_path))
    elif source_location_is_set:
            # Then the user wants to build the directory from the source data.
            source_data_directory = os.path.realpath(args.source_location)
            print "\nThe program is being told that the source data is in:\n\t{:s}.\n".format(str(source_data_directory))
            sys.stdout.flush()
            if build_location_is_set:
                genome_build_directory = build_directory_from_build_location(source_data_directory, args.build_location)
            else:
                # We will build within a subdirectory of the source_data_directory .
                # The name of the build directory will be the default _CTAT_Build_dirname.
                # This _CTAT_Build_dirname directory will not exist until the library is built.
                genome_build_directory = os.path.join(source_data_directory, _CTAT_Build_dirname)                
    elif build_location_is_set:
        genome_build_directory = args.build_location

    if (genome_build_directory is None) or (genome_build_directory == ""):
        raise ValueError("At least one of --download_url, --source_location, or --build_location must be specified.")
        
    print "\nThe location where the CTAT Genome Resource Library exists " + \
        "or will be built is {:s}.\n".format(str(genome_build_directory))
    sys.stdout.flush()

    # To take out builds for testing, comment out the lines that do the building.
    # The command that builds the ctat genome library also has an option for building the gmap indexes.
    # That is why the gmap_build values are sent to build_the_library(), but if we are not building the
    # library, the user might still be asking for a gmap_build. That is done after rechecking for the
    # genome_build_directory.
    if source_data_directory is not None:
        build_the_library(source_data_directory, \
                          genome_build_directory, \
                          args.new_library_build, \
                          args.gmap_build, \
                          args.force_gmap_build)
        lib_was_built = True

    # The following looks to see if the library actually exists after the build,
    # and raises an error if it cannot find the library files.
    # The reassignment of genome_build_directory can be superfluous, 
    # since many times the genome_build_directory will already point to the correct directory.
    # There are cases, however, where a user specifies a location that contains the 
    # genome_build_directory rather than is the genome_build_directory.
    genome_build_directory = search_for_genome_build_dir(genome_build_directory)

    if (args.gmap_build and not lib_was_built):
        # If we did not build the genome resource library
        # the user might still be asking for a gmap_build.
        gmap_the_library(genome_build_directory, args.force_gmap_build)
        sys.stdout.flush()

    if mutation_url_is_set:
        download_and_integrate_mutation_resources(source_url=args.download_mutation_resources_url, \
                                  genome_build_directory=genome_build_directory, \
                                  cosmic_resources_location=args.cosmic_resources_location, \
                                  force_new_download=args.new_mutation_download, \
                                  force_new_integration=args.new_mutation_integration)

    # Need to get the genome name.
    genome_name = find_genome_name_in_path(args.download_url)
    if genome_name is None:
        genome_name = find_genome_name_in_path(genome_build_directory)
    if genome_name is None:
        genome_name = find_genome_name_in_path(extracted_directory)
    if genome_name is None:
        genome_name = find_genome_name_in_path(args.source_location)
    if genome_name is None:
        genome_name = find_genome_name_in_path(args.download_location)
    if genome_name is None:
        genome_name = find_genome_name_in_path(args.display_name)
    if genome_name is None:
        genome_name = _CTAT_ResourceLib_DefaultGenome
        print "WARNING: We could not find a genome name in any of the directory paths."
        sys.stdout.flush()

    # Determine the display_name for the library.
    if (args.display_name is None) or (args.display_name == ""):
        # Create the display_name from the genome_name.
        display_name = _CTAT_ResourceLib_DisplayNamePrefix + genome_name
    else:
        display_name = _CTAT_ResourceLib_DisplayNamePrefix + args.display_name
    display_name = display_name.replace(" ","_")

    # Create a unique_id for the library.
    datetime_stamp = datetime.now().strftime("_%Y_%m_%d_%H_%M_%S_%f")
    unique_id = genome_name + "." + datetime_stamp

    print "The Genome Resource Library's display_name will be set to: {:s}\n".format(display_name)
    print "Its unique_id will be set to: {:s}\n".format(unique_id)
    print "Its dir_path will be set to: {:s}\n".format(genome_build_directory)
    sys.stdout.flush()

    data_manager_dict = {}
    data_manager_dict['data_tables'] = {}
    data_manager_dict['data_tables']['ctat_genome_resource_libs'] = []
    data_table_entry = dict(value=unique_id, name=display_name, path=genome_build_directory)
    data_manager_dict['data_tables']['ctat_genome_resource_libs'].append(data_table_entry)
    
    # Create the data table for the cravat_tissues, if the file is given:
    print "The cravat tissues file is: {:s}".format(str(args.cravat_tissues_filepath))
    if (args.cravat_tissues_filepath is not None) and (args.cravat_tissues_filepath != ""):
        data_manager_dict['data_tables']['ctat_cravat_tissues'] = []
        cravat_file = open(args.cravat_tissues_filepath, 'r')
        for line in cravat_file:
            # print line
            if line[0] != '#':
                # The line is not a comment, so parse it.
                items = [item.strip() for item in line.split("\t")]
                print items
                data_table_entry = dict(value=items[0], name=items[1], code=items[2], date=items[3])
                data_manager_dict['data_tables']['ctat_cravat_tissues'].append(data_table_entry)

    # Temporarily the output file's dictionary is written for debugging:
    print "The dictionary for the output file is:\n\t{:s}".format(str(data_manager_dict))
    sys.stdout.flush()
    # Save info to json file. This is used to transfer data from the DataManager tool, to the data manager,
    # which then puts it into the correct .loc file (I think).
    # One can comment out the following line when testing without galaxy package.
    open(args.output_filename, 'wb').write(to_json_string(data_manager_dict))

if __name__ == "__main__":
    main()
