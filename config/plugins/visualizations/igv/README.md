# Instructions on enabling inspector tools in Galaxy

1. Download an apache module - modxsendfile 

2. Edit httpd.conf 

```
LoadModule xsendfile_module modules/mod_xsendfile.so
```

Add this to your Virtualhost directive or add to your existing \<Location\> directive:

```
<Location "/">

  XSendFile on

  XSendFilePath /

</Location>
```

3. Set up galaxy.ini to allow apache to send the file:

```
apache_xsendfile = True
```

4. Include the /visualizations/igv directory from this github repo into your galaxy set up ( needs to be in the galaxy/config/plugins/visualizations/igv directory ).

5. Replace {YOUR_GALAXY_DIR}/lib/galaxy/datatypes/text.py with the text.py that comes with this repo 

