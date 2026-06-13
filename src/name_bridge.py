# name_bridge.py — match source item ids to target (Canary) appearance ids by
# normalized name. Function-aware: appearance flags (container etc.) break
# same-name ties, and containers-in-use that land on a non-container target
# are flagged. Unmatched ids are kept unchanged and flagged for review.
import re

_WS = re.compile(r"\s+")

def normalize_name(s):
    return _WS.sub(" ", s.strip()).lower()

class NameRemapResult:
    __slots__ = ("mapping", "id_matched", "exact", "ambiguous", "unmatched",
                 "container_risk")
    def __init__(self):
        self.mapping = {}        # sourceID -> targetID (or sourceID if unmatched)
        self.id_matched = []     # sourceIDs kept as-is because the id already exists
                                 # in the target (same-era ID fast path)
        self.exact = {}          # sourceID -> targetID (unique name match)
        self.ambiguous = {}      # sourceID -> [candidate targetIDs]
        self.unmatched = []      # sourceIDs with no/empty/absent name match
        self.container_risk = {} # sourceID used as container on map -> chosen
                                 # targetID that is NOT a container (or unknown)

def _unpack(entry):
    """Accept (aid, name) or (aid, name, flags)."""
    aid, name = entry[0], entry[1]
    flags = entry[2] if len(entry) > 2 else frozenset()
    return aid, name, flags

def build_name_remap(src_names, target_appearances, used_ids, prefer_id=False,
                     src_types=None, container_ids=frozenset()):
    """src_names: {sid: name}; target_appearances: [(appearanceId, name[, flags])];
    used_ids: set of ids used on the map. src_types: optional {sid: items.xml
    type} of the source; container_ids: ids used WITH contents on the map.
    Returns a NameRemapResult.

    When prefer_id is True (same-era source, e.g. another appearances-era server),
    any used id that already exists as a target appearance id is kept unchanged
    (identity) before falling back to name matching. This is faster and more
    reliable than name matching when the source and target share an id space."""
    src_types = src_types or {}
    index = {}  # normalized name -> [appearance ids]
    target_ids = set()
    flags_of = {}
    for entry in target_appearances:
        aid, name, flags = _unpack(entry)
        target_ids.add(aid)
        flags_of[aid] = flags
        norm = normalize_name(name) if name else ""
        if not norm:
            continue
        index.setdefault(norm, []).append(aid)
    for k in index:
        index[k].sort()

    res = NameRemapResult()
    for sid in sorted(used_ids):
        if prefer_id and sid in target_ids:
            res.mapping[sid] = sid
            res.id_matched.append(sid)
            continue
        raw = src_names.get(sid)
        norm = normalize_name(raw) if raw else ""
        cands = index.get(norm) if norm else None
        if not cands:
            res.mapping[sid] = sid
            res.unmatched.append(sid)
            continue
        # Same-name tiebreak: when the source item is functionally a container
        # (used with contents on the map, or typed container in items.xml),
        # prefer a container-flagged candidate; equal ties go to the lowest id.
        wants_container = sid in container_ids or src_types.get(sid) == "container"
        if wants_container:
            chosen = min(cands,
                         key=lambda a: (0 if "container" in flags_of.get(a, ()) else 1, a))
        else:
            chosen = cands[0]
        res.mapping[sid] = chosen
        if len(cands) == 1:
            res.exact[sid] = chosen
        else:
            res.ambiguous[sid] = list(cands)
    for sid in sorted(container_ids):
        new = res.mapping.get(sid)
        if new is None:
            continue
        if "container" not in flags_of.get(new, frozenset()):
            res.container_risk[sid] = new
    return res

def write_report(res, src_names, path):
    lines = ["# Canary name-bridge report", ""]
    lines.append(f"- id matches (same-era, kept as-is): {len(res.id_matched)}")
    lines.append(f"- exact name matches: {len(res.exact)}")
    lines.append(f"- ambiguous (auto-resolved, function-aware): {len(res.ambiguous)}")
    lines.append(f"- container risks (review!): {len(res.container_risk)}")
    lines.append(f"- unmatched (left unchanged): {len(res.unmatched)}")
    lines.append("")
    if res.container_risk:
        lines.append("## Container risks (item has contents on map, target is NOT a container)")
        lines.append("These WILL break: the server drops or rejects the contents.")
        for sid, new in sorted(res.container_risk.items()):
            lines.append(f"- {sid} '{src_names.get(sid, '')}' -> {new}")
        lines.append("")
    if res.ambiguous:
        lines.append("## Ambiguous (sourceID 'name' -> chosen [candidates])")
        for sid, cands in sorted(res.ambiguous.items()):
            lines.append(f"- {sid} '{src_names.get(sid, '')}' -> {res.mapping[sid]} {cands}")
        lines.append("")
    if res.unmatched:
        lines.append("## Unmatched (kept original id)")
        for sid in sorted(res.unmatched):
            lines.append(f"- {sid} '{src_names.get(sid, '')}'")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
