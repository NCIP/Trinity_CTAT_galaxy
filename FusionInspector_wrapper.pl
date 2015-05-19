#!/usr/bin/env perl

use strict;
use warnings;

my @x = @ARGV;

my $out_dir = pop @x;

my $cmd = join(" ", @x);
&process_cmd($cmd);

&process_cmd("mkdir -p $out_dir");

my @files = qw(
FInspector.igv.FusionJuncSpan
FInspector.consolidated.cSorted.bam
FInspector.junction_reads.bam.bed.sorted.bed.gz
Finspector.junction_reads.bam.bed.sorted.bed.gz
);


foreach my $file (@files) {
    rename($file, "$out_dir/$file") or die "Error, cannot rename file $file to $out_dir/$file";
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
