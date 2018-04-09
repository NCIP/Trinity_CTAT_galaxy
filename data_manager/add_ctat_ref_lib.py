#!/usr/bin/env python
# ref: https://galaxyproject.org/admin/tools/data-managers/how-to/define/

# Rewritten by H.E. Cicada Brokaw Dennis from a source downloaded from the toolshed and
# other example code on the web.
# This now allows downloading of a user selected library
# but only from the CTAT Genome Reference Library website.
# Ultimately we might want to allow the user to specify any location 
# from which to download.
# Users can create or download other libraries and use this tool to add them if they don't want
# to add them by hand.

import argparse
import os
#import tarfile
#import urllib
import subprocess

from galaxy.util.json import from_json_string, to_json_string

# The FileListParser is used by get_ctat_genome_filenames(),
# which is called by the Data Manager interface (.xml file) to get
# the filenames that are available online at broadinstitute.org
# Not sure best way to do it. 
# This object uses HTMLParser to look through the html 
# searching for the filenames within anchor tags.
import urllib2
from HTMLParser import HTMLParser

_CTAT_ResourceLib_URL = 'https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/'
_CTAT_BuildDir_Name = 'ctat_genome_lib_build_dir'
_NumBytesNeededForBuild = 64424509440 # 60 Gigabytes. FIX - This might not be correct.
_DownloadSuccessFile = 'download_succeeded.txt'

class FileListParser(HTMLParser):
    def __init__(self):
        # Have to use direct call to super class rather than using super():
        # super(FileListParser, self).__init__()
        # because HTMLParser is an "old style" class and its inheritance chain does not include object.
        HTMLParser.__init__(self)
        self.filenames = set()
    def handle_starttag(self, tag, attrs):
        # Look for filename references in anchor tags and add them to filenames.
        if tag == "a":
            # The tag is an anchor tag.
            for attribute in attrs:
                # print "Checking: {:s}".format(str(attribute))
                if attribute[0] == "href":
                    # Does the href have a tar.gz in it?
                    if ("tar.gz" in attribute[1]) and ("md5" not in attribute[1]):
                        # Add the value to filenames.
                        self.filenames.add(attribute[1])            
# End of class FileListParser

def get_ctat_genome_filenames():
    # open the url and retrieve the filenames of the files in the directory.
    resource = urllib2.urlopen(_CTAT_ResourceLib_URL)
    theHTML = resource.read()
    filelist_parser = FileListParser()
    filelist_parser.feed(theHTML)
    # return a tuple of the filenames
    return tuple(filelist_parser.filenames)

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

