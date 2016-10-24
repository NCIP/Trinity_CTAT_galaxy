<!DOCTYPE html>

<html lang="en">
<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <meta name="description" content="Trinity CTAT visualization for SNVs in discovered RNA-Seq.">
  <meta name="author" content="Timothy Tickle">
  <title>${hda.name} | ${visualization_name}</title>

  <!-- CSS -->
  <!-- Bootstrap //maxcdn.bootstrapcdn.com/bootstrap/3.3.5/css/bootstrap.min.css">-->
  <link rel="stylesheet" type="text/css" href="/static/mutation/bootstrap.min.css">
  <!-- jQuery UI CSS -->
  <link rel="stylesheet" type="text/css" href="/static/mutation/jquery-ui.css"/>
  <!-- Font Awesome CSS -->
  <link rel="stylesheet" type="text/css" href="/static/mutation/font-awesome-4.4.0/css/font-awesome.min.css">
  <!-- IGV CSS -->
  <!-- <link rel="stylesheet" type="text/css" href="/static/mutation/igv.css"> -->
  <!-- Spinner from //www.css-spinners.com/spinner/spinner
  <link rel="stylesheet" href="/static/mutation/spinner.css">-->
  <!--<link rel="stylesheet" type="text/css" href="//www.broadinstitute.org/igv/projects/igv-web/css/igv.css">-->
  <link rel="stylesheet" href="${h.url_for('/plugins/visualizations/mutation_inspector/static/css/igv.css')}">
  <link rel="stylesheet" href="${h.url_for('/plugins/visualizations/mutation_inspector/static/css/spinner.css')}">

  <!-- Associated with the Data Table -->
  <link rel="stylesheet" type="text/css" href="/static/mutation/dataTables.bootstrap.min.css">
  <!-- Specific CSS to inspectors -->
  <link rel="stylesheet" type="text/css" href="${h.url_for('/plugins/visualizations/mutation_inspector/static/css/inspector.css')}">

  <!-- Scripts -->
  <!-- jQuery JS -->
  <script type="text/javascript" src="${h.url_for('//ajax.googleapis.com/ajax/libs/jquery/1.11.3/jquery.min.js')}"></script>
  <script type="text/javascript" src="${h.url_for('//ajax.googleapis.com/ajax/libs/jqueryui/1.11.3/jquery-ui.min.js')}"></script>
  <!-- Bootstrap -->
  <script type="text/javascript" src="${h.url_for('//maxcdn.bootstrapcdn.com/bootstrap/3.3.4/js/bootstrap.min.js')}"></script>
  <!-- IGV JS -->
  <script type="text/javascript" src="${h.url_for('https://igv.org/web/beta/igv-beta.js')}"></script> 
  <!-- <script type="text/javascript" src="${h.url_for('/plugins/visualizations/mutation_inspector/static/scripts/igv-all.js')}"></script> --> 
  <!-- Data Table -->
  <script type="text/javascript" src="${h.url_for('//cdn.datatables.net/1.10.8/js/jquery.dataTables.min.js')}"></script>
  <script type="text/javascript" src="${h.url_for('//cdn.datatables.net/1.10.8/js/dataTables.bootstrap.min.js')}"></script>

