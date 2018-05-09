#!/usr/bin/env python
# ref: https://galaxyproject.org/admin/tools/data-managers/how-to/define/

# Rewritten by H.E. Cicada Brokaw Dennis from a source downloaded from the toolshed and
# other example code on the web.
# This file downloads annotations for lncrna (slncky tool)

import argparse
import os
import subprocess

# The following is used to generate a unique_id value
from datetime import *

# Remove the following line when testing without galaxy package:
from galaxy.util.json import to_json_string
# Am not using the following:
# from galaxy.util.json import from_json_string

# The FileListParser is used by get_ctat_genome_filenames(),
# which is called by the Data Manager interface (.xml file) to get
# the filenames that are available online at broadinstitute.org
# Not sure best way to do it. 
# This object uses HTMLParser to look through the html 
# searching for the filenames within anchor tags.
import urllib2
from HTMLParser import HTMLParser

_CTAT_lncrnaIndexPage_URL = 'https://data.broadinstitute.org/Trinity/CTAT/lncrna'
_CTAT_lncrnaDownload_URL = 'https://data.broadinstitute.org/Trinity/CTAT/lncrna/annotations'
_CTAT_lncrnaTableName = 'ctat_lncrna_annotations'
_CTAT_lncrnaDir_Name = 'annotations'
_CTAT_lncrna_DisplayNamePrefix = 'CTAT_lncrna_annotations_'
_lncrnaFileExtension = 'lc'
_NumBytesNeededForAnnotations =  # Number of bytes
#_DownloadFileSize = 5790678746 # 5.4 Gigabytes.
_Download_TestFile = 'write_testfile.txt'
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

def get_ctat_lncrna_annotations_locations():
    # For dynamic options need to return an interable with contents that are tuples with 3 items.
    # Item one is a string that is the display name put into the option list.
    # Item two is the value that is put into the parameter associated with the option list.
    # Item three is a True or False value, indicating whether the item is selected.
    options = []
    # open the url and retrieve the filenames of the files in the directory.
    resource = urllib2.urlopen(_CTAT_lncrnaIndexPage_URL)
    theHTML = resource.read()
    filelist_parser = FileListParser()
    filelist_parser.feed(theHTML)
    options.append((_CTAT_lncrnaDir_Name, _CTAT_lncrnaDownload_URL, True))
    print "The list of items being returned for the option menu is:"
    print str(options)
    return options 

