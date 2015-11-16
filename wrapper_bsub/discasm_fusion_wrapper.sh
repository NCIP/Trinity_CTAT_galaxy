#!/bin/bash -l

umask 0002

bam=$1
chimeric=$2
LEFT_FQ=$3
RIGHT_FQ=$4
OUTPUTDIR=$5

OUTPUTDIRLASTCHAR="${OUTPUTDIR: -1}"
if [ $OUTPUTDIRLASTCHAR != "/" ]
then
OUTPUTDIR="$OUTPUTDIR/"
fi

PIPEOFILENAME="pipe.out"
PIPEEFILENAME="pipe.err"

PIPERRFILE="$OUTPUTDIR$PIPEEFILENAME"
PIPEOUTFILE="$OUTPUTDIR$PIPEOFILENAME"

bsub -q regevlab -P discasm -e $PIPERRFILE -o $PIPEOUTFILE -K -R "rusage[mem=50]" $DISCASM_DIR/DISCASM --aligned_bam $bam --chimeric_junctions $chimeric --left_fq $LEFT_FQ --right_fq $RIGHT_FQ --denovo_assembler OasesMultiK --out_dir $OUTPUTDIR 
