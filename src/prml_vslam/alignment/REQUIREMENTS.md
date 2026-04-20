# Alignment Requirements

## Purpose

This document is the concise source of truth for `prml_vslam.alignment`.

## Responsibilities

- own derived alignment contracts and implementation services
- detect dominant ground planes from normalized SLAM artifacts
- derive explicit viewer-scoped transforms such as `T_viewer_world_world`
- emit typed alignment metadata and visualization-ready plane geometry
- stay separate from backend execution, benchmark metric computation, and
  Rerun logging

## Non-Negotiable Requirements

- Native SLAM artifacts remain untouched; alignment outputs are always derived
  artifacts.
- Alignment metadata must carry explicit frame semantics.
- V1 owns metadata and visualization-ready plane geometry only; it does not own
  aligned trajectory/cloud artifacts or aligned `.rrd` export.
- Ground-plane detection must be best-effort: low-confidence or unsupported
  cases return explicit diagnostics rather than failing silently.

## Validation

- The package can consume normalized `SlamArtifacts` without backend-specific
  special cases beyond documented capability checks.
- Derived transforms map native `world` into explicit `viewer_world`.
- The package can express a finite plane patch suitable for later Rerun
  visualization without recomputing the plane fit.
