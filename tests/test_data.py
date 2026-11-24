import sqlite3
from contextlib import closing

import pytest

from sentinel.data import seed_demo


def test_demo_seed_is_repeatable(tmp_path) -> None:
    path = tmp_path / "demo.sqlite3"

    assert seed_demo(path) == 2
    assert seed_demo(path) == 0

    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute(
            """
            SELECT event_type, order_id, amount_minor, currency, origin, fixture_version
            FROM synthetic_events ORDER BY occurred_at_utc
            """
        ).fetchall()

    assert rows == [
        ("order_paid", "demo-order-1", 10000, "BRL", "synthetic", "order-lifecycle-v1"),
        ("order_refunded", "demo-order-1", 10000, "BRL", "synthetic", "order-lifecycle-v1"),
    ]


def test_conflicting_seed_rolls_back(tmp_path) -> None:
    path = tmp_path / "demo.sqlite3"
    seed_demo(path)

    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute("DELETE FROM synthetic_events WHERE event_type = 'order_paid'")
        connection.execute("UPDATE synthetic_events SET amount_minor = 1")

    with pytest.raises(ValueError, match="demo-refund-1"):
        seed_demo(path)

    with closing(sqlite3.connect(path)) as connection:
        rows = connection.execute(
            "SELECT event_id, amount_minor FROM synthetic_events"
        ).fetchall()

    assert rows == [("demo-refund-1", 1)]
