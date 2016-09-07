#!/bin/bash -l

umask 0002

fusion_file=$1

$FUSION_ANNOTATOR/FusionAnnotator --fusion_annot_lib $FUSION_ANNOTATOR/Hg19_CTAT_fusion_annotator_lib --annotate $fusion_file >> annotation.txt

