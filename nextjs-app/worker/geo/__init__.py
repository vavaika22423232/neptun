"""
GeoResolver pipeline for NEPTUN.

Multi-stage location resolution:
  Text -> Entities -> Candidates -> Scoring -> Validation -> Best match

Modules:
  resolver   - Orchestrator
  gazetteer  - SQLite-backed settlement lookup (28k+ entries)
  scoring    - Weighted candidate scoring
  rules      - Polygon/bbox validation, heuristic penalties
  feedback   - Corrections storage and learning
"""
