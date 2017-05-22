import sys, os, subprocess

TRINITY_BASE_DIR = ""
if os.environ.has_key('TRINITY_HOME'):
    TRINITY_BASE_DIR = os.environ['TRINITY_HOME'];
else:
    sys.stderr.write("You must set the environmental variable TRINITY_BASE_DIR to the base installation directory of Trinity before running this");
    sys.exit()

usage= "usage: " + sys.argv[0] + " " + "edgeR.tar.gz " + "TMM_normalized_FPKM_matrix " + "P-value " + "C-value"
print sys.argv 
print usage 
print " "

if len(sys.argv)<5:
	print "Require atleast two parameters"
else:
	print "All good- command going ahead"
print " "

Normalized_Matrix=sys.argv[2]
Pvalue=sys.argv[3]
Cvalue=sys.argv[4]

def run_command(cmd):
	print "The command used: " + cmd
	pipe= subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE)
        pipe.wait()
	ret= pipe.returncode
	if ret:
		print "command died: " + str(ret)
                print pipe.stderr.readlines()
                sys.exit(1)
	else:
		return
print " "

Final_tar_gz= "edgeR.tar.gz"
run_command("cp "+ sys.argv[1] + " " + "Final_tar_gz")
run_command("tar -xvf " + "Final_tar_gz")
run_command("mv " + "edgeR_results" + "/* ." )

# run the analyze command
cmd= TRINITY_BASE_DIR + "/Analysis/DifferentialExpression/analyze_diff_expr.pl "+ "--matrix " +  Normalized_Matrix + " -P " +  Pvalue + " -C " + Cvalue
run_command(cmd)

origMatrixName= "diffExpr.P" + Pvalue + "_" + "C" + Cvalue + ".matrix"
# diffExpr.P0.001_C2.0.matrix
run_command("mv " + origMatrixName + " diffExpr.matrix")

SampleCorName= "diffExpr.P" + Pvalue + "_" + "C" + Cvalue + ".matrix.log2.sample_cor.dat"
# diffExpr.P0.001_C2.0.matrix.log2.sample_cor.dat
run_command("mv " + SampleCorName + " diffExpr.matrix.log2.sample_cor.dat")

CorMatrix= "diffExpr.P" + Pvalue + "_" + "C" + Cvalue + ".matrix.log2.sample_cor_matrix.pdf"
# diffExpr.P0.001_C2.0.matrix.log2.sample_cor_matrix.pdf
run_command("mv " + CorMatrix + " diffExpr.matrix.log2.sample_cor_matrix.pdf")

Heatmap= "diffExpr.P" + Pvalue + "_" + "C" + Cvalue + ".matrix.log2.centered.genes_vs_samples_heatmap.pdf"
#diffExpr.P0.001_C2.0.matrix.log2.centered.genes_vs_samples_heatmap.pdf
run_command("mv " + Heatmap + " diffExpr.matrix.log2.centered.genes_vs_samples_heatmap.pdf")

sys.exit(0)
