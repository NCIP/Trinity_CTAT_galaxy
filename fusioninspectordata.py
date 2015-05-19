"""
FusionInspectorData 
"""
import logging
import os,os.path,re
import galaxy.datatypes.data
from galaxy.datatypes.images import Html
from galaxy.datatypes.binary import Binary
from galaxy import util
from galaxy.datatypes.metadata import MetadataElement
import sys

log = logging.getLogger(__name__)

class FusionInspectorData( Html ):
    """
    FusionInspector output files:

    FInspector.fusion_predictions.txt

    """
    file_ext = 'fusioninspectordata'
    is_binary = False
    composite_type = 'auto_primary_file'
    allow_datatype_change = False

    def __init__( self, **kwd ):
        Html.__init__( self, **kwd )

        log.debug("#########  FUSION INSPECTOR DATA ############\n\n\n")
        #sys.exit(1)

        self.add_composite_file('FInspector.fusion_predictions.txt', description = 'fusion predictions', mimetype = 'text/html', is_binary = False )

        self.add_composite_file('FInspector.fa', description = 'fusion contigs', mimetype = 'text/html', optional = True, is_binary = False )
        self.add_composite_file('FInspector.fa.fai', description = 'fusion contigs index', mimetype = 'text/html', optional = True, is_binary = False )
        
                
    def generate_primary_file( self, dataset = None ):
        """ 
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """

        log.debug("## generate_primary_file() for FusionInspectorData")

        rval = ['<html><head><title>CuffDiff Output</title></head>']
        rval.append('<body>')
        rval.append('<p/>CuffDiff Outputs:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files( dataset = dataset ).iteritems():
            fn = composite_name
            log.debug( "Velvet log info  %s %s %s" % ('JJ generate_primary_file',fn,composite_file))
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            if composite_file.get('description'):
                rval.append( '<li><a href="%s" type="text/plain">%s (%s)</a>%s</li>' % ( fn, fn, composite_file.get('description'), opt_text ) )
            else:
                rval.append( '<li><a href="%s" type="text/plain">%s</a>%s</li>' % ( fn, fn, opt_text ) )
        rval.append( '</ul></body></html>' )
        return "\n".join( rval )


    def regenerate_primary_file(self,dataset):
        """
        cannot do this until we are setting metadata 
        """
        
        log.debug("## regenerate_primary_file() for FusionInspectorData")
        
        flist = os.listdir(dataset.extra_files_path)
        rval = ['<html><head><title>CuffDiff Output</title></head>']
        rval.append('<body>')
        rval.append('<p/>CuffDiff Outputs:<p/><ul>')
        for i,fname in enumerate(flist):
            sfname = os.path.split(fname)[-1]
            rval.append( '<li><a href="%s" type="text/html">%s</a>' % ( sfname, sfname ) )
        rval.append( '</ul></body></html>' )
        f = file(dataset.file_name,'w')
        f.write("\n".join( rval ))
        f.write('\n')
        f.close()

    def set_meta( self, dataset, **kwd ):
        log.debug("## set_meta for FusionInspector ")
        Html.set_meta( self, dataset, **kwd )
        self.regenerate_primary_file(dataset)

    def sniff( self, filename ):
        return False

