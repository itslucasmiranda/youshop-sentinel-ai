"""Exact attribution matches within each synthetic dataset."""
from collections import defaultdict
from functools import lru_cache

from . import twin


def build_index(fixtures):
    index = defaultdict(list)
    for events, journey in fixtures:
        if journey is None:
            continue
        first = events[0]
        row = (first["occurred_at_utc"][:10], first["order_id"])
        for field in ("creator", "offer", "link"):
            value = getattr(journey, field)
            if value:
                index[field, value].append(row)
    return {key: sorted(rows, reverse=True) for key, rows in index.items()}


@lru_cache(maxsize=1)
def twin_index():
    return build_index(twin.fixture(i)[:2] for i in range(twin.SIZE))


def matches(index, case, field):
    value = (case["attribution"] or {}).get(field)
    rows = index.get((field, value), ())
    return dict(value=value, orders=[dict(date=day, order=id_) for day, id_ in rows
                                     if id_ != case["order_id"]])