def download_from_BroadInst(src_filename, destination, force_download):
    # ctat_resource_lib_url is the full URL of the file we want to download.
    ctat_resource_lib_url = _CTAT_ResourceLib_URL + src_filename
    # Get the root filename of the Genome Directory.
    root_genome_dirname = src_filename.split(".")[0]
    # If the src_filename indicates it is a source file, as opposed to plug-n-play, 
    # then we may need to do some post processing on it.
    type_of_download = src_filename.split(".")[1]
    download_has_source_data = (type_of_download == "source_data"):

    # We want to make sure that destination is absolute fully specified path.
    cannonical_destination = os.path.realpath(destination)
    if os.path.exists(cannonical_destination):
        if not os.path.isdir(cannonical_destination):
            raise ValueError("The destination is not a directory: " + \
                             "{:s}".format(cannonical_destination))
        # else all is good. It is a directory.
    else:
        # We need to create it.
        try:
            os.makedirs(cannonical_destination)
        except os.error:
            print "ERROR: Trying to create the following directory path:"
            print "\t{:s}".format(cannonical_destination)
            raise

    # Make sure the directory now exists and we can write to it.
    if not os.path.exists(cannonical_destination):
        # It should have been created, but if it doesn't exist at this point
        # in the code, something is wrong. Raise an error.
        raise OSError("The destination directory could not be created: " + \
                      "{:s}".format(cannonical_destination))
    test_writing_file = "{:s}/{:s}".format(cannonical_destination, _Download_TestFile)
    try:
        filehandle = open(test_writing_filee, "w")
    except IOError:
        print "The destination directory could not be written into: " + \
                      "{:s}".format(cannonical_destination))
        raise
    
    # Get the list of files in the directory,
    # We use it to check for a previous download or extraction among other things.
    orig_files_in_destdir = set(os.listdir(cannonical_destination))
    # See whether the file has been downloaded already.
    download_success_file_path = "{:s}/{:s}".format(cannonical_destination, _DownloadSuccessFile)
    if (_DownloadSuccessFile not in orig_files_in_destdir) \
        or (root_genome_dirname not in orig_files_in_destdir) \
        or force_download):
        # Check whether there is enough space on the device for the library.
        statvfs = os.statvfs(cannonical_destination)
        # fs_size = statvfs.f_frsize * statvfs.f_blocks          # Size of filesystem in bytes
        # num_free_bytes = statvfs.f_frsize * statvfs.f_bfree    # Actual number of free bytes
        num_avail_bytes = statvfs.f_frsize * statvfs.f_bavail    # Number of free bytes that ordinary users
                                                                 # are allowed to use (excl. reserved space)
        if (num_avail_bytes < _NumBytesNeededForBuild):
            raise OSError("There is insufficient space ({:s} bytes)".format(str(num_avail_bytes)) + \
                          " on the device of the destination directory: " + \
                          "{:s}".format(cannonical_destination))
    
        #Previous code to download and untar. Not using anymore.
        #full_filepath = os.path.join(destination, src_filename)
        #
        #Download ref: https://dzone.com/articles/how-download-file-python
        #f = urllib2.urlopen(ctat_resource_lib_url)
        #data = f.read()
        #with open(full_filepath, 'wb') as code:
        #    code.write(data)
        #
        #Another way to download:
        #try: 
        #    urllib.urlretrieve(url=ctat_resource_lib_url, filename=full_filepath)
        #
        #Then untar the file.
        #try: 
        #    tarfile.open(full_filepath, mode='r:*').extractall()
    
        # We want to transfer and untar the file without storing the tar file, because that
        # adds all that much more space to the needed amount of free space on the disk.
        # Use subprocess to pipe the output of curl into tar.
        command = "curl {:s} | tar -xzvf - -C {:s}".format(ctat_resource_lib_url, cannonical_destination)
        try: # to send the command that downloads and extracts the file.
            command_output = subprocess.check_output(command, shell=True)
            # FIX - not sure check_output is what we want to use. If we want to have an error raised on
            # any problem, maybe we should not be checking output.
        except subprocess.CalledProcessError:
            print "ERROR: Trying to run the following command:\n\t{:s}".format(command)
            raise

    # Some code to help us if errors occur.
    print "\n*******************************\nFinished download and extraction."
    subprocess.check_call("ls -lad {:s}/*".format(cannonical_destination), shell=True)
    subprocess.check_call("ls -lad {:s}/*/*".format(cannonical_destination), shell=True)
    
    newfiles_in_destdir = set(os.listdir(cannonical_destination)) - orig_files_in_destdir
    if (root_genome_dirname not in newfiles_in_destdir):
        # Perhaps it has a different name than what we expected it to be.
        # It will be the file that was not in the directory
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
                    found_filename = filename
        if found_filename is not None:
            root_genome_dirname = found_filename

    downloaded_directory = "{:s}/{:s}".format(cannonical_destination, root_genome_dirname)

    if (os.path.exists(downloaded_directory):
        try:
            # Create a file to indicate that the download succeeded.
            subprocess.check_call("touch {:s}".format(download_success_file_path), shell=True)
        # Look for the build directory, or specify the path where it should be placed.
        if len(os.listdir(downloaded_directory)) == 1:
            # Then that one file is a subdirectory that should be the downloaded_directory.
            subdir_filename = os.listdir(downloaded_directory)[0]
            genome_build_directory = "{:s}/{:s}".format(downloaded_directory, subdir_filename)
        else:
            genome_build_directory = "{:s}/{:s}".format(downloaded_directory, _CTAT_BuildDir_Name)
    else:
        raise ValueError("ERROR: Could not find the extracted file in the destination directory:" + \
                             "\n\t{:s}".format(cannonical_destination))

    return (downloaded_directory, download_has_source_data, genome_build_directory)
        
def gmap_the_library(genome_build_directory):
        # This is the processing that needs to happen for gmap-fusion to work.
        # genome_build_directory should normally be a fully specified path, 
        # though it should work if it is relative.
        command = "gmap_build -D {:s}/ -d ref_genome.fa.gmap -k 13 {:s}/ref_genome.fa".format( \
                  genome_build_directory, genome_build_directory)
        try: # to send the gmap_build command.
            command_output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError:
            print "ERROR: While trying to run the gmap_build command on the library:\n\t{:s}".format(command)
            raise
        finally:
            # Some code to help us if errors occur.
            print "\n*******************************\nAfter running gmap_build."
            subprocess.check_call("ls -lad {:s}/../*".format(genome_build_directory), shell=True)
            subprocess.check_call("ls -lad {:s}/*".format(genome_build_directory), shell=True)
            subprocess.check_call("ls -lad {:s}/*/*".format(genome_build_directory), shell=True)
            print "*******************************"

def build_the_library(genome_source_directory, genome_build_directory, build, gmap_build):
    """ genome_source_directory is the location of the source_data needed to build the library.
            Normally it is fully specified, but could be relative.
        genome_build_directory is the location where the library will be built.
            It can be relative to the current working directory or an absolute path.
        build specifies whether to run prep_genome_lib.pl even if it was run before.
        gmap_build specifies whether to run gmap_build or not.

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
    if (genome_source_directory != "" ) and build:
        if os.path.exists(genome_source_directory):
            os.chdir(genome_source_directory)
            # FIX - look for a fusion_annot_lib and include it, else omit it.
            command = "prep_genome_lib.pl --genome_fa ref_genome.fa --gtf ref_annot.gtf " + \
                      "--fusion_annot_lib CTAT_HumanFusionLib.v0.1.0.dat.gz " + \
                      "--annot_filter_rule AnnotFilterRule.pm " + \
                      "--pfam_db PFAM.domtblout.dat.gz " + \
                      "--output_dir {:s} ".format(genome_build_directory)
            if gmap_build:
                command += "--gmap_build "
            try: # to send the prep_genome_lib command.
                command_output = subprocess.check_call(command, shell=True)
            except subprocess.CalledProcessError:
                print "ERROR: While trying to run the prep_genome_lib.pl command " + \
                    "on the CTAT Genome Resource Library:\n\t{:s}".format(command)
                raise
            finally:
                # Some code to help us if errors occur.
                print "\nSource Directory {:s}:".format(genome_source_directory)
                subprocess.check_call("ls -lad {:s}/*".format(genome_source_directory), shell=True)
                print "\nBuild Directory {:s}:".format(genome_build_directory)
                subprocess.check_call("ls -lad {:s}/*".format(genome_build_directory), shell=True)
                subprocess.check_call("ls -lad {:s}/*/*".format(genome_build_directory), shell=True)
        else:
            raise ValueError("Cannot build the CTAT Genome Resource Library. " + \
                "The source directory does not exist:\n\t{:s}".format(genome_source_directory))
    elif gmap_build:
        gmap_the_library(genome_build_directory)

def main():
    #Parse Command Line
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download_file', default="", \
        help='This is the filename (tar.gz) of a file at https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/.')
    parser.add_argument('-g', '--genome_name', default="UNSPECIFIED_GenomeName", \
        help='Is used as the selector text for the entry of this Genome Resource Library in the data table.')
    parser.add_argument('-p', '--destination_path', \
        help='Full path of the CTAT Resource Library location or destination, either where it is, or where it will be placed.')
    parser.add_argument('-o', '--output_filename', \
        help='Name of the output file, where the json dictionary will be written.')
    parser.add_argument('-f', '--force_download', 
        help='Forces download of the Genome Resource Library, even if previously downloaded.', action="store_true")
    parser.add_argument('-b', '--build', 
        help='Forces build/rebuild the Genome Resource Library, even if previously built. ' + \
             'Must have downloaded source_data for this to work.', action="store_true")
    parser.add_argument('-m', '--gmap_build', 
        help='Must be selected if you want the library to be gmapped. ' + \
             'Will force gmap_build of the Genome Resource Library, even if previously gmapped.', action="store_true")
    args = parser.parse_args()

    # All of the input parameters are written by default to the output file prior to
    # this program being called.
    # But I do not get input values from the json file, but rather from command line.
    # Just leaving the following code as a comment, in case it might be useful to someone later.
    # params = from_json_string(open(filename).read())
    # target_directory = params['output_data'][0]['extra_files_path']
    # os.mkdir(target_directory)

    lib_was_downloaded = False
    download_has_source_data = False
    if (args.download_file != ""):
        downloaded_directory, download_has_source_data, genome_build_directory = \
            download_from_BroadInst(src_filename=args.download_file, \
                                    destination=args.destination_path, \
                                    force_download=args.force_download)
        lib_was_downloaded = True
    else:
        genome_build_directory = args.destination_path
        if not os.path.exists(genome_build_directory)
            raise ValueError("Cannot find the CTAT Genome Resource Library. " + \
                "The directory does not exist:\n\t{:s}".format(genome_build_directory))
        # FIX - Check if there is an actual CTAT Genome Ref Lib there.

    print "\nThe location of the CTAT Genome Resource Library is {:s}.\n".format(genome_build_directory)

    if (download_has_source_data or args.build or args.gmap) 
        build_the_library(downloaded_directory, genome_build_directory, args.build, args.gmap)
    elif (args.gmap_build)
        gmap_the_library(genome_build_directory)

    if (args.genome_name is None) or (args.genome_name == ""):
        # Get the name out of the downloaded_directory name.
        if (download_file != None) && (download_file != ""):
            genome_name = download_file.split(".")[0]
        else:
            genome_name = "GRCh38_gencode_v27"
            print "WARNING: Do not have a genome name. Using a default, that might not be correct."
    else:
        genome_name = args.genome_name
    print "The Genome Name will be set to: {:s}\n".format(genome_name)

    # Set the value to the basename of the downloaded directory name minus the extension. 
    # FIX - Need to make sure is unique. This is prob. not good way to do it. Just doing it this way now for testing.
    table_entry_value = os.path.basename(downloaded_directory).split(".")[0]
    data_manager_dict = {}
    data_manager_dict['data_tables'] = {}
    data_manager_dict['data_tables']['ctat_genome_ref_libs'] = []
    data_table_entry = dict(value=table_entry_value, name=genome_name, path=genome_build_directory)
    data_manager_dict['data_tables']['ctat_genome_ref_libs'].append(data_table_entry)

    # Temporarily the output file's dictionary is written for debugging:
    print "The dictionary for the output file is:\n\t{:s}".format(str(data_manager_dict))
    # Save info to json file. This is used to transfer data from the DataManager tool, to the data manager,
    # which then puts it into the correct .loc file (I think).
    open(args.output_filename, 'wb').write(to_json_string(data_manager_dict))

if __name__ == "__main__":
    main()
