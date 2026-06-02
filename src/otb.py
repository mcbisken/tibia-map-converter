# otb.py — parse an items.otb into server-id-keyed nodes + client ids.
import fileloader as fl

ITEM_ATTR_SERVERID = 0x10
ITEM_ATTR_CLIENTID = 0x11

class OtbData:
    __slots__ = ("identifier", "root", "items", "client_of")
    def __init__(self, identifier, root, items, client_of):
        self.identifier = identifier
        self.root = root
        self.items = items          # {serverID: Node}
        self.client_of = client_of  # {serverID: clientID or None}

def _iter_attrs(props):
    """Yield (attr, value_bytes) over an OTB item node's props (skip u32 flags)."""
    i = 4  # skip flags u32
    n = len(props)
    while i < n:
        attr = props[i]; i += 1
        ln = int.from_bytes(props[i:i+2], "little"); i += 2
        val = props[i:i+ln]; i += ln
        yield attr, val

def read_attr_u16(node, which):
    for attr, val in _iter_attrs(node.props):
        if attr == which:
            return int.from_bytes(val[:2], "little")
    return None

def parse_otb(path):
    with open(path, "rb") as f:
        data = f.read()
    identifier, root = fl.read_tree(data)
    items, client_of = {}, {}
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
    return OtbData(identifier, root, items, client_of)
