"use strict;"

///////////////////////
// Data
//////////////////////

/**
 * A small cach of SNP related info
 */
var mutationInspectorState = {
  cache : {},
  abridged : false,
  galaxy_mode : true,
  load_json_in_js : false
};


///////////////////////
// Mutation Table Associated
//
///////////////////////

/**
 * Read in the JSON object that points to the bams and variants of interest.
 * @param {string} mutation_json_data - The path / URL to the JSON object ( mutationInspectorState.load_json_in_js === true ) or object read in from json ( mutationInspectorState.load_json_in_js === false ) depending on mutationInspectorState.load_json_in_js
 */
function loadMutationTable( mutation_json_data ) {

  // Holds all information about the mutation view
  mutationInspectorView = {};

  // Hold the array of hidden columns in the data table
  mutationInspectorState.cache.hiddenCols = [];

  // Read in the JSON file
  if( mutationInspectorState.load_json_in_js === true ){
    readMutationJSON( mutation_json_data );
  } else {
    mutationInspectorView.json = mutation_json_data;
  }

  // Forced order of the mutation table elements.
  // Any element in the table and not in this array
  // will be after these elements in the table and will
  // be in no specific order
  forceHeaderKeyOrder = ['CHROM', 'POS', 'GENE', 'REF', 'ALT', 'QUAL', 'CHASM_PVALUE', 'VEST_PVALUE', 'CHASM_FDR', 'VEST_FDR']

  // Create table from json file
  // Get an array of the keys
  mutationHeaderKeys = []
  for( mutationHeader in mutationInspectorView.json.SNV[0] ) {
    if( mutationInspectorView.json.SNV[0].hasOwnProperty( mutationHeader ) ) {
      mutationHeaderKeys.push( mutationHeader );
    }
  }
  mutationInspectorState.cache.mutationHeaderKeys = orderTableKeysBeginning( mutationHeaderKeys, forceHeaderKeyOrder);

  // Store locations of certain key row elements used later
  // These elements can be considered REQUIRED in the data
  mutationInspectorView.headerKeys = mutationInspectorState.cache.mutationHeaderKeys
  mutationInspectorView.chrKey = mutationInspectorState.cache.mutationHeaderKeys.indexOf( "CHROM" );
  mutationInspectorView.posKey = mutationInspectorState.cache.mutationHeaderKeys.indexOf( "POS" );
  mutationInspectorView.refKey = mutationInspectorState.cache.mutationHeaderKeys.indexOf( "REF" );
  mutationInspectorView.altKey = mutationInspectorState.cache.mutationHeaderKeys.indexOf( "ALT" );

  // Add header and footer elements to the table
  var mutationTable = $('#mutationTable');
  var mutationHeader = mutationInspectorState.cache.mutationHeaderKeys.map( toTableRowHeaderElement );
  mutationTable.append( '<thead><tr>' + mutationHeader.join('') + '</tr></thead>' );
  mutationTable.append( '<tfoot><tr>' + mutationHeader.join('') + '</tr></tfoot>' );

  // Add table body
  mutationTable.append( '<tbody>' );
  for( snvIndex = 0; snvIndex < mutationInspectorView.json.SNV.length; snvIndex++ ){
      snvEntry = mutationInspectorView.json.SNV[ snvIndex ];
      mutationEntryValues = mutationInspectorState.cache.mutationHeaderKeys.map( function( key ){
        return snvEntry[ key ]; } )
      mutationTable.append( '<tr>' + mutationEntryValues.map( toTableRowBodyElement ) + '</tr>' );
  }
  mutationTable.append( '</tbody>' );
  // Add click event for column hiding
  $(".hide-glyph").on("click", function(e){
    e.preventDefault();
    hideVariantColumn( $(this).attr("data-column") );
  })

  // Return the inspector
  return mutationInspectorView;
}

/**
 * Order the mutation table keys so certain element are in front in a specific order
 * @param {array} ArrayToOrder - Array of elements to reorder.
 * @param {array} forcedOrder - Array of elements that should be at the beginning and in this order.
 */
