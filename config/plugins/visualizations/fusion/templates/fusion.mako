<!DOCTYPE html>

<html lang="en">
<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <meta name="description" content="Trintiy CTAT visualization for Fusions in discovered RNA-Seq.">
    <meta name="author" content="Brian Haas,Timothy Tickle">
    <title>${hda.name} | ${visualization_name}</title>

    <!-- CSS -->
    <!-- jQuery UI CSS -->
    <link rel="stylesheet" type="text/css" href="//ajax.googleapis.com/ajax/libs/jqueryui/1.11.3/themes/smoothness/jquery-ui.css"/>
    <!-- Bootstrap CSS -->
    <link rel="stylesheet" type="text/css" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">
    <!-- Font Awesome CSS -->
    <link rel="stylesheet" type="text/css" href="//maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/font-awesome.min.css">
    <!-- IGV CSS -->
    <link rel="stylesheet" type="text/css" href="//igv.org/web/beta/igv.css">
    <!-- inspector css -->
    <link rel="stylesheet" type="text/css" href="${h.url_for('/plugins/visualizations/fusion/static/css/inspector.css')}">
    <!-- Spinner from //www.css-spinners.com/spinner/spinner -->
    <link rel="stylesheet" type="text/css" href="//www.css-spinners.com/css/spinner/spinner.css">
    <!-- Associated with the Data Table -->
    <link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/1.10.8/css/dataTables.bootstrap.min.css">

    <!-- Scripts -->
    <!-- jQuery JS -->
    <script type="text/javascript" src="${h.url_for('//ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js')}"></script>
    <script type="text/javascript" src="${h.url_for('//ajax.googleapis.com/ajax/libs/jqueryui/1.11.3/jquery-ui.min.js')}"></script>
    <!-- IGV JS-->
    <script type="text/javascript" src="${h.url_for('/plugins/visualizations/igv/static/scripts/igv-all.js')}"></script>
    <!--<script type="text/javascript" src="${h.url_for('//igv.org/web/beta/igv-beta.js')}"></script>-->
    <!-- Data Table -->
    <script type="text/javascript" src="${h.url_for('https://cdn.datatables.net/1.10.8/js/jquery.dataTables.min.js')}"></script>
    <script type="text/javascript" src="${h.url_for('https://cdn.datatables.net/1.10.8/js/dataTables.bootstrap.min.js')}"></script>
    <!-- Bootstrap JS -->
    <script type="text/javascript" src="${h.url_for('https://maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js')}"></script>
