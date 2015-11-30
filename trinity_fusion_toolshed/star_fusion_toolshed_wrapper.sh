#!/bin/bash -l

umask 0002


LEFT_FQ=$1
RIGHT_FQ=$2
OUTPUTDIR=$3

GENOME_LIB=$CTAT_GENOME_LIB

$STAR_FUSION_DIR/STAR-Fusion --genome_lib_dir $GENOME_LIB --left_fq $LEFT_FQ --right_fq $RIGHT_FQ --output_dir $OUTPUTDIR
