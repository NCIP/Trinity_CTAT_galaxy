# Trinity_CTAT_galaxy
Files needed for Galaxy tools used to run Trinity_CTAT workflows.
This repository is the source repository for the user trinity_ctat's
tools uploaded to the Galaxy Toolshed.

## FIX The below information is likely to be out of date at present. FIX ##


## Environment Variables

The following environment variables are needed by various tools in this suite:

FUSION_RESOURCES - contains gencode19 gtf files, bowtie indices, Hg19 fasta and fai files, star indices and gmap indices files for Fusion tools.
(Not located in git; do not include in git).

MUTATION_RESOURCES - contains jar files for mutation as well as Hg19 fasta, bed and star indices; required vcf files and cravat files.
(Not located in git; do not include in git).

TOOLS - the folder that contains Trinity_CTAT and SciEDPipeR

EXTLIBS - A location that contains external libraries and executables needed for Trinity_CTAT tools to run

TRINTOOLS - usually the same as EXTLIBS, contains the folders DISCASM, STAR-FUSION, FusionInspector, etc

## Tool-specific changes

Fusion Inspector
Make sure STAR is in your path when using fusion inspector.

SLNCKY
In slncky_galaxy_wrapper.py, the following paths will need to be filled in:

BEDTOOLS = ''    
LASTZ = ''    
LIFTOVER = ''    
SCIEDPIPER_HOME = ''    

IU specific changes have been saved here; be careful to test your own setup if you use these.


