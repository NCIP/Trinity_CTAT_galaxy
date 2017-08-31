#!/usr/bin/env python

'''
trinity_runner.py
This program is used as a wrapper for Trinity to allow an automatic rerun of failed jobs. It takes arguments for a typical Trinity run:
~ Required args ~
Input files - single or paired (left and right)
File type (fasta, fastq)
Max memory - this I need to derive somehow from the dynamic runner using Galaxy slots

~ Optional args ~
Output directory - this allows users to run the same job over in case it walltime'd out or failed for recoverable reasons.

 --
Created Tuesday, 7 March 2017.
Carrie Ganote

Licensed to Indiana University under Creative Commons 3.0
'''
import subprocess32
import argparse
import logging as log
import sys
import os
import errno
from datetime import datetime

TRINITY_OUT_DIR = "trinity_out_dir"

def main(*args):
    parser = argparse.ArgumentParser(description="")
    parser.add_argument("-o","--output", help="Name of output directory")
    parser.add_argument("-q","--seqType", help="Type of reads; fa or fq")
    parser.add_argument("-m","--max_memory", help="How much memory to allocate? Or maybe how many cpus?")
    parser.add_argument("-p","--mem_per_cpu", help="Memory PER CPU, in GB, in case we want to multiply mem x cpu at runtime")
    parser.add_argument("-s","--single", help="Single read file input")
    parser.add_argument("-l","--left", help="Left read file from paired inputs")
    parser.add_argument("-r","--right", help="Right read file from paired inputs")
    parser.add_argument("-v","--verbose", help="Enable debugging messages to be displayed", action='store_true')
    parser.add_argument("-g","--log", help="Log file")
    parser.add_argument("-t","--timing", help="Timing file, if it exists", default=None)
    parser.add_argument("-d","--dir", help="if supplying a rerunnable job, this is the (hopefully unique) name of the directory to run it in.")
    parser.add_argument("-u","--user", help="Username to run job under")
    parser.add_argument("-f","--fullpath", help="if supplying a rerunnable job, this is the full path (except the user and dir names) to run the job in.")
    parser.add_argument("-c","--CPU", help="CPUs, either a hard coded numer or from Galaxy slots")
#    parser.add_argument("-","--", help="")
    args = parser.parse_args()

    if args.verbose:
        log.basicConfig(format='%(message)s',level=log.DEBUG)
    cmd = ["Trinity"]

    ### Add rerun ability ###########################################
    # This variable tells us later whether to copy the files back to the job working directory
    copyback = False
    if args.dir and args.user and args.fullpath:
        cleandir = args.dir
        chars = "\\`*_{}[]()>#+-.!$&;| "
        for c in chars:
            if c in cleandir:
                cleandir = cleandir.replace(c, "_")
        rerunPath = "%s/%s/%s" % (args.fullpath, args.user, cleandir)
        print "Rerunpath is ",rerunPath
        try:
            os.makedirs(rerunPath)
            print "Created dir ",rerunPath
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(rerunPath):
                pass
            else:
                raise
        copyback = os.getcwd()
        outdir = copyback + "/" + TRINITY_OUT_DIR
        try:
            os.makedirs(outdir)
            print "Created dir ",outdir
        except OSError as exc:
            if exc.errno == errno.EEXIST and os.path.isdir(outdir):
                pass
            else:
                raise
        os.chdir(rerunPath)

    ### Add information for reads ###################################
    if args.left and args.right:
        cmd += ["--left",args.left,"--right", args.right]
    elif args.single:
        cmd += ["--single",args.single]
    else:
        raise Exception ("Need input files in order to run Trinity!")

    ### Add seqtype ##################################################
    if args.seqType:
        cmd += ["--seqType",args.seqType]
    else:
        raise Exception ("Please specify a file type for your reads!")

    ### Memory and CPU management ####################################
    if args.mem_per_cpu and not args.max_memory:
        if args.CPU:
            memry = int(args.CPU) * int(args.mem_per_cpu)
            memstr = "%dG" % (memry)
            cmd += ["--max_memory",memstr]
        else:
            memry = 2 * int(args.mem_per_cpu)
            memstr = "%dG" % (memry)
            cmd += ["--max_memory",memstr]
    elif args.max_memory and not args.mem_per_cpu:
        cmd += ["--max_memory",args.max_memory]
    else:
        raise Exception ("Please pick Memory per cpu, or max mem, but not both.")
    if args.CPU:
        cmd += ["--CPU", args.CPU]
    
    ### Enough args, let's run it ####################################
    print "About to write to %s" % args.log
    out = open(args.log, 'w')
    totalattempts = attempts = 2
    ec = 1
    finish = 1
    out.write("Command is:\n%s\n" % (" ".join(cmd)))

    ### There is definitely some value in running the job more than once, especially if it dies for stupid reasons.. ###
    while ec != 0 and attempts > 0 and finish != 0:

        dt = datetime.now()
        dtstr = dt.strftime("%d/%m/%y %H:%M")
        out.write("Beginning attempt %d of Trinity job at %s\n" % (totalattempts - attempts +1, dtstr) )
        attempts -= 1
        ec = subprocess32.call(cmd, shell=False, stdin=None, stdout=out, stderr=out, timeout=None)       
        out.write("Trinity exited with status %d\n" % ec)

        greplog = open("greplog", 'w')
        cmds = ["grep", 'All commands completed successfully', args.log]
        finish = subprocess32.call(cmds,shell=False,  stdin=None, stdout=greplog, stderr=greplog, timeout=None)
        greplog.close()
        out.write("Finished and found the success command with grep code %d\n" % finish)

    if ec == 0 and args.timing is not None:
        if copyback is not False:
            cwd = os.getcwd()
            dest = copyback + "/" + TRINITY_OUT_DIR + "/Trinity.fasta"
            src = cwd + "/" + TRINITY_OUT_DIR + "/Trinity.fasta"
            print "copying trinity outputs from %s to %s" % (src, dest)
            os.symlink(src, dest)

        #copy the timing file into the log
        try: 
            handle = open (args.timing, 'r')
            for line in handle:
                out.write(line)
            handle.close()
        except (OSError, IOError) as e:
            print "Oops, no timing file found? ",e


    out.close()
    exit (ec)
 
if __name__ == "__main__":
    main(*sys.argv)