function orderTableKeysBeginning( arrayToOrder, forcedOrder ){
  newArray = [];
  for( arrayElement = 0; arrayElement < arrayToOrder.length; arrayElement++ ){
    if( !( forcedOrder.indexOf( arrayToOrder[ arrayElement ] ) >= 0 )){
      newArray.push( arrayToOrder[ arrayElement ] );
    }
  }
  return( forcedOrder.concat( newArray ));
}


/**
 * Make a table header row containing a given value.
 * Helper function for the map call.
 * @param {string} tableRowValue - Value to put in the header row.
 */
function toTableRowHeaderElement( tableRowValue ){
    return '<th><span>' + tableRowValue + '<\span><span class="glyphicon glyphicon-eye-open hide-glyph" data-column="'+tableRowValue+'"></span></th>';
}

/**
 * Make a table row containing a given value.
 * Helper function for the map call.
 * @param {string} tableRowValue - Value to put in the row.
 */
function toTableRowBodyElement( tableRowValue ){
    return '<td>' + tableRowValue + '</td>';
}

/**
 * Show a hidden column of the data table.
 * @param {string} columnLabel - Data-column attribute of column to show.
 */
function showVariantColumn( columnLabel ){
  if( mutationInspectorState.cache.hiddenCols.indexOf( columnLabel ) >= 0 && 
      mutationInspectorState.cache.mutationHeaderKeys.indexOf( columnLabel >= 0 )){
    // Remove from array of hidden columns
    mutationInspectorState.cache.hiddenCols.splice( mutationInspectorState.cache.hiddenCols.indexOf( columnLabel ) , 1 );
    // Make visible by index ( 0 based )
    mutationInspectorState.cache.mutationTable.column( mutationInspectorState.cache.mutationHeaderKeys.indexOf( columnLabel ) ).visible( true );
    // Update UI text
    updateHiddenColumns();
  }
}

/**
 * Hide a visible column of the data table.
 * @param {string} columnLabel - data-column attribute of column to hide.
 */
function hideVariantColumn( columnLabel ){
  if( mutationInspectorState.cache.hiddenCols.indexOf( columnLabel ) < 0 &&
      mutationInspectorState.cache.mutationHeaderKeys.indexOf( columnLabel >= 0 )){
    // Add the column to the array of hidden columns
    mutationInspectorState.cache.hiddenCols.push( columnLabel );
    // Make invisible by index ( 0 based )
    mutationInspectorState.cache.mutationTable.column( mutationInspectorState.cache.mutationHeaderKeys.indexOf( columnLabel ) ).visible( false );
    // Update UI text
    updateHiddenColumns();
  }
}

/**
 * Manage the UI text indicating which columns are hidden given the current state.
 */
function updateHiddenColumns(){
  buildHiddenTabLinks = [];
  if( mutationInspectorState.cache.hiddenCols.length === 0 ){
    buildHiddenTabLinks.push( "None Hidden" );
  } else {
    for( hiddenCol = 0; hiddenCol < mutationInspectorState.cache.hiddenCols.length; hiddenCol++ ){
      buildHiddenTabLinks.push( '<a class="hide-col" data-column="'+mutationInspectorState.cache.hiddenCols[ hiddenCol ]+'">'+mutationInspectorState.cache.hiddenCols[ hiddenCol ]+'</a>' );
    }
  }
  $("#hidden_tabs").html( '<p><b>Show Hidden Tab <span class="glyphicon glyphicon-eye-close"></span> :</b>'+ buildHiddenTabLinks.join("-") + '</p>' );
  // Add click event
  $( "a.hide-col" ).on( 'click', function(e) {
    e.preventDefault();
    showVariantColumn( $(this).attr('data-column') );
  })
}

//////////////////////
// Associated with the specific view tab.
//
//////////////////////

/**
 * Add a tab for a specific genomic location / SNP.
 * Update the full UI to be consistent with selection.
 * Populate the body of the table with specific information.
 * @param {string} curRowChr - Chromsome location
 * @param {string} curRowPos - Genomic position on chromosome
 * @param {string} curRowRef - Reference base
 * @param {string} curRowAlt - Alternative base
 */
