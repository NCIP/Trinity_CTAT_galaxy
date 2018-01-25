#!/usr/bin/env python
# ref: https://galaxyproject.org/admin/tools/data-managers/how-to/define/

# Rewritten by H.E. Cicada Brokaw Dennis from a source downloaded from the toolshed and
# other example code on the web.
# This now allows downloading of a user selected library
# but only from the CTAT Genome Reference Library website.
# Ultimately we might want to allow the user to specify any location 
# from which to download.
# Users can create or download other libraries and use this tool to add them if they don't want
# or don't know how to add them by hand.

import argparse
import os
#import tarfile
#import urllib
import subprocess

from galaxy.util.json import from_json_string, to_json_string

# The following function is used by the Data Manager interface (.xml file) to get the
# filenames that are available online at broadinstitute.org
# Not sure best way to do it. This method parses the html looking for the filenames.
import urllib2
from HTMLParser import HTMLParser

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
    resource = urllib2.urlopen('https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/')
    theHTML = resource.read()
    filelist_parser = FileListParser()
    filelist_parser.feed(theHTML)
    # return a tuple of the filenames
    return tuple(filelist_parser.filenames)

# The following was used by the example program to get input parameters through the json.
# Just leaving here for reference.
#def get_reference_id_name(params):
#    genome_id = params['param_dict']['genome_id']
#    genome_name = params['param_dict']['genome_name']
#    return genome_id, genome_name
#
#def get_url(params):
#    trained_url = params['param_dict']['trained_url']
#    return trained_url

def download_from_BroadInst(src_filename, destination):
    # FIX - The name of this function is too narrow now. It does more than download.
    # Perhaps split function into its pieces and rename.
    # FIX - need to consider if this is a rerun of a failed processing or download
    # If the files that would be downloaded exist and are the correct size, we should
    # skip the download, also in post-processing we should see if the data has been
    # processed before, and whether the processed files are the correct size?
    # or do the functions themselves already check if the files are there and skip steps?
    # Maybe add a field for the user to indicate to ignore/delete previous data and
    # redownload and reprocess. In Notes to Galaxy Admin recommend that certain memory 
    # and computing resources are needed to generate the indexes.
    ctat_resource_lib = 'https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/' + src_filename
    # FIX - Check that the download directory is empty if it exists. 
    # why does it need to be empty? The downloaded file will be a single directory in that file.
    # Also, can we check if there is enough space on the device as well?
    # FIX - Also we want to make sure that destination is absolute fully specified path.
    cannonical_destination = os.path.realpath(destination)
    if os.path.exists(cannonical_destination):
        if not os.path.isdir(cannonical_destination):
            raise ValueError("The destination is not a directory: {:s}".format(cannonical_destination))
        # else all is good. It is a directory.
    else:
        # We need to create it.
        os.makedirs(cannonical_destination)
    # Get the list of files in the directory, so after we extract the archive we can find the one
    # that was extracted as the file that is not in this list.
    orig_files_in_destdir = set(os.listdir(cannonical_destination))
    #Download ref: https://dzone.com/articles/how-download-file-python
    #f = urllib2.urlopen(ctat_resource_lib)
    #data = f.read()
    #with open(filepath, 'wb') as code:
    #    code.write(data)
    # another way
    #full_filepath = os.path.join(destination, src_filename)
    #urllib.urlretrieve(url=ctat_resource_lib, filename=full_filepath)
    # Put the following into a try statement, so that if there is a failure 
    # something can be printed about it before reraising exception.
    #tarfile.open(full_filepath, mode='r:*').extractall()
    # But we want to transfer and untar it without storing the tar file, because that
    # adds all that much more space to the needed amount of free space.
    # so use subprocess to pipe the output of curl into tar.
    command = "curl {:s} | tar -xzvf - -C {:s}".format(ctat_resource_lib, cannonical_destination)
    try: # to run the command that downloads and extracts the file.
        command_output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        print "ERROR: Trying to run the following command:\n\t{:s}".format(command)
        print "================================================"
        print "\tOutput while running the command was:\n\n{:s}".format(e.output)
        print "================================================"
        raise
    # Get the root filename of the extracted file. It will be the file that was not in the directory
    # before we did the download and extraction.
    newfiles_in_destdir = set(os.listdir(cannonical_destination)) - orig_files_in_destdir
    found_filename = None
    for filename in newfiles_in_destdir:
        # If things are right there should just be one new file, the directory that was extracted.
        # But in case there was something that happened on the system that created other files,
        # the correct file's name should be a substring of the tar file that was downloaded.
        if filename in src_filename:
            found_filename = filename
    if found_filename is not None:
        ctat_genome_directory = cannonical_destination + "/" + found_filename
        if len(os.listdir(ctat_genome_directory)) == 1:
            # Then that one file is a subdirectory that should be the ctat_genome_directory.
            subdir_filename = os.listdir(ctat_genome_directory)[0]
            ctat_genome_directory += "/" + subdir_filename
    else:
        raise ValueError("ERROR: Could not find the extracted file in the destination directory:" + \
                         "\n\t{:s}".format(cannonical_destination))

    # In all downloaded libraries there is additional processing 
    # that needs to happen for gmap-fusion to work.
    command = "gmap_build -D {:s}/ -d ref_genome.fa.gmap -k 13 {:s}/ref_genome.fa".format( \
              ctat_genome_directory, ctat_genome_directory)
    try: # to run the command.
        command_output = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError as e:
        print "ERROR: While trying to process the genome library library:\n\t{:s}".format(command)
        print "================================================"
        print "\n\tOutput while running the command was:\n\n{:s}".format(e.output)
        print "================================================"
        raise

    # If the src_filename indicates it is a source file, as opposed to plug-n-play, 
    # then we need to do additional post processing on it with FusionFilter commands.
    if src_filename.split(".").contains("source_data"):
        # The use of conda to install the FusionFilter should make the following commands
        # available without the need to find out where FusionFilter resides. 
        # ${FusionFilter_HOME}/prep_genome_lib.pl \
        #    --genome_fa ref_genome.fa \
        #    --gtf ref_annot.gtf \
        #    --blast_pairs blast_pairs.gene_syms.outfmt6.gz \
        #    --fusion_annot_lib fusion_lib.dat.gz
        # ${FusionFilter_HOME}/util/index_pfam_domain_info.pl  \
        #     --pfam_domains PFAM.domtblout.dat.gz \
        #     --genome_lib_dir ctat_genome_lib_build_dir
        #
        # I don't know if we can run the programs without changing to the directory.
        # The instructions in https://github.com/FusionFilter/FusionFilter/wiki
        # say to change directory before running the commands.
        os.chdir(ctat_genome_directory)
        command = "prep_genome_lib.pl " + \
                    "--genome_fa ref_genome.fa " + \
                    "--gtf ref_annot.gtf " + \
                    "--blast_pairs blast_pairs.gene_syms.outfmt6.gz " + \
                    "--fusion_annot_lib fusion_lib.dat.gz"
        try: # to run the command.
            command_output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            print "ERROR: While trying to process the genome library:\n\t{:s}".format(command)
            print "================================================"
            print "\n\tOutput while running the command was:\n\n{:s}".format(e.output)
            print "================================================"
            raise
        command = "index_pfam_domain_info.pl " + \
                    "--pfam_domains PFAM.domtblout.dat.gz " + \
                    "--genome_lib_dir \"{:s}\"".format(ctat_genome_directory)
        try: # to run the command.
            command_output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            print "ERROR: While trying to process the genome library:\n\t{:s}".format(command)
            print "================================================"
            print "\n\tOutput while running the command was:\n\n{:s}".format(e.output)
            print "================================================"
            raise
    # end of post-processing for source_data files
    
    return ctat_genome_directory

