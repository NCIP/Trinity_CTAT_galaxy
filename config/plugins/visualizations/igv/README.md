1.Load an apache module - modxsendfile

2.Set up apache, 

LoadModule xsendfile_module modules/mod_xsendfile.so

Add this to your Virtualhost directive or add to your existing <Location> directive:

::<Location "/">
  XSendFile on
  XSendFilePath /
</Location>::


3.Set up galaxy.ini to allow apache to send the file:

apache_xsendfile = True

4.Include the /visualizations/igv directory in your galaxy set up

5.Replace lib/galaxy/datatypes/text.py with text.py that comes with this repo 

