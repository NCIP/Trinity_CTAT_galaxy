#!/usr/bin/env perl

use strict;
use warnings;

my $CTAT_GALAXY_DATA = $ENV{CTAT_GALAXY_DATA} or die "Error, need CTAT_GALAXY_DATA env var set to dir under apache for linking to the galaxy data area";

my @x = @ARGV;

my $galaxy_data_file = pop @x;

my $out_dir = $galaxy_data_file;
$out_dir =~ s/\.dat$/_files/ or die "Error, cannot convert .dat to _files dir for $out_dir";

my $cmd = join(" ", @x);
&process_cmd($cmd);

&process_cmd("mkdir -p $out_dir");

my @files = qw(
cytoBand.txt
FInspector.gtf
FInspector.bed
FInspector.bed.sorted.bed.gz
FInspector.bed.sorted.bed.gz.tbi
FInspector.fa
FInspector.fa.fai
FInspector.fusion_predictions.txt
FInspector.igv.FusionJuncSpan
FInspector.consolidated.cSorted.bam
FInspector.consolidated.cSorted.bam.bai
FInspector.junction_reads.bam.bed.sorted.bed.gz
FInspector.junction_reads.bam.bed.sorted.bed.gz.tbi
FInspector.junction_reads.bam
FInspector.junction_reads.bam.bai
FInspector.spanning_reads.bam.bed.sorted.bed.gz
FInspector.spanning_reads.bam.bed.sorted.bed.gz.tbi
FInspector.spanning_reads.bam
FInspector.spanning_reads.bam.bai

);

=TrinGG
FInspector.gmap_trinity_GG.fusions.gff3.bed.sorted.bed.gz
FInspector.gmap_trinity_GG.fusions.gff3.bed.sorted.bed.gz.tbi
=cut

foreach my $file (@files) {
    &process_cmd("cp $file $out_dir/$file");    
}

# make a link to the out_dir from the apache data area
my $token = sprintf("%x", int(rand(time)) . int(rand(time)));
open (my $ofh, ">$out_dir/symtok.txt") or die "Error, cannot write to $out_dir/symtok.txt";
print $ofh $token;
close $ofh;

my $link_cmd = "ln -s $out_dir $CTAT_GALAXY_DATA/$token";
&process_cmd($link_cmd);


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
