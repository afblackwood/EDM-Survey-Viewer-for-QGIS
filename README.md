EDM Survey Viewer
-----------------

A QGIS plugin for use with EDMpy (https://github.com/surf3s/EDM) while surveying/excavating with a total station at archaeological sites. EDM Survey Viewer reads the .json database that is being written by EDMpy in real-time, as total station data are being saved. Built for QGIS v3.x-4.x.

To install, go to 'Manage and Install Plugins' in QGIS, and install either from the EDM_Survey_Viewer.zip file, or by copying the EDM Survey Viewer folder into the QGIS plugins folder. Once installed, the plugin opens a panel that contains the controls and options. Press 'Select DB' to find and select the .json database that EDMpy is using  (by default, this will be in the same folder as the .CFG file you are using), then press 'Start' to begin plotting the data. The update interval can be changed on the fly, and the projection can be changed to show plan view (xy), or profile (xz,yz). Use 'Zoom Full' (ctrl+shift+F) to re-centre the points after changing the view. The CRS by default is a local coordinate system and should accept spatial data saved in any format, but it can also be selected manually (for example if you are also loading georectified features such as polygons or rasters).

------------
Version 1.0

Oct 2026
The version before this was tested in the field and found to be stable, but many features have been added since - email me, or add an 'issue' here in github, if any bugs are found and I'll try to fix them asap.