function addSpecificTab( curRowChr, curRowPos, curRowRef, curRowAlt ){
  // Turn off the additional tab creation
  if ( mutationInspectorState.abridged === true ){
    return( false );
  }

  var newTabName = curRowChr+"_"+curRowPos
  var tabArea = $( '#tabContent' );
  // If the the tab already exists, go to tab, do not make a new one.
  if( isExistingSpecificTab( curRowChr, curRowPos )){
    clickSpecificViewTab( newTabName )
    retrieveCRAVATInfo( curRowChr, curRowPos, curRowRef, curRowAlt )
    return;
  }
  // Make a new tab.
  var tabDescArea = $( '#tabDescription' );
  var chromLocation = curRowChr + ":" + curRowPos
  var closeButton = newTabName + "_close"
  var tabHeader = newTabName+"_tab"
  tabDescArea.append( '<li id="'+tabHeader+'"><a href="#'+newTabName+'" data-toggle="tab"><button id="'+closeButton+'" class="close closeTab" type="button">x</button>'+chromLocation+'</a></li>' );
  // Add in the tab area ( by default add in area for browser and cravat info )
  tabArea.append( '<div id="'+newTabName+'" class="tab-pane fade"></div>' );
  clickSpecificViewTab( newTabName );
  // Update cache of SNP info per genomic location.
  mutationInspectorState.cache[ chromLocation ] = { 
    'Chromosome' : curRowChr,
    'Position' : curRowPos,
    'alt' : curRowRef,
    'ref' : curRowAlt,
  }
  // MuPIT link will be added by an asynchronous call
  mutationInspectorState.cache[ chromLocation ][ "MuPIT Link" ] = null
  var currentCravatData = retrieveCRAVATInfo( curRowChr, curRowPos, curRowRef, curRowAlt );
  // Add click event for close button and tab.
  registerCloseEvent( closeButton, tabHeader, newTabName );
  registerOnClickEvent( tabHeader, chromLocation );
}

/**
 * Indicates if the tab already exists.
 * @param {string} curCheckChr - Chromsome to check.
 * @param {string} curCheckPos - Postion on chromosome to check.
 */
function isExistingSpecificTab( curCheckChr, curCheckPos ){
  var newTabName = curCheckChr+"_"+curCheckPos
  var mutationTabs = $( '.tab-pane' );
  for( var tabIndex = 0; tabIndex < mutationTabs.length; tabIndex++ ){
    if( mutationTabs[ tabIndex ].id === newTabName ){
      return true;
    }
  }
  return false; 
}

/**
 * Clicks on a specific tab to make it active.
 * @param {string} curSpecificViewTabId - The id of the tab to click and make active.
 */
function clickSpecificViewTab( curSpecificViewTabId ){
  $('.nav-tabs a[href="#' + curSpecificViewTabId + '"]').tab('show');
}

/**
 * Create custom close button event.
 * Closes associated tab and changes the active tab to the browsing tab.
 * @param {string} closeButtonId - Id of close button to which to add the event.
 * @param {string} closeTabId - Id of tab header to remove.
 * @param {string} closeBodyId - Id of tab content to remove.
 */
function registerCloseEvent( closeButtonId, closeTabId, closeBodyId ){
  // Add close button solution from
  // Hardcoded and not dynamic but works for now.
  $( "#"+closeButtonId ).click( function() {
    $( '#' + closeTabId ).remove();
    $( '#' + closeBodyId ).remove();
    $( '#tabDescription a[href="#tabBrowser"]' ).tab('show'); // Show the default tab body
    $( "#tabBrowser_tab" ).click();
  });
}

/**
 * Create a custom click event for the tabs.
 * Updates the page to be consistent with the active tab.
 * @param {string} tabHeader - The id of the tab to which to add the click event.
 * @param {string} registerChrLoc - The genomic location of the SNP being viewed (format= Chr:Pos).
 */
function registerOnClickEvent( tabHeader, registerChrLoc ){
  $( "#" + tabHeader ).click( function() {
    var currentState = mutationInspectorState.cache[ registerChrLoc ];
    goToSNP( currentState.Chromosome, currentState.Position );
    updateSNPInfo( currentState.Chromosome, currentState.Position, currentState.ref, currentState.alt );
    updateMupitLink( currentState );
  });
}

/**
 * Create a custom click event for the default tab.
 * This tab does not represent a specific location so some
 * of the page is cleared of info. The browser is not removed but stays
 * in it's last state.
 * @param {string} tabHeader - The id of the tab to which to add the click event.
 */
