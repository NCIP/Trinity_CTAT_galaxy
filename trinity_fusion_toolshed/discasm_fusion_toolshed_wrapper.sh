#!/bin/bash -l

umask 0002

bam=$1
chimeric=$2
LEFT_FQ=$3
RIGHT_FQ=$4
OUTPUTDIR=$5

$DISCASM_DIR/DISCASM --aligned_bam $bam --chimeric_junctions $chimeric --left_fq $LEFT_FQ --right_fq $RIGHT_FQ --denovo_assembler OasesMultiK --out_dir $OUTPUTDIR 