def main():
    #Parse Command Line
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download', default="", \
        help='Do not use if you already have a CTAT Resource Library that this program downloads.')
    parser.add_argument('-g', '--genome_name', default="UNSPECIFIED_GenomeName", \
        help='Is used as the selector text of the entry in the data table.')
    parser.add_argument('-p', '--destination_path', \
        help='Full path of the CTAT Resource Library location or destination.')
    parser.add_argument('-o', '--output_filename', \
        help='Name of the output file, where the json dictionary will be written.')
    args = parser.parse_args()

    # All of the input parameters are written by default to the json output file prior to
    # this program being called.
    # But I do not get input values from the json file, but rather from command line.
    # Just leaving the following code as a comment, in case it might be useful to someone later.
    # The target_directory is the typical location where data managers put their data, but then
    # the typical model is to then copy it to the final location. With our files taking up so many 
    # GB of space, we don't want to move them around, but rather have the Galaxy Admin give us
    # the final location (the destination_path) where the files will be placed (or currently reside).
    #
    # params = from_json_string(open(output_filename).read())
    # target_directory = params['output_data'][0]['extra_files_path']
    # os.mkdir(target_directory)

    if args.download != "":
        ctat_genome_resource_lib_path = \
            download_from_BroadInst(src_filename=args.download, destination=args.destination_path)
    else:
        # FIX - probably should check if this is a valid path with an actual CTAT Genome Ref Lib there.
        ctat_genome_resource_lib_path = args.destination_path

    if (args.genome_name is None) or (args.genome_name == ""):
        genome_name = "GRCh38_gencode_v26"
    else:
        genome_name = args.genome_name
    # Set the table_entry_value to the basename of the directory path minus the extension. 
    # FIX - Need to make sure is unique. This is not good way to do it. Just doing it this way now for testing.
    table_entry_value = os.path.basename(ctat_genome_resource_lib_path).split(".")[0]
    data_manager_dict = {}
    data_manager_dict['data_tables'] = {}
    data_manager_dict['data_tables']['ctat_genome_ref_libs'] = []
    data_table_entry = dict(value=table_entry_value, name=genome_name, path=ctat_genome_resource_lib_path)
    data_manager_dict['data_tables']['ctat_genome_ref_libs'].append(data_table_entry)

    # Save info to json file. This is used to transfer data from the DataManager tool, to the data manager,
    # which then puts it into the correct .loc file (I think).
    open(args.output_filename, 'wb').write(to_json_string(data_manager_dict))

if __name__ == "__main__":
    main()

