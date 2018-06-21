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

#_CTAT_lncrnaIndexPage_URL = 'https://data.broadinstitute.org/Trinity/CTAT/lncrna/annotations.tar.gz'
_CTAT_lncrnaDownload_URL = 'https://data.broadinstitute.org/Trinity/CTAT/lncrna/annotations.tar.gz'
_CTAT_lncrnaTableName = 'ctat_lncrna_annotations'
_CTAT_lncrnaDir_Name = 'annotations'
_CTAT_lncrna_DisplayNamePrefix = 'CTAT_lncrna_annotations_'
_lncrnaFileExtension = 'lc'
_NumBytesNeededForAnnotations = 2147483648 # Number of bytes
#_DownloadFileSize = 5790678746 # 5.4 Gigabytes.
_Download_TestFile = 'write_testfile.txt'
_DownloadSuccessFile = 'download_succeeded.txt'

'''
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
'''


def get_ctat_lncrna_annotations_locations():
    # For dynamic options need to return an interable with contents that are tuples with 3 items.
    # Item one is a string that is the display name put into the option list.
    # Item two is the value that is put into the parameter associated with the option list.
    # Item three is a True or False value, indicating whether the item is selected.
    options = []
    # open the url and retrieve the filenames of the files in the directory.
    # resource = urllib2.urlopen(_CTAT_lncrnaIndexPage_URL)
    # theHTML = resource.read()
    # filelist_parser = FileListParser()
    # filelist_parser.feed(theHTML)
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
        if (num_avail_bytes < _NumBytesNeededForAnnotations):
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
        command = "curl --silent {:s} | tar -xzf - -C {:s} --strip 1".format(src_location, cannonical_destination) 
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
    ## Changed from found_filenames 
    if (len(files_in_destdir) >= 4):
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
    print "\ndownload_location is {:s}".format(str(_CTAT_lncrnaDownload_URL))
    print "display_name is {:s}".format(str(args.display_name))
    print "destination_path is {:s}\n".format(str(args.destination_path))
    root_annotations_dirname = None
    # FIX - Prob don't need annotations_was_downloaded. Not doing anything with it.
    # But it indicates success downloading the annotations, so maybe should be checking it.
    annotations_was_downloaded = False
    if (_CTAT_lncrnaDownload_URL != ""):
        annotations_directory, root_annotations_dirname, annotations_was_downloaded = \
            download_annotations(src_location=_CTAT_lncrnaDownload_URL, \
                           destination=args.destination_path, \
                           force_download=args.force_download)
    else:
        cannonical_destination = os.path.realpath(args.destination_path)
        # If args.destination_path is a directory containing 
        # a subdirectory that contains the annotations files,
        # then we need to set the annotations_directory to be that subdirectory.
        if not os.path.exists(cannonical_destination):
           raise ValueError("Cannot find the Lncrna annotations.\n" + \
               "The directory does not exist:\n\t{:s}".format(cannonical_destination))
        files_in_destination_path = os.listdir(cannonical_destination)
        if (len(files_in_destination_path) == 4):
            #path_to_file = "{:s}/{:s}".format(cannonical_destination, files_in_destination_path[0])
            #if os.path.isdir(path_to_file):
            #    annotations_directory = path_to_file
            #else:
            annotations_directory = cannonical_destination
        else:
            raise ValueError("Contents of destination directory not equal to expected - 4")
            #annotations_directory = cannonical_destination
        # Get the root_annotations_dirname of the annotations from the annotations_directory name.
        root_annotations_dirname = annotations_directory.split("/")[-1].split(".")[0]

    # Check if there is an actual Lncrna annotations file in the annotations_directory.
    print "\nThe location of the Lncrna annotations is {:s}.\n".format(annotations_directory)
    files_in_annotations_directory = set(os.listdir(annotations_directory))
    annotations_file_found = False
    annotations_file_path_mm9 = annotations_directory+"/annotations.config"
    annotations_file_path_mm10 = annotations_directory+"/annotations.config"
    annotations_file_path_hg19 = annotations_directory+"/annotations.config"
    annotations_file_path_hg38 = annotations_directory+"/annotations.config"

    # Set the display_name
    # if (args.display_name is None) or (args.display_name == ""):
        # Use the root_annotations_dirname.
        # print "display_name_ok$$$$$$$"
    
    if (root_annotations_dirname != None) and (root_annotations_dirname != ""):
        print "root_annotations_ok%%%%"
        display_name_hg19 = "hg19"
        display_name_hg38 = "hg38"
        display_name_mm10 = "mm10"
        display_name_mm9 = "mm9"
    else:
        display_name = _CTAT_lncrna_DisplayNamePrefix + _CTAT_lncrnaDir_Name
        print "WARNING: Did not set the display name. Using the default: {:s}".format(display_name_value)
    #else:
    #    display_name = _CTAT_lncrna_DisplayNamePrefix + args.display_name
    # display_name = display_name.replace(" ","_")

    # Set the unique_id
    datetime_stamp = datetime.now().strftime("_%Y_%m_%d_%H_%M_%S_%f")
    if (root_annotations_dirname != None) and (root_annotations_dirname != ""):
        hg19_unique_id = "ctat_lncrna_hg19" + datetime_stamp
        mm10_unique_id = "ctat_lncrna_mm10" + datetime_stamp
        mm9_unique_id = "ctat_lncrna_mm9" + datetime_stamp
        hg38_unique_id = "ctat_lncrna_hg38" + datetime_stamp
    else:
        unique_id = _CTAT_lncrnaDir_Name + datetime_stamp

    print "The hg19 Index's display_name will be set to: {:s}\n".format(display_name_hg19)
    print "Its hg19 unique_id will be set to: {:s}\n".format(hg19_unique_id)
    print "Its hg19 dir_path will be set to: {:s}\n".format(annotations_file_path_hg19)


    print "The hg38 Index's display_name will be set to: {:s}\n".format(display_name_hg38)
    print "Its hg38 unique_id will be set to: {:s}\n".format(hg38_unique_id)
    print "Its hg38 dir_path will be set to: {:s}\n".format(annotations_file_path_hg38)


    print "The mm9 Index's display_name will be set to: {:s}\n".format(display_name_mm9)
    print "Its mm9 unique_id will be set to: {:s}\n".format(mm9_unique_id)
    print "Its mm9 dir_path will be set to: {:s}\n".format(annotations_file_path_mm9)


    print "The mm10 Index's display_name will be set to: {:s}\n".format(display_name_mm10)
    print "Its mm10 unique_id will be set to: {:s}\n".format(mm10_unique_id)
    print "Its mm10 dir_path will be set to: {:s}\n".format(annotations_file_path_mm10)

    data_manager_dict = {}
    data_manager_dict['data_tables'] = {}
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName] = []
    data_table_entry_mm9 = dict(value=display_name_mm9, name=display_name_mm9, path=annotations_file_path_mm9)
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName].append(data_table_entry_mm9)

    data_table_entry_mm10 = dict(value=display_name_mm10, name=display_name_mm10, path=annotations_file_path_mm10)
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName].append(data_table_entry_mm10)

    data_table_entry_hg19 = dict(value=display_name_hg19, name=display_name_hg19, path=annotations_file_path_hg19)
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName].append(data_table_entry_hg19)

    data_table_entry_hg38 = dict(value=display_name_hg38, name=display_name_hg38, path=annotations_file_path_hg38)
    data_manager_dict['data_tables'][_CTAT_lncrnaTableName].append(data_table_entry_hg38)

    # Temporarily the output file's dictionary is written for debugging:
    print "The dictionary for the output file is:\n\t{:s}".format(str(data_manager_dict))
    # Save info to json file. This is used to transfer data from the DataManager tool, to the data manager,
    # which then puts it into the correct .loc file (I think).
    # Remove the following line when testing without galaxy package.
    open(args.output_filename, 'wb').write(to_json_string(data_manager_dict))

if __name__ == "__main__":
    main()
