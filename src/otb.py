# otb.py — parse an items.otb into server-id-keyed nodes, client ids, and
# function data (item group + flags) used for function-aware matching.
import fileloader as fl

ITEM_ATTR_SERVERID = 0x10
ITEM_ATTR_CLIENTID = 0x11

# Item groups (the OTB item node's type byte, itemloader.h ITEM_GROUP_*).
GROUP_NONE = 0
GROUP_GROUND = 1
GROUP_CONTAINER = 2
GROUP_TELEPORT = 7
GROUP_MAGICFIELD = 8
GROUP_SPLASH = 11
GROUP_FLUID = 12
GROUP_DOOR = 13

_GROUP_NAMES = {0: "none", 1: "ground", 2: "container", 3: "weapon",
                4: "ammunition", 5: "armor", 6: "charges", 7: "teleport",
                8: "magicfield", 9: "writeable", 10: "key", 11: "splash",
                12: "fluid", 13: "door", 14: "deprecated"}

def group_name(group):
    return _GROUP_NAMES.get(group, f"group-{group}")

# Item flags (first u32 of an OTB item node's props, itemloader.h FLAG_*).
FLAG_BLOCK_SOLID = 1 << 0
FLAG_PICKUPABLE = 1 << 5
FLAG_MOVEABLE = 1 << 6
FLAG_STACKABLE = 1 << 7

_FLAG_NAMES = {FLAG_BLOCK_SOLID: "block-solid", FLAG_PICKUPABLE: "pickupable",
               FLAG_MOVEABLE: "moveable", FLAG_STACKABLE: "stackable"}

def flag_names(flags):
    return [name for bit, name in sorted(_FLAG_NAMES.items()) if flags & bit]

class OtbData:
    __slots__ = ("identifier", "root", "items", "client_of", "group_of", "flags_of")
    def __init__(self, identifier, root, items, client_of, group_of, flags_of):
        self.identifier = identifier
        self.root = root
        self.items = items          # {serverID: Node}
        self.client_of = client_of  # {serverID: clientID or None}
        self.group_of = group_of    # {serverID: item group (node type byte)}
        self.flags_of = flags_of    # {serverID: flags u32}

def _iter_attrs(props):
    """Yield (attr, value_bytes) over an OTB item node's props (skip u32 flags)."""
    i = 4  # skip flags u32
    n = len(props)
    while i < n:
        attr = props[i]; i += 1
        ln = int.from_bytes(props[i:i+2], "little"); i += 2
        val = props[i:i+ln]; i += ln
        yield attr, val

def parse_otb(path):
    with open(path, "rb") as f:
        data = f.read()
    identifier, root = fl.read_tree(data)
    items, client_of, group_of, flags_of = {}, {}, {}, {}
    for node in root.children:
        sid = None
        cid = None
        for attr, val in _iter_attrs(node.props):
            if attr == ITEM_ATTR_SERVERID:
                sid = int.from_bytes(val[:2], "little")
            elif attr == ITEM_ATTR_CLIENTID:
                cid = int.from_bytes(val[:2], "little")
        if sid is None:
            continue
        items[sid] = node
        client_of[sid] = cid
        group_of[sid] = node.type
        flags_of[sid] = int.from_bytes(node.props[0:4], "little")
    return OtbData(identifier, root, items, client_of, group_of, flags_of)
