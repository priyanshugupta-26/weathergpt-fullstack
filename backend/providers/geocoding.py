"""Offline GeoNames gazetteer; factual coordinates, not demo weather."""

import json
import unicodedata
from functools import lru_cache
from pathlib import Path


def normalized(text):
    return "".join(
        c
        for c in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(c)
    )


@lru_cache(maxsize=1)
def cities():
    file = Path(__file__).resolve().parent.parent / "resources/cities.json"
    if not file.exists():
        return []
    result = json.loads(file.read_text())
    for row in result:
        row["_names"] = {
            normalized(name)
            for name in [row["name"], row["ascii"], *row["aliases"].split(",")]
            if name
        }
    return result


def local_search(query):
    q = normalized(query.strip())
    matches = []
    for row in cities():
        if q in row["_names"]:
            matches.append((0, row))
        elif normalized(row["name"]).startswith(q) or normalized(
            row["ascii"]
        ).startswith(q):
            matches.append((1, row))
    matches.sort(key=lambda pair: (pair[0], -pair[1]["population"]))
    return [
        {k: row[k] for k in ["name", "latitude", "longitude", "country", "timezone"]}
        | {"source": "GeoNames offline gazetteer"}
        for _, row in matches[:8]
    ]
