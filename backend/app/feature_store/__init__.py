"""Feature Store — centralised spatial/temporal/competition feature vectors.

Assembles per-location (or per-H3-cell) feature vectors from the domain
engines, ready for scoring and (later) ML. Features carry metadata (source,
version) via the registry so downstream consumers can reason about provenance —
matching the project's "confidence tracking" principle.
"""
