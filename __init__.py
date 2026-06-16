# -*- coding: utf-8 -*-
"""
VectorLayersExport2WebHTML – Export QGIS vector layers to an interactive Leaflet HTML map.
"""

from .plugin import Export2Web


def classFactory(iface):
    """Required plugin entry point for QGIS."""
    return Export2Web(iface)