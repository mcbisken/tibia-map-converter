# write_otb.py — emit a new items.otb = distro base + relocated custom items,
# plus an items.custom.xml fragment cloned from Evolera items.xml.
import copy
import xml.etree.ElementTree as ET
import fileloader as fl
import otb

def with_server_id(node, new_sid):
    """Return a copy of an OTB item node with its SERVERID attr value replaced."""
    props = bytearray(node.props)
    i = 4  # skip flags u32
    n = len(props)
    while i < n:
        attr = props[i]; i += 1
        ln = int.from_bytes(props[i:i+2], "little"); i += 2
        if attr == otb.ITEM_ATTR_SERVERID:
            props[i:i+2] = int(new_sid).to_bytes(2, "little")
            return fl.Node(node.type, bytes(props), [])
        i += ln
    raise ValueError("node has no SERVERID attribute")

def build_new_otb(distro, evolera, custom):
    """distro: OtbData; evolera: OtbData or None; custom: {evoleraSID: newSID}.
    Returns the serialized new OTB bytes."""
    root = fl.Node(distro.root.type, distro.root.props, list(distro.root.children))
    for old_sid, new_sid in sorted(custom.items(), key=lambda kv: kv[1]):
        src = evolera.items[old_sid]
        root.children.append(with_server_id(src, new_sid))
    return fl.write_tree(distro.identifier, root)

def build_custom_xml(evolera_xml_path, custom, out_path):
    """Clone <item id="oldSID"> entries from Evolera items.xml into a fragment
    with the new ids. Returns the list of customs that had NO xml entry."""
    tree = ET.parse(evolera_xml_path)
    root = tree.getroot()
    by_id = {}
    for el in root.findall("item"):
        if el.get("id"):
            by_id[int(el.get("id"))] = el
        elif el.get("fromid") and el.get("toid"):
            for i in range(int(el.get("fromid")), int(el.get("toid")) + 1):
                by_id[i] = el
    out_root = ET.Element("items")
    missing = []
    for old_sid, new_sid in sorted(custom.items(), key=lambda kv: kv[1]):
        src = by_id.get(old_sid)
        if src is None:
            missing.append(old_sid)
            continue
        clone = copy.deepcopy(src)
        for k in ("fromid", "toid"):
            if k in clone.attrib:
                del clone.attrib[k]
        clone.set("id", str(new_sid))
        out_root.append(clone)
    ET.ElementTree(out_root).write(out_path, encoding="utf-8", xml_declaration=True)
    return missing
