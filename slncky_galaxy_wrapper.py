#!/usr/bin/env python
import argparse
import sys
import os
#import sciedpiper.Commandline as commandline
import shutil

TOOLS = os.environ.get( 'TOOLS' )
EXTLIBS = os.environ.get( 'EXTLIBS' )

SLNCKY_DIR = os.path.join( TOOLS,'Trinity_CTAT','lncrna','slncky' )
LNCRNA_DIR = os.path.join( TOOLS,'Trinity_CTAT','lncrna' )

BEDTOOLS = '/N/soft/rhel6/bedtools/2.20.1/bin'
LASTZ = '/N/dc2/projects/galaxyshared/trinity/third_party_applications/lastz-distrib-1.03.73/bin'
LIFTOVER = '/N/dc2/projects/galaxyshared/trinity/third_party_applications/liftover'
SCIEDPIPER_HOME = '/N/dc2/projects/galaxyshared/trinity/SciEDPipeR-0.1.5/sciedpiper'

SLNCKY_PIPELINE_SCRIPT = os.path.join( LNCRNA_DIR, 'lncrna_discovery.py' )
CONFIGSTR = os.path.join( SLNCKY_DIR,'annotations.config' )

KCOPIPE_ERR = "kcopipe_runner.err"  
KCOPIPE_OUT = "kcopipe_runner.out"
KCOPIPE_RUNNER_SCRIPT = "kcopipe_runner.sh"
RUNNER_SCRIPT = "runner.sh"

def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bedfile", required = True ,help="bed12 file of transcripts")
    parser.add_argument("--assembly",required = True ,help="assembly")
    parser.add_argument("--out_prefix", default="slncky",help="out_prefix")
    parser.add_argument("--config", default=CONFIGSTR ,type=str, help="path to assembly.config file. default uses config file in same directory as slncky")
    parser.add_argument("--no_orth_search",action="store_true", help="flag if you only want to filter lncs but don\'t want to search for orthologs")
    parser.add_argument('--no_filter', action='store_true', help='flag if you don\'t want lncs to be filtered before searching for ortholog')
    parser.add_argument('--overwrite', action='store_true', help='forces overwrite of out_prefix.bed')
    parser.add_argument('--threads', type=int, help='number of threads. default = 5', default=5)
    parser.add_argument('--min_overlap', type=float, help='remove any transcript that overlap annotated coding gene > min_overlap%%. default = 0%%', default=0)
    parser.add_argument('--min_cluster', type=int, help='min size of duplication clusters to remove. default=2', default=2)
    parser.add_argument('--min_coding', type=float, help='min exonic identity to filter out transcript that aligns to orthologous coding gene. default is set by learning coding alignment distribution from data', default=0.1)
    parser.add_argument('--no_overlap', action='store_true', help='flag if you don\'t want to overlap with coding')
    parser.add_argument('--no_collapse', action='store_true', help='flag if you don\'t want to collapse isoforms')
    parser.add_argument('--no_dup', action='store_true', help='flag if don\'t want to align to duplicates')
    parser.add_argument('--no_self', action='store_true', help='flag if you don\'t want to self-align for duplicates')
    parser.add_argument('--no_coding', action='store_true', help='flag if you don\'t want to align to orthologous coding')
    parser.add_argument('--no_bg', action='store_true', help='flag if you don\'t want to compare lnc-to-ortholog alignments to a background. This flag may be useful if you want to do a \'quick-and-dirty\' run of the ortholog search.')
    parser.add_argument('--no_orf', action='store_true', help='flag if you don\'t want to search for orfs')
    parser.add_argument('--minMatch', type=float, help='minMatch parameter for liftover. default=0.1', default=0.1)
    parser.add_argument('--pad', type=int, help='# of basepairs to search up- and down-stream when lifting over lnc to ortholog', default=50000)
    parser.add_argument('--gap_open', type=str, default='200')
    parser.add_argument('--gap_extend', type=str, default='40')
    parser.add_argument('--web', action='store_true', help='flag if you want website written visualizing transcripts that were filtered out')
    parser.add_argument('--grid_system', default= 'uger' ,help='lsf or uger')
    parser.add_argument('--queue', default="long", help='long|short')
    parser.add_argument('--project', default="regevlab", help="regevlab|broad")
    parser.add_argument('--memory_required' , default="40", help="memory for grid")
    parser.add_argument('--html', help='for galaxy purpose only')
    parser.add_argument('--html_files_path',help='for galaxy purpose only')
    parser.add_argument('--can_lncs' , help='for galaxy purpose only' )
    parser.add_argument('--clust_info' , help='for galaxy purpose only' )
    parser.add_argument('--filt_info', help='for galaxy purpose only' )
    parser.add_argument('--lncs_bed', help='for galaxy purpose only' )
    parser.add_argument('--lncs_info', help='for galaxy purpose only' )
    parser.add_argument('--orfs', help='for galaxy purpose only' )
    parser.add_argument('--ortho_top', help='for galaxy purpose only' )
    parser.add_argument('--ortho', help='for galaxy purpose only' )
    args = parser.parse_args( )
    return args