def download_annotations(src_location, destination, force_download):
    # We do not know if the annotations has been downloaded already.
    # This function returns whether or not the annotations actually gets downloaded.
    annotations_was_downloaded = False
    # Get the root filename of the Genome Directory. 
    # The part after the last '/' and before the first '.'
    root_annotations_dirname = src_location.split("/")[-1].split(".")[0]

    # We want to make sure that destination is absolute fully specified path.
    cannonical_destination = os.path.realpath(destination) 
    if cannonical_destination.split("/")[-1] != root_annotations_dirname:
        cannonical_destination += "/" + root_annotations_dirname
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
        filehandle = open(test_writing_file, "w")
        filehandle.write("Testing writing to this file.")
        filehandle.close()
        os.remove(test_writing_file)
    except IOError:
        print "The destination directory could not be written into: " + \
                      "{:s}".format(cannonical_destination)
        raise
    
    # Get the list of files in the directory,
    # We use it to check for a previous download or extraction among other things.
    orig_files_in_destdir = set(os.listdir(cannonical_destination))
    # See whether the file has been downloaded already.
    download_success_file_path = "{:s}/{:s}".format(cannonical_destination, _DownloadSuccessFile)
    if (_DownloadSuccessFile not in orig_files_in_destdir) or force_download:
        # Check whether there is enough space on the device for the annotations.
        statvfs = os.statvfs(cannonical_destination)
        num_avail_bytes = statvfs.f_frsize * statvfs.f_bavail    # Number of free bytes that ordinary users
                                                                 # are allowed to use (excl. reserved space)
        if (num_avail_bytes < _NumBytesNeededForIndex):
            raise OSError("There is insufficient space ({:s} bytes)".format(str(num_avail_bytes)) + \
                          " on the device of the destination directory: " + \
                          "{:s}".format(cannonical_destination))
    
        
        if (_DownloadSuccessFile in orig_files_in_destdir):
            # Since we are redoing the download, 
            # the success file needs to be removed
            # until the download has succeeded.
            os.remove(download_success_file_path)
        # We want to transfer and untar the file without storing the tar file, because that
        # adds all that much more space to the needed amount of free space on the disk.
        # Use subprocess to pipe the output of curl into tar.
        # Make curl silent so progress is not printed to stderr.
        command = "curl --silent {:s} | tar -xzf - -C {:s}".format(src_location, cannonical_destination)
        try: # to send the command that downloads and extracts the file.
            command_output = subprocess.check_output(command, shell=True)
            # FIX - not sure check_output is what we want to use. If we want to have an error raised on
            # any problem, maybe we should not be checking output.
        except subprocess.CalledProcessError:
            print "ERROR: Trying to run the following command:\n\t{:s}".format(command)
            raise
        else:
            annotations_was_downloaded = True

    # Some code to help us if errors occur.
    print "\n*******************************\nFinished download and extraction."
    if os.path.exists(cannonical_destination) and os.path.isdir(cannonical_destination):
        subprocess.check_call("ls -la {:s} 2>&1".format(cannonical_destination), shell=True)
    
    files_in_destdir = set(os.listdir(cannonical_destination))
    found_filenames = set()
    for filename in files_in_destdir:
        # There should be three files, but some OS's might have created
        # other files in the directory, or maybe the user did.
        # Look for the annotations files.
        # The download files' names should start with the root_annotations_dirname
        # print "Is root: {:s} in file: {:s}".format(root_annotations_dirname, filename)
        if root_annotations_dirname in filename:
            found_filenames.add(filename)
    # print "The found_filenames are:\n\t{:s}".format(str(found_filenames))
    ## TODO: check number of files it gets
    if (len(found_filenames) >= 3):
        # FIX - we could md5 the files to make sure they are correct.
        # Or at least check their sizes, to see if the download completed ok.
        # Also we could check the names of the files.
        try:
            # Create a file to indicate that the download succeeded.
            subprocess.check_call("touch {:s}".format(download_success_file_path), shell=True)
        except IOError:
            print "The download_success file could not be created: " + \
                      "{:s}".format(download_success_file_path)
            raise
    else:
        print "After download, the potential annotations files found are:\n\t{:s}".format(str(found_filenames))
        raise ValueError("ERROR: Could not find the extracted annotations files " + \
                         "in the destination directory:\n\t{:s}".format(cannonical_destination))

    return (cannonical_destination, root_annotations_dirname, annotations_was_downloaded)
        
