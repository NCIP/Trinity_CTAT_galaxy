#!/usr/bin/env perl

use strict;
use warnings;

my @x = @ARGV;

my $out_dir = pop @x;

my $cmd = join(" ", @x);
&process_cmd($cmd);

&process_cmd("mkdir -p $out_dir");

my @files = qw(
FInspector.fa
FInspector.fa.fai
FInspector.fusion_predictions.txt
FInspector.igv.FusionJuncSpan
FInspector.consolidated.cSorted.bam
FInspector.consolidated.cSorted.bam.bai
FInspector.junction_reads.bam.bed.sorted.bed.gz
FInspector.junction_reads.bam.bed.sorted.bed.gz.tbi
FInspector.junction_reads.bam.bed.sorted.bed.gz
FInspector.junction_reads.bam.bed.sorted.bed.gz.tbi
FInspector.gmap_trinity_GG.fusions.gff3.bed.sorted.bed.gz
FInspector.gmap_trinity_GG.fusions.gff3.bed.sorted.bed.gz.tbi
);


foreach my $file (@files) {
    &process_cmd("cp $file $out_dir/$file");    
}


exit(0);




####
sub process_cmd {
    my ($cmd) = @_;
    
    my $ret = system($cmd);
    if ($ret) {
        die "Error, CMD: $cmd died with ret $ret";
    }
    
    return;
}
