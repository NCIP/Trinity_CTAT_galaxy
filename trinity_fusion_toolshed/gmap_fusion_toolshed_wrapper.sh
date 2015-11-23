#!/bin/bash -l

umask 0002

discasm_trans=$1
LEFT_FQ=$2
RIGHT_FQ=$3
OUTPUTDIR=$4

$GMAP_FUSION_DIR/GMAP-fusion -T $discasm_trans --left_fq $LEFT_FQ --right_fq $RIGHT_FQ --genome_lib_dir $CTAT_GENOME_LIB --output $OUTPUTDIR 
