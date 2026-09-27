EDM Survey Viewer

A QGIS plugin for use with EDMpy (https://github.com/surf3s/EDM) while surveying/excavating with a total station at archaeological sites.

EDM Survey Viewer reads .json databases from EDMpy as total station data is being saved. Built for QGIS v3.x-4.x.

Install using 'Manage and Install Plugins' in QGIS, and the EDM_Survey_Viewer.zip file. Once installed, press 'Select DB' to find and select the .json database that EDMpy is using  (by default, this will be in the same folder as the .CFG file you are using), then press 'Start' to begin plotting the data. The update interval can be changed on the fly, and the projection can be changed to show plan view (xy), or profile (xz,yz). Use 'Zoom Full' (ctrl+shift+F) to re-centre the points after changing the view. The CRS by default is a local coordinate system and should accept spatial data saved in any coordinate system (it will work fine without one), but it can also be selected manually (for example if you are also loading georectified features such as polygons or rasters).

Version 1.0
-------------
Oct 2026
The version before this was tested in the field and found to be stable, but many features have been added since - email me if any bugs are found and I'll try to fix them asap.