</head>    
<body>
    <!-- Header (info) -->
    <div class="constainer-fluid" id="sampleHeader" style="background-color: #E7E7EF">
        <nav class="navbar navbar-default" style="background-color: #E7E7EF">
            <!--<div class="col-xs-3" id="sampleId"><p class="navbar-text"><b>Sample:</b></p></div>-->
            <div class="col-xs-3" id="FusionNameDetail"><p class="navbar-text"><b>Fusion Name:</b> Not Selected</p></div>
            <div class="col-xs-3" id="FusionJunctionDetail"><p class="navbar-text"><b>Junction Read Count:</b> Not Selected</p></div>
            <div class="col-xs-3" id="FusionSpanningDetail"><p class="navbar-text"><b>Spanning Read Count:</b> Not Selected</p></div>
        </nav>
    </div>
    <!-- End fusion details -->
    <hr>

    <!-- Start tabs -->
    <!-- Start tabs header -->
    <ul id="tabDescription" class="nav nav-tabs">
      <li role="presentation" id="tabBrowser_tab" class="active"><a href="#tabBrowser" data-toggle="tab">Browse All Fusions</a></li>
      <!-- <li role="presentation" id="igvTab"><a href="#igvBrowser" data-toggle="tab">IGV Detail</a></li> -->
    </ul>
    <!-- End tabs header -->

    <!-- Start tabs content -->
    <div class="tab-content" id="tabContent">
      <!-- Start Data Table Tab -->
         <div role="tabpanel" id="tabBrowser" class="tab-pane fade in active" data-toggle="tab">
        <!-- Start data table -->
          <div class="table-responsive">
            <table id="fusionTable" class="table table-striped table-bordered table-hover active" cell spacing="0" width="100%"></table>
          </div>
        <!-- End data table -->
      </div>
    </div>
    <!-- End tab content -->

   <%
       from galaxy import model
       users_current_history = trans.history
       url_dict = { }
       dataset_ids = [ trans.security.encode_id( d.id ) for d in users_current_history.datasets ]
       output_datasets = hda.creating_job.output_datasets
       viz_list1 = ['finspector_bed','FusionJuncSpan','cytoBand','finspector_fa','finsepector_idx']
       viz_list2 = ['junction_bed','junction_bam','spanning_bed','spanning_bam']
       viz_list = viz_list1 + viz_list2
       for o in output_datasets:
           if o.name == 'trinity_bed':
              viz_list.append('trinity_bed')
           if o.name in viz_list:      
              url_dict[ o.name ] = trans.security.encode_id( o.dataset_id )
   %>

    <!-- Scripts -->
    <script src="${h.url_for('/plugins/visualizations/fusion/static/FusionInspector.js')}"></script>
    <script>
    var url_dict = ${ h.dumps( url_dict ) };
    var hdaId   = '${trans.security.encode_id( hda.id )}';
    var hdaExt  = '${hda.ext}';
    var ajaxUrl = "${h.url_for( controller='/datasets', action='index')}/" + hdaId + "/display?to_ext=" + hdaExt;
    $.getJSON(ajaxUrl, function(data){
         console.log("JSON DATA");
         console.log(data);
         var data_modified = data;
         data_modified[ "referenceBed" ] = "/datasets/" + url_dict["finspector_bed"] + "/display?to_ext=bed";
         data_modified[ "junctionSpanning" ] = "/datasets/" + url_dict["FusionJuncSpan"] + "/display?to_ext=txt";
         data_modified[ "junctionReads" ] = "/datasets/" + url_dict["junction_bed"] + "/display?to_ext=bed";
         data_modified[ "junctionReadsBam" ] = "/datasets/" + url_dict["junction_bam"] + "/display?to_ext=bam";
         data_modified[ "junctionReadsBai" ] = "/dataset/get_metadata_file?hda_id=" + url_dict["junction_bam"] + "&metadata_name=bam_index";
         data_modified[ "spanningReadsBam" ] = "/datasets/" + url_dict["spanning_bam"] + "/display?to_ext=bam";
         data_modified[ "spanningReadsBai" ] = "/dataset/get_metadata_file?hda_id=" + url_dict["spanning_bam"] + "&metadata_name=bam_index";  
         data_modified[ "spanningReads" ] = "/datasets/" + url_dict["spanning_bed"] + "/display?to_ext=bed"; 
         data_modified[ "trinityBed" ] = "/datasets/" + url_dict["trinity_bed"] + "/display?to_ext=bed";        
         data_modified[ "cytoband" ] = "/datasets/" + url_dict["cytoBand"] + "/display?to_ext=txt";
         data_modified[ "reference" ] = "/datasets/" + url_dict["finspector_fa"] + "/display?to_ext=fasta";  
         data_modified[ "referenceIndex" ] = "/datasets/" + url_dict["finsepector_idx"] + "/display?to_ext=txt";
         console.log("******JSON DATA AFTER*****"); 
         console.log("spanningReadsBai");
         console.log(data_modified["spanningReadsBai"]);
         console.log("junctionReadsBai");
         console.log(data_modified["junctionReadsBai"]);
         $(document).ready(function( ) {
         // Load data (NOT MOCKED)
         fusionInspectorState.cache[ "json" ] = data_modified;
         // Set sample name in header
         // setSampleName( fusionInspectorState.cache.json );
         // Load the data table
         loadFusionDataTable();
         fusionInspectorState.cache.fusionTable = $('#fusionTable').DataTable({
             'order': [[ 0, 'asc' ]],
             'scrollX': true
         });
         $('#fusionTable tbody').on('click', 'tr', function() {
            curFusionRow = fusionInspectorState.cache.fusionTable.row( this ).data();
         // IGV browser has to be visible when the files are loaded.
         // If it is hidden the files load as 200 (full file) as opposed
         // to 206, whichis needed for indexed reading as igv web needs it.
          loadIGVBrowser(
              getFusionAnnotationFromRow( 'Fusion', curFusionRow ),
              getFusionAnnotationFromRow( 'Junction Reads', curFusionRow ),
              getFusionAnnotationFromRow( 'Spanning Fragments', curFusionRow ),
              getFusionAnnotationFromRow( 'Right Pos', curFusionRow ),
              getFusionAnnotationFromRow( 'Left Pos', curFusionRow )
           );//loadIGVBrowser
         });//#fusionTable
         // This hooks into the event fired off by tabs being selected.
         // It forces a redraw of the tab. Because the data table is originally
         // draw in a hidden (height = 0) div, the table is misdrawn. You have to
         // Trigger a redraw when the tab is visible so the height of the data table
         // can be correctly calculated.
         // Thanks to //stackoverflow.com/questions/20705905/bootstrap-3-jquery-event-for-active-tab-change
         $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
         $('#fusionTable').DataTable().columns.adjust().draw();
         })
      }); //Document.ready
    }) //getJSON
    </script>
</body>
</html> 
