#!/usr/bin/env python
import argparse
import sys
import os
import sciedpiper.Commandline as commandline
import shutil
from subprocess import Popen, PIPE

EXTLIBS = os.environ.get('EXTLIBS')
TOOLS = os.environ.get('TOOLS')
EXPRESSION_SCRIPT = os.path.join( TOOLS,"Trinity_CTAT","expression","trinity_ctat_expression.py" )
SCIEDPIPER_HOME = os.path.realpath( os.path.join( TOOLS,'SciEDPipeR-0.1.5','sciedpiper') )
KALLISTO_SCRIPT=os.path.realpath( os.path.join( EXTLIBS,'kallisto','kallisto_linux-v0.42.5') )
KCOPIPE_RUNNER_SCRIPT = "kcopipe_runner.sh"
KCOPIPE_ERR = "kcopipe_runner.err"
KCOPIPE_OUT = "kcopipe_runner.out"
ERRFILE = "pipe.err"
OUTFILE = "pipe.out"


def get_arguments( ):
    parser = argparse.ArgumentParser( )
    parser.add_argument("--annot_config", required=True ,help ="Annotation Config file" )
    parser.add_argument("--left_fq", required=True, help = "Left read fastq" )
    parser.add_argument("--right_fq", default="", help ="Right read fastq" )
    parser.add_argument("--bootstrap_samples", help ="Number of bootstrap samples" )
    parser.add_argument("--bias", action="store_true", help= "Perform sequence based bias correction")
    parser.add_argument("--threads", help ="Number of threads to use for bootstraping" )
    parser.add_argument("--seed", help ="Seed for the bootstrap sampling" )
    parser.add_argument("--out_dir", default="kallisto", help="out directory")
    parser.add_argument("--grid", default="uger", help="uger|lsf")
    parser.add_argument("--memory_required", default="10", help="memory required for grid")
    parser.add_argument("--queue", default="short", help="UGER: -q (short|long)")
    parser.add_argument("--project", default="regevlab",help="UGER: -P")
    args = parser.parse_args( )
    return args

def make_cmd( args ):
    kallisto_cmd = [ EXPRESSION_SCRIPT, 
                     "--left_fq",args.left_fq,"--right_fq",args.right_fq,
                     "--annot_config",args.annot_config,
                     "--bootstrap_samples",args.bootstrap_samples,"--threads",args.threads, 
                     "--seed",args.seed,"--out_dir",args.out_dir,"--update",
                     ( "kallisto_script:" + KALLISTO_SCRIPT ) ]
    if args.bias:
       kallisto_cmd.extend( "--bias" )
    
    wrp_cmd = " ".join(kallisto_cmd)
    print "Kallisto cmd is",wrp_cmd
    return wrp_cmd

def write_to_file( lines_list,script_path ):

    with open( script_path,"w" ) as fh:
         writtenfname = fh.writelines( lines_list )


if __name__ == "__main__":
   args = get_arguments( )
   #if not os.path.exists(args.out_dir):
   #        os.makedirs(args.out_dir)
   wrp_cmd = make_cmd( args )
   condition = commandline.Commandline( 'ExpressionPipeline' ).func_CMD( wrp_cmd,f_use_bash = False )
   if not ( ( os.path.join(args.out_dir,"kallisto","abundance.tsv")).st_size == 0 ):
      print "SUCCESS"
   else:
      print "FAIL"
      exit( 256 )


