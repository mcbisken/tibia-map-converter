# name_bridge.py — match source item ids to target (Canary) appearance ids by
# normalized name. Unmatched ids are kept unchanged and flagged for review.
import re

_WS = re.compile(r"\s+")

def normalize_name(s):
    return _WS.sub(" ", s.strip()).lower()

class NameRemapResult:
    __slots__ = ("mapping", "id_matched", "exact", "ambiguous", "unmatched")
    def __init__(self):
        self.mapping = {}      # sourceID -> targetID (or sourceID if unmatched)
        self.id_matched = []   # sourceIDs kept as-is because the id already exists
                               # in the target (same-era ID fast path)
        self.exact = {}        # sourceID -> targetID (unique name match)
        self.ambiguous = {}    # sourceID -> [candidate targetIDs] (lowest chosen)
        self.unmatched = []    # sourceIDs with no/empty/absent name match

def build_name_remap(src_names, target_appearances, used_ids, prefer_id=False):
    """src_names: {sid: name}; target_appearances: [(appearanceId, name)];
    used_ids: set of ids used on the map. Returns a NameRemapResult.

    When prefer_id is True (same-era source, e.g. another appearances-era server),
    any used id that already exists as a target appearance id is kept unchanged
    (identity) before falling back to name matching. This is faster and more
    reliable than name matching when the source and target share an id space."""
    index = {}  # normalized name -> [appearance ids]
    target_ids = set()
    for aid, name in target_appearances:
        target_ids.add(aid)
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
        chosen = cands[0]
        res.mapping[sid] = chosen
        if len(cands) == 1:
            res.exact[sid] = chosen
        else:
            res.ambiguous[sid] = list(cands)
    return res

def write_report(res, src_names, path):
    lines = ["# Canary name-bridge report", ""]
    lines.append(f"- id matches (same-era, kept as-is): {len(res.id_matched)}")
    lines.append(f"- exact name matches: {len(res.exact)}")
    lines.append(f"- ambiguous (auto-picked lowest id): {len(res.ambiguous)}")
    lines.append(f"- unmatched (left unchanged): {len(res.unmatched)}")
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
