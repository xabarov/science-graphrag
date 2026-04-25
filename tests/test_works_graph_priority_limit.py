"""Priority-aware neighbor LIMIT behavior for work graph payload."""

from __future__ import annotations

from typing import Any

from science_graphrag.api.works.graph_neighborhood import _work_graph_neighborhood_payload


class _Single:
    def __init__(self, data: dict[str, Any]):
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def single(self) -> _Single | None:
        if not self._rows:
            return None
        return _Single(self._rows[0])

    def __iter__(self):
        for row in self._rows:
            yield _Single(row)


def _neighbor_row(nid: str, ntype: str, rt: str = "HAS_AUTHORSHIP") -> dict[str, Any]:
    return {
        "nid": nid,
        "labs": [ntype],
        "rt": rt,
        "nlabel": f"{ntype}-{nid}",
        "src_id": "w-main",
        "tgt_id": nid,
        "n_pub_year": None,
        "n_doi": "",
        "n_arxiv": "",
        "n_venue": "",
        "n_ash_pos": None,
        "n_ash_aff": "",
        "n_ash_corr": None,
        "n_ash_author": "",
        "n_ash_inst": "",
    }


class _FakeSession:
    def run(self, query: str, **params: Any) -> _FakeResult:
        if "RETURN w.id AS wid" in query:
            return _FakeResult(
                [
                    {
                        "wid": "w-main",
                        "wtitle": "Main Work",
                        "wyear": 2024,
                        "wdoi": "",
                        "warxiv": "",
                        "wvenue": "",
                        "has_semantic": True,
                    }
                ]
            )
        if "RETURN count(r) AS c" in query:
            return _FakeResult([{"c": 55}])
        if "WITH labels(n) AS labs, count(r) AS c" in query:
            return _FakeResult([{"kind": "Method", "c": 5}, {"kind": "Author", "c": 50}])
        if (
            "MATCH (w:Work {id: $id})-[r]-(n)" in query
            and "OPTIONAL MATCH (n)-[:OF_AUTHOR]" in query
        ):
            if params.get("prefer_priority"):
                return _FakeResult(
                    [_neighbor_row(f"m{i}", "Method", "USES_METHOD") for i in range(1, 6)]
                )
            return _FakeResult([_neighbor_row(f"a{i}", "Author", "OF_AUTHOR") for i in range(1, 6)])
        if "UNWIND $ids AS aid" in query:
            return _FakeResult([])
        return _FakeResult([])


def test_work_graph_priority_limit_keeps_priority_nodes() -> None:
    payload = _work_graph_neighborhood_payload(
        _FakeSession(),  # type: ignore[arg-type]
        "w-main",
        neighbor_limit=10,
        depth=1,
        prioritize="Method,Dataset,Work",
    )
    assert payload is not None
    nodes = payload["nodes"]
    method_nodes = [n for n in nodes if n.get("type") == "Method"]
    assert len(method_nodes) == 5
    assert payload["meta"]["is_truncated"] is True
    assert payload["meta"]["skipped_by_kind"]["Author"] == 45
