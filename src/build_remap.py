# build_remap.py — build sourceSID->targetSID remap anchored on clientID,
# relocating customs. Function-aware: items.otb group + flags break clientID
# ties and any match whose server-side function differs is flagged for review.
import otb

U16_MAX = 0xFFFF

# Flags that change how the server treats an item on the map.
CRITICAL_FLAGS = (otb.FLAG_BLOCK_SOLID | otb.FLAG_PICKUPABLE |
                  otb.FLAG_MOVEABLE | otb.FLAG_STACKABLE)

class RemapResult:
    __slots__ = ("mapping", "custom", "ambiguous", "unanchored", "mismatch",
                 "container_risk")
    def __init__(self):
        self.mapping = {}        # sourceSID -> targetSID (final id to write in map)
        self.custom = {}         # sourceSID -> new targetSID (relocated items)
        self.ambiguous = {}      # sourceSID -> [candidate target sids]
        self.unanchored = []     # sourceSID with no client id at all (still relocated)
        self.mismatch = {}       # sourceSID -> human-readable function difference
        self.container_risk = {} # sourceSID (used as container on map) -> targetSID
                                 # whose target definition is NOT a container

def _distro_client_index(distro):
    idx = {}  # clientID -> [distro sids]
    for sid, cid in distro.client_of.items():
        if cid:
            idx.setdefault(cid, []).append(sid)
    return idx

def _function_distance(source, target, src_sid, dst_sid):
    """(group differs, number of differing flag bits) — lower is closer."""
    group_diff = 0 if source.group_of.get(src_sid) == target.group_of.get(dst_sid) else 1
    xor = source.flags_of.get(src_sid, 0) ^ target.flags_of.get(dst_sid, 0)
    return (group_diff, bin(xor).count("1"))

def describe_mismatch(source, target, src_sid, dst_sid):
    """Return a human-readable function difference between a source item and the
    target item it was mapped to, or None if their function matches."""
    parts = []
    sg = source.group_of.get(src_sid)
    tg = target.group_of.get(dst_sid)
    if sg != tg:
        parts.append(f"group {otb.group_name(sg)} -> {otb.group_name(tg)}")
    diff = (source.flags_of.get(src_sid, 0) ^ target.flags_of.get(dst_sid, 0)) & CRITICAL_FLAGS
    if diff:
        parts.append("flags differ: " + ", ".join(otb.flag_names(diff)))
    return "; ".join(parts) if parts else None

def build_remap(source, target, used_ids, container_ids=frozenset()):
    """source/target: OtbData. used_ids: ids used on the map. container_ids:
    subset of used_ids that appear on the map as containers WITH contents."""
    res = RemapResult()
    cidx = _distro_client_index(target)
    next_free = max(target.items.keys()) + 1
    for sid in sorted(used_ids):
        if sid not in source.items:
            # id used on map but absent from the source OTB: leave unchanged, flag.
            res.mapping[sid] = sid
            res.unanchored.append(sid)
            continue
        cid = source.client_of.get(sid)
        candidates = cidx.get(cid) if cid else None
        if candidates:
            # Tiebreak when several target server ids share this client id:
            # prefer the candidate whose function (group, then flags) matches the
            # source item; equal-function ties fall back to the lowest server id.
            # Multi-candidate cases are still FLAGGED in `ambiguous` for review.
            chosen = min(sorted(candidates),
                         key=lambda c: _function_distance(source, target, sid, c))
            res.mapping[sid] = chosen
            if len(candidates) > 1:
                res.ambiguous[sid] = sorted(candidates)
            reason = describe_mismatch(source, target, sid, chosen)
            if reason:
                res.mismatch[sid] = reason
        else:
            # custom (or no client id): relocate to a fresh free id
            if next_free > U16_MAX:
                raise RuntimeError("ran out of u16 server-id space for customs")
            res.mapping[sid] = next_free
            res.custom[sid] = next_free
            if not cid:
                res.unanchored.append(sid)
            next_free += 1
    for sid in sorted(container_ids):
        new = res.mapping.get(sid)
        if new is None:
            continue
        if sid in res.custom:
            # relocated customs copy the source node verbatim -> group preserved
            eff_group = source.group_of.get(sid)
        else:
            eff_group = target.group_of.get(new)
        if eff_group != otb.GROUP_CONTAINER:
            res.container_risk[sid] = new
    return res

def _fmt_pos(positions):
    return ", ".join(f"({x},{y},{z})" for x, y, z in positions)

def write_report(res, source, target, used_ids, path, names=None, positions=None):
    """names: optional {sourceSID: name} (from source items.xml). positions:
    optional {sourceSID: [(x,y,z), ...]} sample map positions per id."""
    names = names or {}
    positions = positions or {}
    def label(sid):
        nm = names.get(sid)
        return f"{sid} '{nm}'" if nm else str(sid)
    def where(sid):
        pos = positions.get(sid)
        return f" @ {_fmt_pos(pos)}" if pos else ""
    lines = ["# Remap report", ""]
    lines.append(f"- map-used distinct ids: {len(used_ids)}")
    lines.append(f"- clean matches: {len(res.mapping) - len(res.custom) - len(res.unanchored)}")
    lines.append(f"- ambiguous (auto-resolved, function-aware): {len(res.ambiguous)}")
    lines.append(f"- function mismatches (review!): {len(res.mismatch)}")
    lines.append(f"- container risks (review!): {len(res.container_risk)}")
    lines.append(f"- relocated customs: {len(res.custom)}")
    lines.append(f"- unanchored (no client id / not in source OTB): {len(res.unanchored)}")
    lines.append("")
    if res.container_risk:
        lines.append("## Container risks (item has contents on map, target id is NOT a container)")
        lines.append("These WILL break: the server drops or rejects the contents.")
        for old, new in sorted(res.container_risk.items()):
            tg = otb.group_name(target.group_of.get(new))
            lines.append(f"- {label(old)} -> {new} (target group: {tg}){where(old)}")
        lines.append("")
    if res.mismatch:
        lines.append("## Function mismatches (matched by sprite, but server-side behavior differs)")
        for old, reason in sorted(res.mismatch.items()):
            lines.append(f"- {label(old)} -> {res.mapping[old]}: {reason}{where(old)}")
        lines.append("")
    if res.custom:
        lines.append("## Relocated customs (sourceSID -> newSID, clientID)")
        for old, new in sorted(res.custom.items()):
            lines.append(f"- {label(old)} -> {new} (cid {source.client_of.get(old)}){where(old)}")
        lines.append("")
    if res.ambiguous:
        lines.append("## Ambiguous (sourceSID: candidates -> chosen, function-aware)")
        for old, cands in sorted(res.ambiguous.items()):
            lines.append(f"- {label(old)}: {cands} -> {res.mapping[old]}{where(old)}")
        lines.append("")
    if res.unanchored:
        lines.append("## Unanchored")
        for sid in sorted(res.unanchored):
            lines.append(f"- {label(sid)}{where(sid)}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
