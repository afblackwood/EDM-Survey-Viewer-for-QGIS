EDM Survey Viewer 
A QGIS plugin for use with EDMpy (https://github.com/surf3s/EDM)

EDM Survey Viewer reads .json databases from EDMpy as total station data is being saved. Built for QGIS v3.x-4.x.

Once installed, first browse to and select the folder that has the .json database that EDMpy is writing to (by default, 
this will be in the same folder as the .CFG file you are using) by pressing 'Browse', then press 'Start' to begin live updates. 
The CRS defaults to a local coordinate system, and one doesn't need to be defined (it will work fine without one), but it can also be 
selected manually (for example if you are also loading georectified features such as polygons or rasters etc).
