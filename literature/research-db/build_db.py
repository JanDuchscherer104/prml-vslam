"""Build the persistent SQLite research database for the VSLAM-to-3DGS report task."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema.sql"
SEED_PATH = ROOT / "seed_data.json"
DB_PATH = ROOT / "vslam_to_3dgs.sqlite"


def insert_many(
    cursor: sqlite3.Cursor,
    table: str,
    rows: list[dict[str, object]],
    keys: list[str],
) -> None:
    placeholders = ", ".join(["?"] * len(keys))
    columns = ", ".join(keys)
    values = [tuple(row.get(key) for key in keys) for row in rows]
    cursor.executemany(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", values)


def fetch_id_map(cursor: sqlite3.Cursor, table: str, key_column: str) -> dict[str, int]:
    rows = cursor.execute(f"SELECT id, {key_column} FROM {table}").fetchall()
    return {row[1]: row[0] for row in rows}


def main() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))

    if DB_PATH.exists():
        DB_PATH.unlink()

    connection = sqlite3.connect(DB_PATH)
    try:
        cursor = connection.cursor()
        cursor.executescript(schema)

        insert_many(
            cursor,
            "sources",
            seed["sources"],
            [
                "key",
                "title",
                "source_type",
                "authors",
                "year",
                "venue",
                "url",
                "local_path",
                "citation_key",
                "summary",
                "relevance_score",
                "status",
                "notes",
            ],
        )
        insert_many(
            cursor,
            "concepts",
            seed["concepts"],
            ["slug", "name", "category", "definition", "why_it_matters", "wikipedia_url", "notes"],
        )
        insert_many(
            cursor,
            "equations",
            seed["equations"],
            [
                "slug",
                "name",
                "latex",
                "symbol_legend",
                "conceptual_explanation",
                "report_use",
                "difficulty",
                "notes",
            ],
        )
        insert_many(
            cursor,
            "recommendations",
            seed["recommendations"],
            ["slug", "title", "recommendation", "rationale", "priority", "applies_to", "notes"],
        )
        insert_many(
            cursor,
            "report_fragments",
            seed["report_fragments"],
            ["slug", "target_path", "section_title", "intent", "status", "notes"],
        )

        source_ids = fetch_id_map(cursor, "sources", "key")
        concept_ids = fetch_id_map(cursor, "concepts", "slug")
        equation_ids = fetch_id_map(cursor, "equations", "slug")
        recommendation_ids = fetch_id_map(cursor, "recommendations", "slug")
        fragment_ids = fetch_id_map(cursor, "report_fragments", "slug")

        cursor.executemany(
            "INSERT INTO source_concepts (source_id, concept_id, evidence) VALUES (?, ?, ?)",
            [
                (
                    source_ids[row["source_key"]],
                    concept_ids[row["concept_slug"]],
                    row.get("evidence"),
                )
                for row in seed["links"]["source_concepts"]
            ],
        )
        cursor.executemany(
            "INSERT INTO source_equations (source_id, equation_id, location_hint, evidence) VALUES (?, ?, ?, ?)",
            [
                (
                    source_ids[row["source_key"]],
                    equation_ids[row["equation_slug"]],
                    row.get("location_hint"),
                    row.get("evidence"),
                )
                for row in seed["links"]["source_equations"]
            ],
        )
        cursor.executemany(
            "INSERT INTO source_recommendations (source_id, recommendation_id, evidence) VALUES (?, ?, ?)",
            [
                (
                    source_ids[row["source_key"]],
                    recommendation_ids[row["recommendation_slug"]],
                    row.get("evidence"),
                )
                for row in seed["links"]["source_recommendations"]
            ],
        )
        cursor.executemany(
            "INSERT INTO fragment_sources (fragment_id, source_id, role) VALUES (?, ?, ?)",
            [
                (
                    fragment_ids[row["fragment_slug"]],
                    source_ids[row["source_key"]],
                    row["role"],
                )
                for row in seed["links"]["fragment_sources"]
            ],
        )

        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
