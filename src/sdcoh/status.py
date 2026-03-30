"""Compare file mtimes to detect stale downstream documents."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sdcoh.scanner import ScanResult

# Ignore mtime differences smaller than this to avoid false positives
# from near-simultaneous file creation.
_STALE_THRESHOLD = timedelta(seconds=0.05)


@dataclass
class StaleEntry:
    """A node that needs updating."""

    node_id: str
    node_mtime: str
    cause_id: str
    cause_mtime: str
    relation: str


def check_status(result: ScanResult) -> list[StaleEntry]:
    """Find nodes whose upstream dependencies are newer than they are."""
    mtime_map: dict[str, datetime] = {}
    for node in result.nodes:
        mtime_map[node["id"]] = datetime.fromisoformat(node["mtime"])

    stale: list[StaleEntry] = []
    seen: set[str] = set()

    for edge in result.edges:
        if edge["direction"] == "depends_on":
            # source depends_on target. If target is newer → source is stale
            src = edge["source"]
            tgt = edge["target"]
            src_time = mtime_map.get(src)
            tgt_time = mtime_map.get(tgt)
            if src_time and tgt_time and (tgt_time - src_time) > _STALE_THRESHOLD:
                key = f"{src}<-{tgt}"
                if key not in seen:
                    seen.add(key)
                    stale.append(
                        StaleEntry(
                            node_id=src,
                            node_mtime=src_time.isoformat(),
                            cause_id=tgt,
                            cause_mtime=tgt_time.isoformat(),
                            relation=edge["relation"],
                        )
                    )

        elif edge["direction"] == "updates":
            # source updates target. If source is newer → target is stale
            src = edge["source"]
            tgt = edge["target"]
            src_time = mtime_map.get(src)
            tgt_time = mtime_map.get(tgt)
            if src_time and tgt_time and (src_time - tgt_time) > _STALE_THRESHOLD:
                key = f"{tgt}<-{src}"
                if key not in seen:
                    seen.add(key)
                    stale.append(
                        StaleEntry(
                            node_id=tgt,
                            node_mtime=tgt_time.isoformat(),
                            cause_id=src,
                            cause_mtime=src_time.isoformat(),
                            relation=edge["relation"],
                        )
                    )

    return sorted(stale, key=lambda s: s.node_id)
