# scripts_scan.py — find server scripts that reference remapped item ids.
# The map rewrite changes item ids, but actions.xml/movements.xml/Lua scripts
# still carry the OLD ids; this scan lists every occurrence so the user can
# update them (heuristic: bare numeric literals, so expect some false hits
# where a number is an action id or a count rather than an item id).
import os, re

SCRIPT_EXTS = (".lua", ".xml")
MAX_FILE_BYTES = 8 * 1024 * 1024  # skip anything implausibly large for a script

_NUM = re.compile(r"(?<![\w.])(\d{3,5})(?![\w.])")

def scan_scripts(scripts_dir, changed, max_hits_per_id=25):
    """changed: {oldID: newID} from the remap. Returns {oldID: [(relpath, lineno)]}
    for every changed id (old != new) found in .lua/.xml files under scripts_dir."""
    targets = {old for old, new in changed.items() if old != new}
    if not targets:
        return {}
    hits = {}
    capped = set()
    for base, _dirs, files in os.walk(scripts_dir):
        for fname in files:
            if not fname.lower().endswith(SCRIPT_EXTS):
                continue
            path = os.path.join(base, fname)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
            except OSError:
                continue
            rel = os.path.relpath(path, scripts_dir)
            for lineno, line in enumerate(text.splitlines(), start=1):
                for m in _NUM.finditer(line):
                    iid = int(m.group(1))
                    if iid in targets and iid not in capped:
                        locs = hits.setdefault(iid, [])
                        locs.append((rel, lineno))
                        if len(locs) >= max_hits_per_id:
                            capped.add(iid)
    return hits

def write_report(hits, changed, path):
    lines = ["# Script impact report", ""]
    lines.append("Scripts referencing item ids that the remap CHANGED. These scripts")
    lines.append("still use the OLD id — update them to the new id (or verify the")
    lines.append("number is not an item id; this scan matches bare numeric literals).")
    lines.append("")
    lines.append(f"- remapped ids found in scripts: {len(hits)}")
    lines.append("")
    for old in sorted(hits):
        lines.append(f"## {old} -> {changed[old]}")
        for rel, lineno in hits[old]:
            lines.append(f"- {rel}:{lineno}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
