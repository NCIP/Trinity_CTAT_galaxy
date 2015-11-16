#!/bin/bash -l

umask 0002

. /broad/software/scripts/useuse

reuse .samtools-0.1.19

fusions_list=$1
LEFT_FQ=$2
RIGHT_FQ=$3
OUTPUTDIR=$4
method=$5
trinity=$6

OUTPUTDIRLASTCHAR="${OUTPUTDIR: -1}"
if [ $OUTPUTDIRLASTCHAR != "/" ]
then
OUTPUTDIR="$OUTPUTDIR/"
fi

PIPEOFILENAME="pipe.out"
PIPEEFILENAME="pipe.err"

PIPERRFILE="$OUTPUTDIR$PIPEEFILENAME"
PIPEOUTFILE="$OUTPUTDIR$PIPEOFILENAME"

cmd="bsub -q regevlab -P finspector -e $PIPERRFILE -o $PIPEOUTFILE -K -R "rusage[mem=50]" $FUSION_DIR/FusionInspector --fusions $fusions_list --genome_lib $CTAT_GENOME_LIB --left_fq $LEFT_FQ --right $RIGHT_FQ --out_dir $OUTPUTDIR --out_prefix "finspector" --prep_for_IGV --align_utils $method" 

trinity_f=" --include_Trinity"

if [ $trinity = "true" ] 
then
combined_cmd=$cmd$trinity_f
$combined_cmd
else
$cmd
fi

##echo $bsub 
