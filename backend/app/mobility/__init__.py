"""Mobility Engine — pedestrian/vehicle flow analytics.

Lightweight, dependency-free implementations of the core trajectory pipeline:
GPS cleaning, staypoint detection with dwell time, origin-destination matrices,
and directional flow analysis. Designed to run without MobilityDB/Trackintel so
the logic is unit-testable; those can back the storage layer later.

A trajectory point is a dict: {lat, lon, t} where t is a UNIX timestamp
(seconds) or ISO string.
"""
