# -*- coding: utf-8 -*-
"""
VectorLayersExport2WebHTML - Main plugin logic for QGIS 4.0 (Qt6)
Exports selected vector layers to an interactive Leaflet HTML map.
"""

import os
import uuid
import json
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QPalette
from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QListWidget, QListWidgetItem, QPushButton, QFileDialog,
    QLabel, QProgressBar, QMessageBox, QApplication, QAbstractItemView,
    QLineEdit
)
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsJsonExporter, QgsCoordinateReferenceSystem,
    Qgis
)


class Export2Web:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.toolbar = None

    def initGui(self):
        # Create a dedicated toolbar for the plugin
        self.toolbar = self.iface.addToolBar("Vector Layers Export")
        self.toolbar.setObjectName("VectorLayersExport2WebHTML")

        # Create the action with emoji prefix
        self.action = QAction("🌐 Vector Layers to Web", self.iface.mainWindow())
        self.action.setToolTip("Export selected vector layers to interactive web map")
        self.action.triggered.connect(self.run)

        # Add the action to the dedicated toolbar
        self.toolbar.addAction(self.action)

    def unload(self):
        if self.toolbar and self.action:
            self.toolbar.removeAction(self.action)
        if self.toolbar:
            self.toolbar.deleteLater()
            self.toolbar = None

    def run(self):
        dlg = ExportDialog(self.iface)
        dlg.exec()


class ExportDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.setWindowTitle("Settings")
        self.setMinimumWidth(500)
        self.setModal(True)

        # ---- Detect Light / Dark Mode ----
        palette = self.palette()
        # Use QPalette.ColorRole.Window for PyQt6 compatibility
        bg_color = palette.color(QPalette.ColorRole.Window)
        is_dark = bg_color.lightness() < 128

        # ---- Apply theme‑aware modern stylesheet ----
        if is_dark:
            self.setStyleSheet("""
                QDialog {
                    background: #2b2b2b;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #555;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                    background: #3c3c3c;
                    color: #eee;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #eee;
                }
                QPushButton {
                    background: #4c7df5;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #5a8cf7;
                }
                QPushButton#browseBtn {
                    background: #6c757d;
                }
                QPushButton#browseBtn:hover {
                    background: #7a828a;
                }
                QListWidget {
                    border: 1px solid #555;
                    border-radius: 4px;
                    background: #3c3c3c;
                    color: #eee;
                }
                QListWidget::item:selected {
                    background: #4c7df5;
                }
                QLineEdit {
                    border: 1px solid #555;
                    border-radius: 4px;
                    padding: 4px;
                    background: #3c3c3c;
                    color: #eee;
                }
                QProgressBar {
                    border: 1px solid #555;
                    border-radius: 4px;
                    text-align: center;
                    background: #3c3c3c;
                    color: #eee;
                }
                QProgressBar::chunk {
                    background: #4c7df5;
                    border-radius: 4px;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background: #f5f5f5;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #ccc;
                    border-radius: 6px;
                    margin-top: 10px;
                    padding-top: 10px;
                    background: white;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                }
                QPushButton {
                    background: #4c7df5;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #3b6fe0;
                }
                QPushButton#browseBtn {
                    background: #6c757d;
                }
                QPushButton#browseBtn:hover {
                    background: #5a6268;
                }
                QListWidget {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    background: white;
                }
                QListWidget::item:selected {
                    background: #4c7df5;
                    color: white;
                }
                QLineEdit {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    padding: 4px;
                    background: white;
                }
                QProgressBar {
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    text-align: center;
                    background: white;
                }
                QProgressBar::chunk {
                    background: #4c7df5;
                    border-radius: 4px;
                }
            """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # ---- Layers section ----
        layer_group = QGroupBox("Select Vector Layers")
        layer_layout = QVBoxLayout(layer_group)
        self.layer_list = QListWidget()
        self.layer_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.layer_list.setToolTip("Hold Ctrl to select multiple layers")
        layer_layout.addWidget(self.layer_list)
        self.populate_layers()
        main_layout.addWidget(layer_group)

        # ---- Output file section ----
        file_group = QGroupBox("Output HTML File")
        file_layout = QVBoxLayout(file_group)

        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a location to save the HTML map...")
        self.file_path_edit.setReadOnly(True)
        file_row.addWidget(self.file_path_edit)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.clicked.connect(self.select_output_file)
        file_row.addWidget(self.browse_btn)

        file_layout.addLayout(file_row)
        main_layout.addWidget(file_group)

        # ---- Progress section ----
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        progress_layout.addWidget(self.progress)
        main_layout.addWidget(progress_group)

        # ---- Export button ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.export_btn = QPushButton("Export")
        self.export_btn.setFixedWidth(120)
        self.export_btn.clicked.connect(self.export)
        btn_layout.addWidget(self.export_btn)
        main_layout.addLayout(btn_layout)

        self.output_file = ""

    def populate_layers(self):
        self.layer_list.clear()
        for layer in QgsProject.instance().mapLayers().values():
            if isinstance(layer, QgsVectorLayer):
                item = QListWidgetItem(layer.name())
                item.setData(Qt.ItemDataRole.UserRole, layer.id())
                item.setSelected(True)
                self.layer_list.addItem(item)

    def select_output_file(self):
        default_dir = QgsProject.instance().homePath() or os.path.expanduser("~")
        default_name = f"{QgsProject.instance().baseName() or 'map'}_webmap.html"
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save HTML Map", os.path.join(default_dir, default_name),
            "HTML files (*.html)"
        )
        if file_path:
            self.output_file = file_path
            self.file_path_edit.setText(file_path)

    def export(self):
        selected_items = self.layer_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No layers", "Please select at least one vector layer.")
            return
        if not self.output_file:
            QMessageBox.warning(self, "Output file", "Please choose an output HTML file.")
            return

        layers = []
        for item in selected_items:
            layer_id = item.data(Qt.ItemDataRole.UserRole)
            layer = QgsProject.instance().mapLayer(layer_id)
            if layer and isinstance(layer, QgsVectorLayer):
                layers.append(layer)

        if not layers:
            QMessageBox.warning(self, "No valid layers", "None of the selected layers are valid vector layers.")
            return

        self.export_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        QApplication.processEvents()

        layers_data = []
        errors = []
        skipped_crs_layers = []   # Track layers skipped due to CRS
        total = len(layers)

        for i, layer in enumerate(layers):
            # Check CRS: only EPSG:4326 allowed
            if layer.crs().authid() != "EPSG:4326":
                skipped_crs_layers.append(layer.name())
                errors.append(
                    f"{layer.name()} – Layer CRS is {layer.crs().authid()}, "
                    "must be EPSG:4326. Please reproject first."
                )
                progress_value = int((i + 1) / total * 100)
                self.progress.setValue(progress_value)
                QApplication.processEvents()
                continue

            try:
                geojson_str = self.layer_to_geojson(layer)
                if geojson_str:
                    json.loads(geojson_str)
                    layers_data.append({
                        "name": layer.name(),
                        "geojson": geojson_str
                    })
                else:
                    errors.append(f"{layer.name()} – No features or geometry export failed.")
            except Exception as e:
                errors.append(f"{layer.name()} – {str(e)}")
            progress_value = int((i + 1) / total * 100)
            self.progress.setValue(progress_value)
            QApplication.processEvents()

        self.progress.setValue(100)
        self.progress.setVisible(False)
        self.export_btn.setEnabled(True)

        # If no valid layers at all, show error dialog with all errors
        if not layers_data:
            msg = "No valid GeoJSON data could be generated.\n\n"
            if errors:
                msg += "\n".join(errors)
            else:
                msg += "Unknown error."
            QMessageBox.critical(self, "Export failed", msg)
            return

        # Warn if some layers were skipped due to CRS
        if skipped_crs_layers:
            skip_msg = (
                "The following layers were skipped because they are not in EPSG:4326:\n\n"
                + "\n".join(skipped_crs_layers) +
                "\n\nPlease reproject them to EPSG:4326 and try again if you need them."
            )
            QMessageBox.warning(self, "Layers skipped", skip_msg)

        # Generate HTML with the valid layers
        try:
            self.generate_html(self.output_file, layers_data, errors)
            self.iface.messageBar().pushMessage(
                "VectorLayersExport2WebHTML",
                f"Map exported successfully to {self.output_file}",
                level=Qgis.Success,
                duration=5
            )
            QMessageBox.information(self, "Export Complete", f"Web map saved to:\n{self.output_file}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to write HTML file:\n{str(e)}")

    def layer_to_geojson(self, layer):
        exporter = QgsJsonExporter(layer)
        target_crs = QgsCoordinateReferenceSystem("EPSG:4326")
        exporter.setDestinationCrs(target_crs)
        exporter.setPrecision(6)

        features = list(layer.getFeatures())
        if not features:
            return None

        geojson_str = exporter.exportFeatures(features)
        return geojson_str if geojson_str else None

    def generate_html(self, output_path, layers_data, warnings):
        project_name = QgsProject.instance().baseName() or "Map"

        layers_js = []
        for idx, layer_info in enumerate(layers_data):
            safe_name = f"lyr_{idx}_{uuid.uuid4().hex[:6]}"
            geojson = layer_info["geojson"]
            layers_js.append({
                "var_name": safe_name,
                "display_name": layer_info["name"],
                "geojson": geojson
            })

        html_content = self.build_html_template(project_name, layers_js, warnings)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

    def build_html_template(self, project_name, layers_js, warnings):
        layers_code = "var overlayMaps = {};\nvar layerNames = {};\n"
        for layer in layers_js:
            var_name = layer["var_name"]
            display_name = layer["display_name"].replace("'", "\\'")
            geojson = layer["geojson"]
            layers_code += f"""
            try {{
                var geoData_{var_name} = {geojson};
                var {var_name} = L.geoJSON(geoData_{var_name}, {{
                    style: function() {{ return {{ weight: 2, fillOpacity: 0.2 }}; }},
                    onEachFeature: function(f, l) {{
                        if (l && l.getBounds) boundsGroup.addLayer(l);
                        if (f && f.properties) {{
                            var popupContent = '<b>Attributes</b><br/><div style="max-height:200px; overflow-y:auto;"><table style="font-size:12px; width:100%;">';
                            for (var key in f.properties) {{
                                if (Object.prototype.hasOwnProperty.call(f.properties, key)) {{
                                    var val = f.properties[key];
                                    if (val === null || val === undefined) val = '';
                                    popupContent += '<tr><td style="padding-right:10px;"><b>' + key + '</b></td><td>' + String(val) + '</td></tr>';
                                }}
                            }}
                            popupContent += '</table></div>';
                            try {{ l.bindPopup(popupContent); }} catch(e) {{ console.error('Popup error:', e); }}
                        }}
                    }}
                }});
                {var_name}.addTo(map);
                overlayMaps['{var_name}'] = {var_name};
                layerNames['{var_name}'] = '{display_name}';
                console.log('✅ Added layer: {display_name} (key: {var_name})');
            }} catch(e) {{
                console.error('❌ Failed to add layer {display_name}:', e);
            }}
            """
        basemap_js = """
        var osmLayer = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        });
        var esriWorldImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: '&copy; <a href="https://www.esri.com/en-us/home">Esri</a>',
            maxZoom: 18
        });
        var baseMaps = {
            'OpenStreetMap': osmLayer,
            'Esri World Imagery': esriWorldImagery
        };
        """

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name} – Vector Layers Export</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
        .leaflet-container {{ line-height: 1.3; }}
        #infobox {{
            position: absolute;
            left: 8px;
            bottom: 8px;
            z-index: 1000;
            background: rgba(255,255,255,0.92);
            padding: 10px;
            border-radius: 6px;
            box-shadow: 0 1px 6px rgba(0,0,0,0.25);
            font-size: 14px;
            max-width: 420px;
            pointer-events: none;
        }}
        .mf-circle-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: rgba(255,255,255,0.96);
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            color: #333;
            font-size: 20px;
            text-decoration: none;
            transition: all 0.2s ease;
            pointer-events: auto;
            z-index: 1001;
        }}
        .mf-circle-btn:hover {{
            background: #f8f8f8;
            box-shadow: 0 3px 8px rgba(0,0,0,0.3);
            transform: scale(1.05);
        }}
        .mf-circle-btn.active {{
            background: #e6f2ff;
            color: #0066cc;
        }}
        .mf-control-wrapper {{
            position: absolute;
            top: 10px;
            right: 10px;
            z-index: 1000;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            pointer-events: none;
        }}
        .mf-control-wrapper .mf-circle-btn {{
            pointer-events: auto;
        }}
        .mf-control-panel {{
            display: none;
            background: rgba(255,255,255,0.95);
            border-radius: 8px;
            box-shadow: 0 3px 10px rgba(0,0,0,0.2);
            padding: 12px;
            margin-bottom: 8px;
            max-height: 320px;
            overflow-y: auto;
            width: 220px;
            pointer-events: auto;
        }}
        .mf-control-panel.open {{ display: block; }}
        .mf-control-panel label {{
            display: block;
            margin: 5px 0;
            white-space: normal;
            word-wrap: break-word;
        }}
        #search-panel select, #search-panel button {{
            width: 100%;
            margin-bottom: 8px;
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
        }}
        #search-panel input.search-value-input {{
            width: 206px;
            margin: 0 auto 8px auto;
            display: block;
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
            font-size: 14px;
            text-align: center;
        }}
        #search-panel button {{
            background-color: #4c7df5;
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
        }}
        #search-panel button:hover {{ background-color: #3b6fe0; }}
        #search-results {{
            max-height: 200px;
            overflow-y: auto;
            margin-top: 10px;
            border-top: 1px solid #eee;
            padding-top: 10px;
        }}
        .search-result-item {{
            display: block;
            padding: 5px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            font-size: 13px;
        }}
        .search-result-item:hover {{ background-color: #f0f6ff; }}
        .no-layers-msg {{
            color: #666;
            font-style: italic;
            padding: 5px 0;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <div id="infobox">
        Made with QGIS QT6 VectorLayersExport2WebHTML Plugin
    </div>
    <div class="mf-control-wrapper">
        <div id="basemap-panel" class="mf-control-panel"></div>
        <button id="basemap-btn" class="mf-circle-btn" title="Basemaps"><i class="fas fa-globe"></i></button>
        <div id="components-panel" class="mf-control-panel"></div>
        <button id="components-btn" class="mf-circle-btn" title="Layers"><i class="fas fa-layer-group"></i></button>
        <div id="search-panel" class="mf-control-panel">
            <select id="search-layer-select"><option value="">Select Layer</option></select>
            <select id="search-field-select1"><option value="">Select Field 1</option></select>
            <input type="text" id="search-value-input1" class="search-value-input" placeholder="Search value">
            <select id="search-field-select2"><option value="">Select Field 2 (Optional)</option></select>
            <input type="text" id="search-value-input2" class="search-value-input" placeholder="Search value (Optional)">
            <button id="search-button">Search</button>
            <div id="search-results"></div>
        </div>
        <button id="search-btn" class="mf-circle-btn" title="Search"><i class="fas fa-search"></i></button>
    </div>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            {basemap_js}

            var map = L.map('map', {{ layers: [osmLayer] }}).setView([0, 0], 2);
            var boundsGroup = L.featureGroup().addTo(map);

            {layers_code}

            console.log('overlayMaps keys:', Object.keys(overlayMaps));
            console.log('layerNames:', layerNames);

            try {{
                // Basemap panel
                var basemapPanel = document.getElementById('basemap-panel');
                if (basemapPanel) {{
                    var title = document.createElement('div');
                    title.style.fontWeight = '600';
                    title.style.marginBottom = '6px';
                    title.innerText = 'Basemaps';
                    basemapPanel.appendChild(title);
                    var list = document.createElement('div');
                    basemapPanel.appendChild(list);
                    for (var name in baseMaps) {{
                        if (baseMaps.hasOwnProperty(name)) {{
                            (function(nm) {{
                                var row = document.createElement('label');
                                row.style.display = 'block';
                                var radio = document.createElement('input');
                                radio.type = 'radio';
                                radio.name = 'mf_basemap';
                                radio.value = nm;
                                radio.style.marginRight = '6px';
                                if (map.hasLayer(baseMaps[nm])) radio.checked = true;
                                radio.addEventListener('change', function() {{
                                    for (var k in baseMaps) {{
                                        if (baseMaps.hasOwnProperty(k)) {{
                                            try {{ map.removeLayer(baseMaps[k]); }} catch(e) {{}}
                                        }}
                                    }}
                                    map.addLayer(baseMaps[nm]);
                                }});
                                row.appendChild(radio);
                                row.appendChild(document.createTextNode(nm));
                                list.appendChild(row);
                            }})(name);
                        }}
                    }}
                }}

                // Layers panel
                var componentsPanel = document.getElementById('components-panel');
                if (componentsPanel) {{
                    var title2 = document.createElement('div');
                    title2.style.fontWeight = '600';
                    title2.style.marginBottom = '6px';
                    title2.innerText = 'Layers';
                    componentsPanel.appendChild(title2);
                    var list2 = document.createElement('div');
                    componentsPanel.appendChild(list2);
                    var layerKeys = Object.keys(overlayMaps);
                    if (layerKeys.length === 0) {{
                        var msg = document.createElement('div');
                        msg.className = 'no-layers-msg';
                        msg.innerText = 'No layers available to display.';
                        list2.appendChild(msg);
                    }} else {{
                        layerKeys.forEach(function(key) {{
                            var displayName = layerNames[key] || key;
                            (function(nm, key) {{
                                var row = document.createElement('label');
                                row.style.display = 'block';
                                var cb = document.createElement('input');
                                cb.type = 'checkbox';
                                cb.checked = map.hasLayer(overlayMaps[key]);
                                cb.style.marginRight = '6px';
                                cb.addEventListener('change', function() {{
                                    if (this.checked) map.addLayer(overlayMaps[key]);
                                    else map.removeLayer(overlayMaps[key]);
                                }});
                                row.appendChild(cb);
                                row.appendChild(document.createTextNode(nm));
                                list2.appendChild(row);
                            }})(displayName, key);
                        }});
                    }}
                }}

                // Buttons
                var basemapBtn = document.getElementById('basemap-btn');
                var componentsBtn = document.getElementById('components-btn');
                var searchBtn = document.getElementById('search-btn');
                var searchPanel = document.getElementById('search-panel');

                function closeAllExcept(keep) {{
                    var panels = ['basemap-panel', 'components-panel', 'search-panel'];
                    var btns = [basemapBtn, componentsBtn, searchBtn];
                    for (var i = 0; i < panels.length; i++) {{
                        var p = document.getElementById(panels[i]);
                        var b = btns[i];
                        if (p && keep !== panels[i]) p.classList.remove('open');
                        if (b && keep !== panels[i]) b.classList.remove('active');
                    }}
                }}
                if (basemapBtn) basemapBtn.addEventListener('click', function(e) {{
                    e.preventDefault();
                    var panel = document.getElementById('basemap-panel');
                    if (panel.classList.contains('open')) {{
                        panel.classList.remove('open');
                        basemapBtn.classList.remove('active');
                    }} else {{
                        closeAllExcept('basemap-panel');
                        panel.classList.add('open');
                        basemapBtn.classList.add('active');
                    }}
                }});
                if (componentsBtn) componentsBtn.addEventListener('click', function(e) {{
                    e.preventDefault();
                    var panel = document.getElementById('components-panel');
                    if (panel.classList.contains('open')) {{
                        panel.classList.remove('open');
                        componentsBtn.classList.remove('active');
                    }} else {{
                        closeAllExcept('components-panel');
                        panel.classList.add('open');
                        componentsBtn.classList.add('active');
                    }}
                }});
                if (searchBtn) searchBtn.addEventListener('click', function(e) {{
                    e.preventDefault();
                    if (searchPanel.classList.contains('open')) {{
                        searchPanel.classList.remove('open');
                        searchBtn.classList.remove('active');
                    }} else {{
                        closeAllExcept('search-panel');
                        searchPanel.classList.add('open');
                        searchBtn.classList.add('active');
                    }}
                }});

                // Search functionality
                var layerSelect = document.getElementById('search-layer-select');
                var fieldSelect1 = document.getElementById('search-field-select1');
                var fieldSelect2 = document.getElementById('search-field-select2');
                var searchButton = document.getElementById('search-button');
                var searchResults = document.getElementById('search-results');

                // Populate layer dropdown
                var layerKeys2 = Object.keys(overlayMaps);
                if (layerKeys2.length === 0) {{
                    var opt = document.createElement('option');
                    opt.value = '';
                    opt.textContent = 'No layers available';
                    layerSelect.appendChild(opt);
                }} else {{
                    layerKeys2.forEach(function(key) {{
                        var displayName = layerNames[key] || key;
                        var opt = document.createElement('option');
                        opt.value = key;
                        opt.textContent = displayName;
                        layerSelect.appendChild(opt);
                    }});
                }}

                layerSelect.addEventListener('change', function() {{
                    var layerKey = this.value;
                    fieldSelect1.innerHTML = '<option value="">Select Field 1</option>';
                    fieldSelect2.innerHTML = '<option value="">Select Field 2 (Optional)</option>';
                    if (layerKey && overlayMaps[layerKey]) {{
                        var fields = new Set();
                        overlayMaps[layerKey].eachLayer(function(l) {{
                            if (l.feature && l.feature.properties) {{
                                for (var p in l.feature.properties) fields.add(p);
                            }}
                        }});
                        fields.forEach(function(f) {{
                            var opt1 = document.createElement('option');
                            opt1.value = f; opt1.textContent = f;
                            fieldSelect1.appendChild(opt1);
                            var opt2 = document.createElement('option');
                            opt2.value = f; opt2.textContent = f;
                            fieldSelect2.appendChild(opt2);
                        }});
                    }}
                }});

                searchButton.addEventListener('click', function() {{
                    var layerKey = layerSelect.value;
                    var field1 = fieldSelect1.value;
                    var val1 = document.getElementById('search-value-input1').value.toLowerCase();
                    var field2 = fieldSelect2.value;
                    var val2 = document.getElementById('search-value-input2').value.toLowerCase();
                    searchResults.innerHTML = '';
                    if (!layerKey || !field1 || !val1) {{
                        searchResults.innerHTML = '<div class="search-result-item">Required: Layer, Field, and Search Value</div>';
                        return;
                    }}
                    var layer = overlayMaps[layerKey];
                    var results = [];
                    layer.eachLayer(function(l) {{
                        try {{
                            if (l.feature && l.feature.properties) {{
                                var match = true;
                                var prop1 = l.feature.properties[field1];
                                if (prop1 != null && String(prop1).toLowerCase().indexOf(val1) === -1) match = false;
                                if (match && field2 && val2) {{
                                    var prop2 = l.feature.properties[field2];
                                    if (prop2 == null || String(prop2).toLowerCase().indexOf(val2) === -1) match = false;
                                }}
                                if (match) results.push(l);
                            }}
                        }} catch(e) {{}}
                    }});
                    if (results.length === 0) {{
                        searchResults.innerHTML = '<div class="search-result-item">No records available for this query.</div>';
                    }} else {{
                        results.forEach(function(r, idx) {{
                            var div = document.createElement('div');
                            div.className = 'search-result-item';
                            div.textContent = 'Result ' + (idx+1) + ': ' + String(r.feature.properties[field1]);
                            div.addEventListener('click', function() {{
                                try {{
                                    if (r.getBounds) map.fitBounds(r.getBounds());
                                    else if (r.getLatLng) map.setView(r.getLatLng(), 14);
                                    r.openPopup();
                                }} catch(e) {{}}
                            }});
                            searchResults.appendChild(div);
                        }});
                    }}
                }});

                setTimeout(function() {{
                    try {{
                        var b = boundsGroup.getBounds();
                        if (b.isValid()) map.fitBounds(b.pad(0.05));
                    }} catch(e) {{}}
                }}, 400);
            }} catch(err) {{
                console.error('UI setup error:', err);
            }}
        }});
    </script>
</body>
</html>"""
        return html