function registerDefaultTabClick( tabHeader ){

  // This is a hack added in after the fact. We needed to remove elements associated
  // with webservices until they were resolved. This does not belong here but is a
  // place that is called once. (Could not change the html as well).
  if( mutationInspectorState.abridged === true ){
    $("#sampleHeader").children().children()[5].remove();
    $("#currentMupit").remove();
  }
  $( "#"+tabHeader ).click( function() {
    updateSNPInfo( "NA", "NA", "NA", "NA" );
    updateMupitLink( { 'MuPIT Link' : null,
                       'Chromosome' : null 
    });
  });
}

/**
 * Update the top of the page with a summary of the location being viewed.
 * Also set the MuPIT link to a spinner as it will be loading.
 * @param {string} curSNPChr - Current view's chromosome.
 * @param {string} curSNPChr - Current view's position.
 * @param {string} curSNPChr - Current view's reference base.
 * @param {string} curSNPChr - Current view's alternative base.
 */
function updateSNPInfo( curSNPChr, curSNPPos, curSNPRef, curSNPAlt ){
  $( '#currentChr' ).text( curSNPChr );
  $( '#currentPosition' ).text( curSNPPos );
  $( '#currentRef' ).text( curSNPRef );
  $( '#currentAlt' ).text( curSNPAlt );
  if( mutationInspectorState.abridged === false ){
    $( '#currentMupit' ).text( '' );
    $( '#currentMupit' ).append( '<div class=\"spinner-loader\">Loading...</div>' );
  }
}


///////////////////////
// IGV browser Associated
//
//////////////////////

/**
 * Initializes a IGV browser instance.
 * @param {string} sampleInfo - Object holding the bam url/path, bam index url/path, and sample name.
 */
function createIGVBrowser( sampleInfo ){
  // Create a browser
  var div = $("#igvBrowser")[0],
  options = {
    showNavigation: true,
    genome: "hg19",
    tracks: [{ type: 'alignment',
               sourceType: 'file',
               url: sampleInfo.BAM,
               indexURL: sampleInfo.BAM_INDEX,
               name: sampleInfo.SAMPLE,
               maxHeight: 250 },
             { type: 'annotation',
               format: 'bed',
               sourceType: 'file',
               url: sampleInfo.BED,
               indexURL: sampleInfo.BED_INDEX,
               name: "Genes",
               order: Number.MAX_VALUE,
               displayMode: "EXPANDED",
               maxHeight: 75 }]
  };

  if( mutationInspectorState.galaxy_mode === true ){
    options = {
      showNavigation: true,
      genome: "hg19",
      tracks: [{ type: 'alignment',
               sourceType: 'file',
               url: sampleInfo.BAM,
               indexURL: sampleInfo.BAM_INDEX,
               name: sampleInfo.SAMPLE,
               maxHeight: 250 },
             { type: 'annotation',
               format: 'bed',
               sourceType: 'file',
               url: sampleInfo.BED,
               name: "Genes",
               indexed: false,
               order: Number.MAX_VALUE,
               displayMode: "EXPANDED",
               maxHeight: 75 }]
    };
  }
  igv.createBrowser( div, options );
}

/**
 * Go to SNP location.
 * @param {string} dataTableRowChr - Chromosomal location to which to move.
 * @param {string} dataTableRowPos - Position of interest
 */
function goToSNP( dataTableRowChr, dataTableRowPos ){
  // Move the igv browser to a specific location
  // Example "chr1:181,413,875-181,413,925"
  // The position needs to be a span so we are adding a window around the given position.
  igv.browser.search( dataTableRowChr + ":" + Math.max( 0, parseInt( dataTableRowPos ) - 50 ) + "-" + ( parseInt( dataTableRowPos ) + 50 ) );
}


//////////////////////
// Data IO
//
//////////////////////

/**
 * Reads in the mutation JSON file.
 * @param {string} readInFile - Path or URL to file.
 */
function readMutationJSON( readInFile ){
  $.getJSON( readInFile , function( jsonInfo ){
    mutationInspectorView.json = jsonInfo
  })
  .done( function(){ console.log( 'Completed reading file:' + readInFile ); } )
  .fail( function(){ console.log( 'Failed to read file:' + readInFile ); } )
}


