# convert.py — path-free orchestrators. Two modes:
#   convert()            : OTB -> OTB clientID-anchored remap (classic, v1.0)
#   convert_to_canary()  : source items.xml names -> Canary appearances.dat ids
# Both write outputs atomically (temp dir -> move on full success) and can
# optionally scan a server scripts folder for references to remapped ids.
import os, json, shutil, tempfile
import otb, build_remap, write_otb
import appearances, itemsxml, name_bridge
import scripts_scan
import remap_otbm as rm

class Summary:
    __slots__ = ("matches", "customs", "ambiguous", "unanchored", "changed",
                 "mismatches", "container_risks", "script_hits",
                 "out_map", "out_otb", "out_custom_xml", "out_report", "out_json",
                 "out_script_report",
                 "missing_xml", "exact", "unmatched", "id_matched")
    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

def _atomic_outputs(out_dir, build):
    """build(work_dir) -> list of temp file paths to publish. Files are written
    under a temp dir and moved into out_dir only if build() fully succeeds.
    Returns {basename: published_path}."""
    work = tempfile.mkdtemp(prefix="otbm-remap-")
    try:
        produced = build(work)
        os.makedirs(out_dir, exist_ok=True)
        placed = {}
        for p in produced:
            dst = os.path.join(out_dir, os.path.basename(p))
            shutil.move(p, dst)
            placed[os.path.basename(p)] = dst
        return placed
    finally:
        shutil.rmtree(work, ignore_errors=True)

def _scan_scripts(scripts_dir, mapping, work, files, log):
    """Append a script-impact report to `files` if scripts_dir is given.
    Returns the number of remapped ids found referenced in scripts."""
    if not scripts_dir:
        return None
    changed = {k: v for k, v in mapping.items() if k != v}
    log(f"scanning scripts in {scripts_dir} for {len(changed)} remapped ids...")
    hits = scripts_scan.scan_scripts(scripts_dir, changed)
    p = os.path.join(work, "script-impact.md")
    scripts_scan.write_report(hits, changed, p)
    files.append(p)
    if hits:
        log(f"  WARNING: {len(hits)} remapped ids are referenced in scripts "
            "(see script-impact.md)")
    else:
        log("  no script references to remapped ids found")
    return len(hits)

def convert(map_path, src_otb_path, dst_otb_path, out_dir, src_xml=None,
            scripts_dir=None, log=print):
    """Classic OTB->OTB clientID remap. Writes outputs only on full success."""
    log("parsing item tables...")
    source = otb.parse_otb(src_otb_path)
    target = otb.parse_otb(dst_otb_path)
    log(f"  source items={len(source.items)} target items={len(target.items)}")

    log("loading map + collecting used item ids...")
    ident, root = rm.load(map_path)
    usage = rm.collect_usage(root)
    used = usage.ids
    log(f"  map uses {len(used)} distinct item ids "
        f"({len(usage.container_ids)} as containers with contents)")

    log("building remap table (function-aware)...")
    res = build_remap.build_remap(source, target, used,
                                  container_ids=usage.container_ids)
    matches = len(res.mapping) - len(res.custom) - len(res.unanchored)
    changed = sum(1 for k, v in res.mapping.items() if k != v)
    log(f"  matches={matches} customs={len(res.custom)} "
        f"ambiguous={len(res.ambiguous)} unanchored={len(res.unanchored)} "
        f"changed={changed}")
    if res.mismatch:
        log(f"  WARNING: {len(res.mismatch)} function mismatches (see remap-report.md)")
    if res.container_risk:
        log(f"  WARNING: {len(res.container_risk)} container risks (see remap-report.md)")

    names = itemsxml.read_item_names(src_xml) if src_xml else None
    base = os.path.splitext(os.path.basename(map_path))[0]
    missing_xml = []
    script_hits = []

    def build(work):
        files = []
        p_report = os.path.join(work, "remap-report.md")
        build_remap.write_report(res, source, target, used, p_report,
                                 names=names, positions=usage.positions)
        files.append(p_report)

        p_json = os.path.join(work, "remap.json")
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in res.mapping.items()}, f, indent=0)
        files.append(p_json)

        log("writing new items.otb...")
        p_otb = os.path.join(work, "items.otb")
        with open(p_otb, "wb") as f:
            f.write(write_otb.build_new_otb(target, source, res.custom))
        files.append(p_otb)

        if res.custom and src_xml:
            p_xml = os.path.join(work, "items.custom.xml")
            mx = write_otb.build_custom_xml(src_xml, res.custom, p_xml)
            missing_xml.extend(mx)
            files.append(p_xml)
            if mx:
                log(f"  WARNING: {len(mx)} customs had no items.xml entry")
        elif res.custom:
            log("  NOTE: customs relocated but no source items.xml supplied — "
                "add their server-side definitions manually (see remap-report.md).")

        script_hits.append(_scan_scripts(scripts_dir, res.mapping, work, files, log))

        log("rewriting map item ids...")
        rm.rewrite(root, res.mapping, set_minor=None)
        p_map = os.path.join(work, f"{base}.remapped.otbm")
        rm.save(ident, root, p_map)
        files.append(p_map)
        return files

    placed = _atomic_outputs(out_dir, build)
    log(f"done. outputs in {out_dir}")
    return Summary(matches=matches, customs=len(res.custom),
                   ambiguous=len(res.ambiguous), unanchored=len(res.unanchored),
                   changed=changed, mismatches=len(res.mismatch),
                   container_risks=len(res.container_risk),
                   script_hits=script_hits[0],
                   out_map=placed[f"{base}.remapped.otbm"],
                   out_otb=placed["items.otb"],
                   out_custom_xml=placed.get("items.custom.xml"),
                   out_report=placed["remap-report.md"], out_json=placed["remap.json"],
                   out_script_report=placed.get("script-impact.md"),
                   missing_xml=missing_xml)

