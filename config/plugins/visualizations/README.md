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

4. Replace {YOUR_GALAXY_DIR}/lib/galaxy/datatypes/text.py with the text.py that comes with this repo 

5. Replace {YOUR_GALAXY_DIR}/lib/galaxy/datatypes/dataproviders/dataset.py with the dataset.py that comes with this repo

