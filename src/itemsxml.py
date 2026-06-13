# itemsxml.py — read a server items.xml into {serverID: name} / {serverID: type}.
# Handles both <item id=.. name=..> and <item fromid=.. toid=..> range entries.
# Names are returned raw (normalization happens in name_bridge).
import xml.etree.ElementTree as ET

def _iter_ids(el):
    if el.get("id") is not None:
        yield int(el.get("id"))
    elif el.get("fromid") is not None and el.get("toid") is not None:
        yield from range(int(el.get("fromid")), int(el.get("toid")) + 1)

def read_item_names(path):
    root = ET.parse(path).getroot()
    names = {}
    for el in root.findall("item"):
        name = el.get("name")
        if name is None:
            continue
        for i in _iter_ids(el):
            names[i] = name
    return names

def read_item_types(path):
    """{serverID: lowercased type attribute} for items that declare one
    (container, door, teleport, key, bed, depot, ...)."""
    root = ET.parse(path).getroot()
    types = {}
    for el in root.findall("item"):
        typ = el.get("type")
        if typ is None:
            continue
        for i in _iter_ids(el):
            types[i] = typ.lower()
    return types