def write_qsub_runner( args,slncky_cmd,runner_errfile,runner_outfile ):

    runner_list = [ "#! /bin/bash" + "\n"  ]
    runner_list.append( "\n" )

    runner_list.append( slncky_cmd )
    runner_script_path = RUNNER_SCRIPT 
    write_to_file( runner_list,runner_script_path )

    return runner_script_path

def write_to_file( lines_list,script_path ):

    with open( script_path,"w" ) as fh:
         writtenfname = fh.writelines( lines_list )


if __name__ == "__main__":
   args = get_arguments( )

   
   ######################
   ##Check for boolean values
   ######################
   args_param = [args.no_orth_search,args.no_filter,args.overwrite,args.no_overlap,
                 args.no_collapse,args.no_dup,args.no_self,args.no_coding,args.no_bg,
                 args.no_orf]

   boolean_args_list = ['--no_orth_search','--no_filter','--overwrite','--no_overlap',
                        '--no_collapse','--no_dup','--no_self','--no_coding','--no_bg','--no_orf']

   args_param_zip = zip( args_param,boolean_args_list )
   boolean_args_str = ""
   for param, arg_str in args_param_zip:
       if param:
          boolean_args_str = boolean_args_str + " " + arg_str 
            
   ######################
   ##Form slncky command
   ######################
   common_lst =   [ 
                      SLNCKY_PIPELINE_SCRIPT + " \\",
                      '--config ' + args.config + " \\",
                      '--threads ' + str( args.threads ) + " \\",
                      '--min_overlap ' + str( args.min_overlap ) + " \\",
                      '--min_cluster ' + str( args.min_cluster ) + " \\",
                      '--min_coding ' + str( args.min_coding ) + " \\",                       
                      '--bedtools ' + BEDTOOLS + " \\",
                      '--liftover ' +  LIFTOVER + " \\",
                      '--minMatch ' + str( args.minMatch ) + " \\",
                      '--pad ' + str( args.pad ) + " \\",
                      '--lastz ' + LASTZ +  " \\",
                      '--gap_open ' + args.gap_open + " \\",
                      '--gap_extend ' + args.gap_extend + " \\",
                      '--web ' + " \\",
                      '--bedfile ' + args.bedfile + " \\",
                      '--assembly ' + args.assembly + " \\", 
                      '--out_prefix ' + args.out_prefix + " \\",
                      '--update slncky.v1.0:' + SLNCKY_DIR  + " \\"] 
                      
   if boolean_args_str:
      common_lst.append( boolean_args_str )
   
   common_str = '\n'.join( common_lst )

   errorfile = 'pipe.err' 
   outfile = 'pipe.out' 

   kcopipe_script = write_qsub_runner( args,common_str,errorfile,outfile )
   wrp_cmd = "sh " + kcopipe_script


 
   #########################
   ##Copy slncky outputs to Galaxy assigned output files
   #########################
   condition = commandline.Commandline('sLNCkyPipeline').func_CMD( wrp_cmd,f_use_bash = False )

   if condition:
      current_wd = os.getcwd( )
      shutil.copy( os.path.join( current_wd,"slncky.EvolutionBrowser","browse.html" ), args.html )
      shutil.copytree( os.path.join( current_wd,"slncky.EvolutionBrowser" ), args.html_files_path )
      shutil.copy( os.path.join( current_wd,"slncky.canonical_to_lncs.txt" ), args.can_lncs )
      shutil.copy( os.path.join( current_wd,"slncky.filtered_info.txt" ), args.filt_info )
      shutil.copy( os.path.join( current_wd,"slncky.lncs.bed" ) , args.lncs_bed )
      shutil.copy( os.path.join( current_wd,"slncky.lncs.info.txt" ) , args.lncs_info )
      shutil.copy( os.path.join( current_wd,"slncky.orfs.txt" ), args.orfs )
      shutil.copy( os.path.join( current_wd,"slncky.orthologs.top.txt" ), args.ortho_top )
      shutil.copy( os.path.join( current_wd,"slncky.orthologs.txt" ), args.ortho )
      shutil.copy( os.path.join( current_wd,"slncky.cluster_info.txt" ), args.clust_info )
