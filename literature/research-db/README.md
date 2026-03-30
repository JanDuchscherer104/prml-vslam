# Research DB

This directory stores the persistent source database for the report fragment
`docs/report/challenge-intro/challenge-from-Vslam-to-3DGS.typ`.

## Layout

- `schema.sql`: SQLite schema used as the canonical relational model
- `seed_data.json`: human-readable seed data for sources, concepts, equations, recommendations, and fragment links
- `build_db.py`: deterministic database builder
- `vslam_to_3dgs.sqlite`: generated SQLite database

## Why SQLite

The task is relational. A single paper can support many concepts, equations, and design
recommendations, and one report fragment can draw on many papers and grounding links. SQLite gives a
durable local database that can later be queried from scripts, notebooks, or future automation
without having to manually keep many Markdown notes in sync.

## Regeneration

Run:

```bash
python3 literature/research-db/build_db.py
```

This rebuilds `vslam_to_3dgs.sqlite` from `schema.sql` and `seed_data.json`.