//////////////////////
// CRAVAT Associated
//
/////////////////////

/**
 * Sets the area to contain the detailed (CRAVAT) info to a spinner
 * given we will wait for the associated asynchronous call.
 * @param {string} retrieveAnnotationTabName - The id of the tab content div to set to a spinner as we wait.
 */
function setAnnotationTabToLoad( retrieveAnnotationTabName ){
  $( '#' + retrieveAnnotationTabName ).html( "" );
  if( mutationInspectorState.abridged === false ){
    $( '#' + retrieveAnnotationTabName ).append( "<div class=\"spinner-loader\">Loading...</div>" );
  }
}

/**
 * Query the CRAVAT web service for information about the genomic location of interest.
 * Update the page when the data is received.
 * Asyncronous call.
 * @param {string} retrieveChr - Chromosome of interest, used in the cravat call.
 * @param {string} retrievePos - Position of interest, used in the cravat call.
 */
function retrieveCRAVATInfo( retrieveChr, retrievePos, retrieveRef, retrieveAlt ){
  // Performs an asynchronous call to the CRAVAT web service
  // Updates both the CRAVAT info header and the info tab
  // Puts a loading logo up while waiting
  var positionKey = retrieveChr + "_" + retrievePos
  var cravat_prefix = "//www.cravat.us/CRAVAT/rest/service/query?mutation="
  setAnnotationTabToLoad( positionKey );
  $.ajax({ type: 'GET',
           dataType: 'json',
           success: function( cravatData ){
    if( cravatData ){
      updateMupitLink( cravatData );
      updateCravatTab( retrieveChr + "_" + retrievePos, cravatData );
      mutationInspectorState.cache[ retrieveChr+':'+retrievePos ]["MuPIT Link"] = cravatData[ "MuPIT Link" ];
      }
    },
           url: cravat_prefix+retrieveChr+"_"+retrievePos+"_+_"+retrieveRef+"_"+retrieveAlt
  });
  return null;
}

/**
 * Write all information in a CRAVAT object received from the CRAVAT web service to a content tab /table.
 * @param {string} updateTab - Tab to add content to from CRAVAT.
 * @param {object} cravatItem - Obect of annotation, all members and value of the object are written to the table.
 */
function updateCravatTab( updateTab, cravatItem ){
  // Make CRAVAT annotation table for data
  var newTable = "<div class=\"table-responsive\"><table class=\"table-hover\">"
  for( var cravatElement in cravatItem ){
    if( cravatItem.hasOwnProperty( cravatElement ) ){
      var curValue = cravatItem[ cravatElement ]
      newTable = newTable + "<tr><td><b>" + cravatElement + ":</b> " + ( curValue ? curValue : "Not Specified" ) + "</td></tr>";
    }
  }
  newTable = newTable + "</table></div>"
  $( '#'+updateTab ).html( "" );
  $( '#'+updateTab ).append( newTable );
}


/////////////////////
// MuPIT Link / Button
//
/////////////////////

/**
 * Update the MuPIT link, handling cases where there was a link, there was no link, or a bad call occured.
 * @param {object} cravatItem - Object from the CRAVAT web service.
 */
function updateMupitLink( cravatItem ){

  if( mutationInspectorState.abridged === true ){
    return( false );
  }

  var mupit = cravatItem[ "MuPIT Link" ];
  // If there is a MuPIT link add as a button (update the label to a label)
  if( mupit ){
    $( '#currentMupit' ).html( "" );
    $( '#currentMupit' ).append( '<button id=\"mupitButton\" class=\"btn btn-info\"> View in MuPIT</button>');
    $( '#mupitButton' ).click( function() {
      window.open( mupit );
    });
  } else if( cravatItem[ 'Chromosome' ] ){
    $( '#currentMupit' ).html( "" );
    $( '#currentMupit' ).html( 'No Link for '+cravatItem[ 'Chromosome' ]+':'+cravatItem[ 'Position' ] );
  } else {
    $( '#currentMupit' ).html( "" );
    $( '#currentMupit' ).html( 'Please select a variant' );
  }
}
