"""Competition Intelligence Engine.

Pure-Python (geometry-light) analytics on top of catchment zones and Huff
probabilities: service-area overlap, cannibalization / revenue transfer,
white-space (under-served) detection, and a competition graph.

All modules avoid hard dependencies on heavy GIS libs so they can be unit
tested without PostGIS. Geometry inputs are GeoJSON dicts or lat/lon points.
"""
