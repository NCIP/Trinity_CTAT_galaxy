"""
CompositeDataTest
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

class CompositeDataTest( Html ):
    """


    """
    file_ext = 'compositedatatest'
    is_binary = False
    composite_type = 'basic' #'auto_primary_file'
    allow_datatype_change = False

    def __init__( self, **kwd ):
        Html.__init__( self, **kwd )

        log.debug("######### Composite Data Test ############\n\n\n")
        #sys.exit(1)

        self.add_composite_file('test_file_1.txt', description = 'test file 1', mimetype = 'text/html', is_binary = False )

        self.add_composite_file('test_file_2.txt', description = 'test file 2', mimetype = 'text/html', optional = True, is_binary = False )
        self.add_composite_file('test_file_3.txt', description = 'test file 3', mimetype = 'text/html', optional = True, is_binary = False )
        
                
    def generate_primary_file( self, dataset = None ):
        """ 
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """

        log.debug("## generate_primary_file() for Test data")

        rval = ['<html><head><title>CuffDiff Output</title></head>']
        rval.append('<body>')
        rval.append('<p/>CuffDiff Outputs:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files( dataset = dataset ).iteritems():
            fn = composite_name
            log.debug( "test generate html  %s %s %s" % ('generate_primary_file',fn,composite_file))
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            if composite_file.get('description'):
                rval.append( '<li><a href="%s" type="text/plain">%s (%s)</a>%s</li>' % ( fn, fn, composite_file.get('description'), opt_text ) )
            else:
                rval.append( '<li><a href="%s" type="text/plain">%s</a>%s</li>' % ( fn, fn, opt_text ) )
        rval.append( '</ul></body></html>' )
        return "\n".join( rval )


    def sniff( self, filename ):
        return False

