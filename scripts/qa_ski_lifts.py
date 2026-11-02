"""Offline regression: Overpass HTTP 502 retries and alternate mirror fallback."""
from __future__ import annotations

import json
import tempfile
import urllib.error
from pathlib import Path
from unittest.mock import patch

import ski_lifts


class Response:
    def __init__(self, payload: bytes):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, limit: int):
        assert limit > len(self.payload)
        return self.payload


def main() -> None:
    geo = {
        "elements": [{
            "type": "way",
            "id": 12345,
            "tags": {"aerialway": "gondola", "name": "Pierrafort"},
            "geometry": [
                {"lat": 45.458987, "lon": 6.44331},
                {"lat": 45.45050, "lon": 6.44320},
                {"lat": 45.442458, "lon": 6.44112},
            ],
        }],
    }
    payload = json.dumps(geo).encode("utf-8")
    calls = []
    def fake_open(request, timeout=None):
        calls.append(request.full_url)
        if len(calls) <= 2:
            raise urllib.error.HTTPError(request.full_url, 502,
                                         "Bad Gateway", None, None)
        return Response(payload)

    with tempfile.TemporaryDirectory() as directory:
        with (patch.object(ski_lifts, "CACHE", Path(directory)),
              patch.object(ski_lifts.urllib.request, "urlopen", side_effect=fake_open),
              patch.object(ski_lifts.time, "sleep", return_value=None)):
            route = ski_lifts.osm_route()
            assert len(route) == 3, route
            assert len(calls) == 3, calls
            assert calls[0] == calls[1], calls
            assert calls[2] != calls[0], calls
            assert (Path(directory) / "pierrafort_osm.json").is_file()
            # Cached verified route must work offline with no new network.
            route2 = ski_lifts.osm_route()
            assert route == route2 and len(calls) == 3
    print("PIERRAFORT OSM RETRY QA: OK (HTTP 502 mirror fallback and cache)")


if __name__ == "__main__":
    main()
