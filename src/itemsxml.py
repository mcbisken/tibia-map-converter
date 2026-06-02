# itemsxml.py — read a server items.xml into {serverID: name}. Handles both
# <item id=.. name=..> and <item fromid=.. toid=.. name=..> range entries.
# Names are returned raw (normalization happens in name_bridge).
import xml.etree.ElementTree as ET

def read_item_names(path):
    root = ET.parse(path).getroot()
    names = {}
    for el in root.findall("item"):
        name = el.get("name")
        if name is None:
            continue
        if el.get("id") is not None:
            names[int(el.get("id"))] = name
        elif el.get("fromid") is not None and el.get("toid") is not None:
            for i in range(int(el.get("fromid")), int(el.get("toid")) + 1):
                names[i] = name
    return names
