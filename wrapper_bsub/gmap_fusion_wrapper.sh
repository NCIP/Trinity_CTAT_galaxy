#!/bin/bash -l

umask 0002

discasm_trans=$1
LEFT_FQ=$2
RIGHT_FQ=$3
OUTPUTDIR=$4

OUTPUTDIRLASTCHAR="${OUTPUTDIR: -1}"
if [ $OUTPUTDIRLASTCHAR != "/" ]
then
OUTPUTDIR="$OUTPUTDIR/"
fi

PIPEOFILENAME="pipe.out"
PIPEEFILENAME="pipe.err"

PIPERRFILE="$OUTPUTDIR$PIPEEFILENAME"
PIPEOUTFILE="$OUTPUTDIR$PIPEOFILENAME"

bsub -q regevlab -P gmap -e $PIPERRFILE -o $PIPEOUTFILE -K -R "rusage[mem=50]" $GMAP_FUSION_DIR/GMAP-fusion -T $discasm_trans --left_fq $LEFT_FQ --right_fq $RIGHT_FQ --genome_lib_dir $CTAT_GENOME_LIB --output $OUTPUTDIR 
