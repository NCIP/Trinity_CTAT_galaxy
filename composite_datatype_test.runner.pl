#!/usr/bin/env perl

use strict;
use warnings;

for my $num (1, 2, 3) {

    open (my $ofh, ">test_file_$num.txt") or die "Error, cannot write to file";
    print $ofh "testing $num\n";
    close $ofh;
}

exit(0);

