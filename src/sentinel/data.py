import argparse
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS synthetic_events (
    event_id TEXT PRIMARY KEY NOT NULL,
    order_id TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('order_paid', 'order_refunded')),
    occurred_at_utc TEXT NOT NULL,
    amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
    currency TEXT NOT NULL CHECK (currency = 'BRL'),
    origin TEXT NOT NULL CHECK (origin = 'synthetic'),
    fixture_version TEXT NOT NULL
) STRICT
"""

FIXTURE_VERSION = "order-lifecycle-v1"
EVENTS = (
    ("demo-paid-1", "demo-order-1", "order_paid", "2026-01-01T12:00:00Z", 10000),
    ("demo-refund-1", "demo-order-1", "order_refunded", "2026-01-02T12:00:00Z", 10000),
)


def seed_demo(path: Path) -> int:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(SCHEMA)
        inserted = 0
        for event in EVENTS:
            record = (*event, "BRL", "synthetic", FIXTURE_VERSION)
            result = connection.execute(
                """
                INSERT INTO synthetic_events (
                    event_id, order_id, event_type, occurred_at_utc,
                    amount_minor, currency, origin, fixture_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                record,
            )
            if result.rowcount == 0:
                existing = connection.execute(
                    """
                    SELECT event_id, order_id, event_type, occurred_at_utc,
                           amount_minor, currency, origin, fixture_version
                    FROM synthetic_events WHERE event_id = ?
                    """,
                    (event[0],),
                ).fetchone()
                if existing != record:
                    raise ValueError(f"Conflicting synthetic event: {event[0]}")
            inserted += result.rowcount
        return inserted


def main() -> None:
    parser = argparse.ArgumentParser(description="Carrega eventos sintéticos locais.")
    parser.add_argument(
        "--database", type=Path, default=Path("sentinel-demo.sqlite3")
    )
    args = parser.parse_args()
    inserted = seed_demo(args.database)
    print(f"Eventos sintéticos inseridos: {inserted}")


if __name__ == "__main__":
    main()
