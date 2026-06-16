# VectorLayersExport2WebHTML Plugin for QGIS 4.0

Exports selected vector layers to an interactive Leaflet HTML map with basemap selector, layer control, and attribute search.

## How to install

1. Download the source code as a ZIP archive.
2. Uncompress the ZIP file.
3. Move the extracted `VectorLayersExport2WebHTML` parent folder to the QGIS 4 plugins directory (create folders if they don't exist):  
   `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins`

> **Note:** Ensure you have at least one vector layer loaded in a QGIS 4.0 project before proceeding.

## How to use

1. Load one or more vector layers in QGIS 4.0.
2. Enable **VectorLayersExport2WebHTML** from the **Plugin Manager** (a new toolbar icon 🌐 appears).
3. Click the 🌐 toolbar button to open the export dialog.
4. In the dialog, select the layers you want to export (hold Ctrl to select multiple).
5. Choose an output folder and filename for the HTML map.
6. Click **Export** – the generated web map will open in your default browser.

**Note:** Only layers in **EPSG:4326** (WGS84) are exported. Layers with a different CRS are automatically skipped, and a warning lists them. Reproject your layers to EPSG:4326 if you need them included.
