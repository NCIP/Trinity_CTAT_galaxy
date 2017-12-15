#!/usr/bin/env python
# ref: https://galaxyproject.org/admin/tools/data-managers/how-to/define/

# Rewritten by H.E. Cicada Brokaw Dennis from source downloaded from the toolshed.
# Eventually this should be modified to allow downloading of more than just the one library,
# to let the user select what library/location to download, but that would require the
# download tool to generate the list of libraries to download on the fly. Currently
# we are only using the one library.
# Users can create other ones locally and use this tool to add them if they don't want
# to add them by hand.

import argparse
import os
import tarfile
import urllib

from galaxy.util.json import from_json_string, to_json_string

# The following was used by prior program to get input parameters from the json.
# Just leaving here for reference.
#def get_reference_id_name(params):
#    genome_id = params['param_dict']['genome_id']
#    genome_name = params['param_dict']['genome_name']
#    return genome_id, genome_name
#
#def get_url(params):
#    trained_url = params['param_dict']['trained_url']
#    return trained_url

def download_from_BroadInst(destination):
    ctat_resource_lib = 'https://data.broadinstitute.org/Trinity/CTAT_RESOURCE_LIB/GRCh38_gencode_v26_CTAT_lib_Nov012017.plug-n-play.tar.gz'
    # FIX - Check that the download directory is empty if it exists. Also, can we check if there is enough space on the device as well?
    # FIX - Also we want to make sure that destination is absolute fully specified path.
    os.mkdir(destination)
    full_filepath = os.path.join(destination, 'GRCh38_gencode_v26_CTAT_lib_Nov012017.plug-n-play.tar.gz')

    #Download ref: https://dzone.com/articles/how-download-file-python
    #f = urllib2.urlopen(ctat_resource_lib)
    #data = f.read()
    #with open(filepath, 'wb') as code:
    #    code.write(data)

    urllib.urlretrieve(url=ctat_resource_lib, filename=full_filepath)
    # Put the following into a try statement, so that if there is a failure something can be printed about it before reraising exception.
    tarfile.open(full_filepath, mode='r:*').extractall()
    # FIX - There is additional processing that needs to happen for gmap-fusion to work.
    # Get the root filename of the extracted file. 
    # That directory is the actual destination that needs to be set as the ctat_genome_resource_library

def main():
    #Parse Command Line
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--download', action="store_true", \
        help='Do not use if you already have the CTAT Resource Library that this program downloads.')
    parser.add_argument('-g', '--genome_name', default="GRCh38_gencode_v26", \
        help='Is used as the selector text of the entry in the data table.')
    parser.add_argument('-p', '--destination_path', \
        help='Full path of the CTAT Resource Library location or destination.')
    parser.add_argument('-o', '--output_filename', \
        help='Name of the output file, where the json dictionary will be written.')
    args = parser.parse_args()

    # All of the input parameters are written by default to the output file prior to
    # this program being called.
    # But I do not get input values from the json file, but rather from command line.
    # Just leaving the following code as a comment, in case it might be useful to someone later.
    # params = from_json_string(open(filename).read())
    # target_directory = params['output_data'][0]['extra_files_path']
    # os.mkdir(target_directory)

    if args.download:
        ctat_genome_resource_lib_path = download_from_BroadInst(destination=args.destination_path)
    else:
        # FIX - probably should check if this is a valid path with an actual CTAT Genome Ref Lib there.
        ctat_genome_resource_lib_path = args.destination_path

    if (args.genome_name is None) or (args.genome_name == ""):
        genome_name = "GRCh38_gencode_v26"
    else:
        genome_name = args.genome_name

    data_manager_dict = {}
    data_manager_dict['data_tables'] = {}
    data_manager_dict['data_tables']['ctat_genome_ref_libs'] = []
    data_table_entry = dict(value="CTAT_RESOURCE_LIB", name=genome_name, path=ctat_genome_resource_lib_path)
    data_manager_dict['data_tables']['ctat_genome_ref_libs'].append(data_table_entry)

    # Save info to json file. This is used to transfer data from the DataManager tool, to the data manager,
    # which then puts it into the correct .loc file (I think).
    open(args.output_filename, 'wb').write(to_json_string(data_manager_dict))

if __name__ == "__main__":
    main()