def main():
    #Parse Command Line
    # print "At start before parsing arguments."
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download_location', default="", \
        help='This is the download location of the lncrna annotations.')
    parser.add_argument('-n', '--display_name', default="", \
        help='Is used as the selector text for the entry of this lncrna annotations in the data table.')
    parser.add_argument('-p', '--destination_path', \
        help='Full path of the lncrna annotations location or destination, either where it is, or where it will be placed.')
    parser.add_argument('-o', '--output_filename', \
        help='Name of the output file, where the json dictionary will be written.')
    parser.add_argument('-f', '--force_download', 
        help='Forces download of lncrna annotations, even if previously downloaded. ' + \
             'Requires download_location to be set in order to work.', action="store_true")
    args = parser.parse_args()

    # print "Arguments are parsed."
    print "\ndownload_location is {:s}".format(str(args.download_location))
    print "display_name is {:s}".format(str(args.display_name))
    print "destination_path is {:s}\n".format(str(args.destination_path))
    root_annotations_dirname = None
    # FIX - Prob don't need annotations_was_downloaded. Not doing anything with it.
    # But it indicates success downloading the annotations, so maybe should be checking it.
    annotations_was_downloaded = False
    if (args.download_location != ""):
        annotations_directory, root_annotations_dirname, annotations_was_downloaded = \
            download_annotations(src_location=args.download_location, \
                           destination=args.destination_path, \
                           force_download=args.force_download)
    else:
        cannonical_destination = os.path.realpath(args.destination_path)
        if not os.path.exists(cannonical_destination):
            raise ValueError("Cannot find the Lncrna annotations.\n" + \
                "The directory does not exist:\n\t{:s}".format(annotations_directory))
        # If args.destination_path is a directory containing 
        # a subdirectory that contains the annotations files,
        # then we need to set the annotations_directory to be that subdirectory.
        files_in_destination_path = os.listdir(cannonical_destination)
        if (len(files_in_destination_path) == 1):
            path_to_file = "{:s}/{:s}".format(cannonical_destination, files_in_destination_path[0])
            if os.path.isdir(path_to_file):
                annotations_directory = path_to_file
            else:
                annotations_directory = cannonical_destination
        else:
            annotations_directory = cannonical_destination
        # Get the root_annotations_dirname of the annotations from the annotations_directory name.
        root_annotations_dirname = annotations_directory.split("/")[-1].split(".")[0]

    # Check if there is an actual Lncrna annotations file in the annotations_directory.
    print "\nThe location of the Lncrna annotations is {:s}.\n".format(annotations_directory)
    files_in_annotations_directory = set(os.listdir(annotations_directory))
    annotations_file_found = False
    annotations_file_path = annotations_directory
    """
    #Will need to change according to what you download for lncrna
    for filename in files_in_annotations_directory:
        if filename.split(".")[-1] == _lncrnaFileExtension:
            annotations_file_found = True
            # The centrifuge program wants the root name of the files to be final part of the path.
            annotations_file_path = "{:s}/{:s}".format(annotations_directory, filename.split(".")[0])
    """
    if not annotations_file_found:
        raise ValueError("Cannot find any Lncrna annotations files.\n" + \
            "The contents of the directory {:s} are:\n\t".format(annotations_directory) + \
            "\n\t".join(files_in_annotations_directory))

    # Set the display_name
    if (args.display_name is None) or (args.display_name == ""):
        # Use the root_annotations_dirname.
        if (root_annotations_dirname != None) and (root_annotations_dirname != ""):
            display_name = _CTAT_lncrnaDisplayNamePrefix + root_annotations_dirname
        else:
            display_name = _CTAT_lncrnaDisplayNamePrefix + _CTAT_lncrnaDir_Name
            print "WARNING: Did not set the display name. Using the default: {:s}".format(display_name_value)
    else:
        display_name = _CTAT_lncrna_annotations_DisplayNamePrefix + args.display_name
    display_name = display_name.replace(" ","_")

    # Set the unique_id
    datetime_stamp = datetime.now().strftime("_%Y_%m_%d_%H_%M_%S_%f")
    if (root_annotations_dirname != None) and (root_annotations_dirname != ""):
        unique_id = root_annotations_dirname + datetime_stamp
    else:
        unique_id = _CTAT_lncrnaDir_Name + datetime_stamp

    print "The Index's display_name will be set to: {:s}\n".format(display_name)
    print "Its unique_id will be set to: {:s}\n".format(unique_id)
    print "Its dir_path will be set to: {:s}\n".format(annotations_file_path)

    data_manager_dict = {}
    data_manager_dict['data_tables'] = {}
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName] = []
    data_table_entry = dict(value=unique_id, name=display_name, path=annotations_file_path)
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName].append(data_table_entry)

    # Temporarily the output file's dictionary is written for debugging:
    print "The dictionary for the output file is:\n\t{:s}".format(str(data_manager_dict))
    # Save info to json file. This is used to transfer data from the DataManager tool, to the data manager,
    # which then puts it into the correct .loc file (I think).
    # Remove the following line when testing without galaxy package.
    open(args.output_filename, 'wb').write(to_json_string(data_manager_dict))

if __name__ == "__main__":
    main()
