#!/usr/bin/env python
import argparse
import sys
import os
import sciedpiper.Commandline as commandline
import shutil
from subprocess import Popen, PIPE

EXTLIBS = os.environ.get('EXTLIBS')
TOOLS = os.environ.get('TOOLS')
STRINGTIE_SCRIPT = os.path.realpath( os.path.join( EXTLIBS, 'stringtie-1.2.2.Linux_x86_64') )
STRINGTIE_DIR = os.path.join( TOOLS,"Trinity_CTAT","genome_guided_transcript_reconstruction" )
STRINGTIE_CTAT_SCRIPT = os.path.join( TOOLS,"Trinity_CTAT","genome_guided_transcript_reconstruction","transcript_reconstruction.py" )

SCIEDPIPER_HOME = os.path.realpath( os.path.join( TOOLS,'SciEDPipeR-0.1.5','sciedpiper') )

KCOPIPE_RUNNER_SCRIPT = "kcopipe_runner.sh"
KCOPIPE_ERR = "kcopipe_runner.err"
KCOPIPE_OUT = "kcopipe_runner.out"
ERRFILE = "pipe.err"
OUTFILE = "pipe.out"


def get_arguments( ):
    parser = argparse.ArgumentParser( )
    parser.add_argument("--bam_file", required=True ,help ="Aligned Bam file" )
    parser.add_argument("--ref_annot", required=True , help="Reference annotation")
    parser.add_argument("--output_gtf", required=True , help="Output GTF")
    parser.add_argument("--output_bed", required=True , help="Output BED")
    parser.add_argument("--grid", default="uger", help="uger|lsf")
    parser.add_argument("--memory_required", default="20", help="memory required for grid")
    parser.add_argument("--queue", default="short", help="UGER: -q (short|long)")
    parser.add_argument("--project", default="regevlab",help="UGER: -P")
    args = parser.parse_args( )
    return args

def make_cmd( args ):

    stringtie_cmd = [ STRINGTIE_CTAT_SCRIPT, 
                     "--ref_annot",args.ref_annot,
                     "--bam_file",args.bam_file,
                     "--output_gtf",args.output_gtf,
                     "--output_bed",args.output_bed,
                     "--update",
                     ( "stringtie:" + STRINGTIE_SCRIPT + ",gtf2bed.py:" + STRINGTIE_DIR ) ]

    cmdstr = " ".join(stringtie_cmd) 
    print "Stringtie command: ", cmdstr
    return cmdstr

def write_to_file( lines_list,script_path ):

    with open( script_path,"w" ) as fh:
         writtenfname = fh.writelines( lines_list )


if __name__ == "__main__":
   args = get_arguments( )
   #if not os.path.exists(args.out_dir):
   #        os.makedirs(args.out_dir)
   wrp_cmd = make_cmd( args )
   condition = commandline.Commandline( 'Stringtie' ).func_CMD( wrp_cmd,f_use_bash = False )