def convert_to_canary(map_path, src_xml, appearances_path, out_dir, log=print,
                      prefer_id=False, scripts_dir=None):
    """Match source items.xml names to Canary appearances.dat ids and rewrite the
    map. Unmatched ids are kept unchanged and listed in the report.

    prefer_id=True enables the same-era ID fast path: a used id that already exists
    as a target appearance id is kept as-is before any name matching."""
    log("reading target appearances.dat...")
    target = appearances.read_appearances(appearances_path)
    log(f"  target appearances={len(target)}")

    log("reading source items.xml names + types...")
    src_names = itemsxml.read_item_names(src_xml)
    src_types = itemsxml.read_item_types(src_xml)
    log(f"  source named items={len(src_names)}")

    log("loading map + collecting used item ids...")
    ident, root = rm.load(map_path)
    usage = rm.collect_usage(root)
    used = usage.ids
    log(f"  map uses {len(used)} distinct item ids "
        f"({len(usage.container_ids)} as containers with contents)")

    log("matching by name..." if not prefer_id else "matching by id, then name...")
    res = name_bridge.build_name_remap(src_names, target, used, prefer_id=prefer_id,
                                       src_types=src_types,
                                       container_ids=usage.container_ids)
    changed = sum(1 for k, v in res.mapping.items() if k != v)
    log(f"  id_matched={len(res.id_matched)} exact={len(res.exact)} "
        f"ambiguous={len(res.ambiguous)} unmatched={len(res.unmatched)} changed={changed}")
    if res.container_risk:
        log(f"  WARNING: {len(res.container_risk)} container risks (see remap-report.md)")

    base = os.path.splitext(os.path.basename(map_path))[0]
    script_hits = []

    def build(work):
        files = []
        p_report = os.path.join(work, "remap-report.md")
        name_bridge.write_report(res, src_names, p_report)
        files.append(p_report)

        p_json = os.path.join(work, "remap.json")
        with open(p_json, "w", encoding="utf-8") as f:
            json.dump({str(k): v for k, v in res.mapping.items()}, f, indent=0)
        files.append(p_json)

        script_hits.append(_scan_scripts(scripts_dir, res.mapping, work, files, log))

        log("rewriting map item ids...")
        rm.rewrite(root, res.mapping, set_minor=None)
        p_map = os.path.join(work, f"{base}.remapped.otbm")
        rm.save(ident, root, p_map)
        files.append(p_map)
        return files

    placed = _atomic_outputs(out_dir, build)
    log(f"done. outputs in {out_dir}")
    return Summary(id_matched=len(res.id_matched), exact=len(res.exact),
                   ambiguous=len(res.ambiguous), unmatched=len(res.unmatched),
                   changed=changed, container_risks=len(res.container_risk),
                   script_hits=script_hits[0],
                   out_map=placed[f"{base}.remapped.otbm"],
                   out_report=placed["remap-report.md"], out_json=placed["remap.json"],
                   out_script_report=placed.get("script-impact.md"))
