# build_remap.py — build evoleraSID->distroSID remap, relocating customs.
U16_MAX = 0xFFFF

class RemapResult:
    __slots__ = ("mapping", "custom", "ambiguous", "unanchored")
    def __init__(self):
        self.mapping = {}      # evoleraSID -> distroSID (final id to write in map)
        self.custom = {}       # evoleraSID -> new distroSID (relocated items)
        self.ambiguous = {}    # evoleraSID -> [candidate distro sids]
        self.unanchored = []   # evoleraSID with no client id at all (still relocated)

def _distro_client_index(distro):
    idx = {}  # clientID -> [distro sids]
    for sid, cid in distro.client_of.items():
        if cid:
            idx.setdefault(cid, []).append(sid)
    return idx

def build_remap(evolera, distro, used_ids):
    res = RemapResult()
    cidx = _distro_client_index(distro)
    next_free = max(distro.items.keys()) + 1
    for sid in sorted(used_ids):
        if sid not in evolera.items:
            # id used on map but absent from Evolera OTB: leave unchanged, flag.
            res.mapping[sid] = sid
            res.unanchored.append(sid)
            continue
        cid = evolera.client_of.get(sid)
        candidates = cidx.get(cid) if cid else None
        if candidates:
            # Tiebreak when several distro server ids share this client id:
            # pick the lowest server id and FLAG it in `ambiguous` for review.
            # (The Evolutions map produced zero ambiguous cases; if a future map
            # does, revisit whether a type/flags-aware tiebreak is warranted.)
            chosen = sorted(candidates)[0]
            res.mapping[sid] = chosen
            if len(candidates) > 1:
                res.ambiguous[sid] = sorted(candidates)
        else:
            # custom (or no client id): relocate to a fresh free id
            if next_free > U16_MAX:
                raise RuntimeError("ran out of u16 server-id space for customs")
            res.mapping[sid] = next_free
            res.custom[sid] = next_free
            if not cid:
                res.unanchored.append(sid)
            next_free += 1
    return res

def write_report(res, evolera, distro, used_ids, path):
    lines = ["# Remap report", ""]
    lines.append(f"- map-used distinct ids: {len(used_ids)}")
    lines.append(f"- clean matches: {len(res.mapping) - len(res.custom) - len(res.unanchored)}")
    lines.append(f"- ambiguous (auto-resolved, lowest sid): {len(res.ambiguous)}")
    lines.append(f"- relocated customs: {len(res.custom)}")
    lines.append(f"- unanchored (no client id / not in Evolera OTB): {len(res.unanchored)}")
    lines.append("")
    if res.custom:
        lines.append("## Relocated customs (evoleraSID -> newSID, clientID)")
        for old, new in sorted(res.custom.items()):
            lines.append(f"- {old} -> {new} (cid {evolera.client_of.get(old)})")
        lines.append("")
    if res.ambiguous:
        lines.append("## Ambiguous (evoleraSID: candidates -> chosen)")
        for old, cands in sorted(res.ambiguous.items()):
            lines.append(f"- {old}: {cands} -> {res.mapping[old]}")
        lines.append("")
    if res.unanchored:
        lines.append("## Unanchored")
        lines.append(", ".join(str(x) for x in sorted(res.unanchored)))
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