</head>
<body>
  <!-- Header (info) -->
  <div class="container-fluid" id="sampleHeader">
    <div class="row" style="background-color: #E7E7EF">
      <div class="col-xs-6 col-md-3" id="activeSample"><p><b>Sample: </b>None</p></div>
      <div class="col-xs-6 col-md-2"><p><b>Chr: </b><span id="currentChr">NA</span></p></div>
      <div class="col-xs-6 col-md-2"><p><b>Position: </b><span id="currentPosition">NA</span></p></div>
      <div class="col-xs-6 col-md-1"><p><b>Ref: </b><span id="currentRef">NA</span></p></td></div>
      <div class="col-xs-6 col-md-1"><p><b>Alt: </b><span id="currentAlt">NA</span></p></td></div>
      <div class="col-xs-6 col-md-1"><b>MuPIT: </b></div>
      <div class="col-xs-6 col-md-2" id="currentMupit">Not Available</div>
    </div>
  </div>
  <hr>
  <!-- End Header (info) -->

  <!-- IGV browser area -->
  <div id="igvBrowser">
  </div>
  <hr>
  <!-- End IGV browser area -->

  <!-- Start tabs -->
    <!-- Start tabs header -->
    <ul id="tabDescription" class="nav nav-tabs">
      <li id="tabBrowser_tab" class="active"><a href="#tabBrowser" data-toggle="tab">Browse All</a></li>
    </ul>
    <!-- End tabs header -->

    <!-- Start tabs content -->
    <div class="tab-content" id="tabContent">
      <!-- Start Browser -->
      <div role="tabpanel" id="tabBrowser" class="tab-pane fade in active">
        <div class="container-fluid" id="igvDiv" style="padding:5px; border:1px solid lightgray">
          <!-- Start data table -->
            <div id="hidden_tabs"><p><b>Show Hidden Tab <span class='glyphicon glyphicon-eye-close'></span> :</b>Unknown</p></div>
            <table id="mutationTable" class="table table-striped table-bordered table-hover" cell spacing="0" width="100%">
            </table>
          <!-- End data table -->
        </div>
      </div>
      <!-- End Browser -->
    </div>
    <!-- End tab content -->

  <%
      from galaxy import model
      users_current_history = trans.history
      url_dict = { }
      dataset_ids = [ trans.security.encode_id( d.id ) for d in users_current_history.datasets ]
      output_datasets = hda.creating_job.output_datasets
      for o in output_datasets:
          if o.name == "bed_path":
             url_dict[ o.name ] = trans.security.encode_id( o.dataset_id )
          elif o.name == "recalibrated_bam":
               url_dict[ o.name ] = trans.security.encode_id( o.dataset_id )
  %>

  <!-- Scripts -->
  <script src="${h.url_for('/plugins/visualizations/mutation_inspector/static/MutationInspectorWeb.js')}"></script>
  <script>
    var url_dict = ${ h.dumps( url_dict ) };
    var hdaId   = '${trans.security.encode_id( hda.id )}';
    var hdaExt  = '${hda.ext}';
    var ajaxUrl = "${h.url_for( controller='/datasets', action='index')}/" + hdaId + "/display?to_ext=" + hdaExt;
    $.getJSON(ajaxUrl, function(data){
        console.log("JSON DATA");
        console.log(data);
        var data_modified = data;
        data_modified[ "BAM" ] = "/datasets/" + url_dict["recalibrated_bam"] + "/display?to_ext=bam";
        data_modified[ "BAM_INDEX" ] = "/dataset/get_metadata_file?hda_id=" + url_dict["recalibrated_bam"] + "&metadata_name=bam_index"; 
        data_modified[ "BED" ] = "/datasets/" + url_dict["bed_path"] + "/display?to_ext=bed"; 
        console.log("JSON DATA AFTER MODIFICATION");
        console.log(data_modified); 
        // Add entries to the table
        // Load Mutation table
        $(document).ready(function() {
             // Load mutation table
             //var mutationInspector = data_modified
             //var mutationInspector = loadMutationTable( "mutations.json" );
             var mutationInspector = loadMutationTable( data_modified );
             mutationInspectorState.cache.mutationTable = $('#mutationTable').DataTable({
                 'order': [[ 0, 'asc' ]],
                 'scrollX': true,
                 'columnDefs': [{
                   'render': function( data, type, row ){
                     var rounded_value = Math.round( data * 1000 )/1000;
                     if( isNaN( rounded_value ) ){
                       return 'NA';
                     } else {
                       return Math.round( data * 1000 )/1000;
                     }
                   },
                   'targets': [5,6,7,9,21]
                 }]
             });
             // Add click events to the table rows
             $('#mutationTable tbody').on('click', 'tr', function() {
               curMutationRow = mutationInspectorState.cache.mutationTable.row( this ).data()
               goToSNP( curMutationRow[ mutationInspectorView.chrKey ], curMutationRow[ mutationInspectorView.posKey ] );
               updateSNPInfo( curMutationRow[ mutationInspectorView.chrKey ],
                              curMutationRow[ mutationInspectorView.posKey ],
                              curMutationRow[ mutationInspectorView.refKey ],
                              curMutationRow[ mutationInspectorView.altKey ] );
               addSpecificTab( curMutationRow[ mutationInspectorView.chrKey ],
                               curMutationRow[ mutationInspectorView.posKey ],
                               curMutationRow[ mutationInspectorView.refKey ],
                               curMutationRow[ mutationInspectorView.altKey ] );
              })

             // Update Sample name
             $('#activeSample').html( '<p><b>Sample: </b>'+ mutationInspector.json.SAMPLE+'</p>' );
             // Load browser
             var igvBrowser = createIGVBrowser( mutationInspector.json );

             // Add state change event for default tab
             registerDefaultTabClick( "tabBrowser_tab" );
             
             // Update the hidden columns message
             updateHiddenColumns();
             var initially_hide_elements = ["CRAVAT_PVALUE","KGPROD","MQ","NSF","NSM","NSN","PMC","SAO","TISSUE","TUMOR","VEST_PVALUE"];
             initially_hide_elements.map( hideVariantColumn );
       } )
   } )
  </script>
</body>
</html>
