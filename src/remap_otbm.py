# remap_otbm.py — rewrite OTBM item ids (item nodes + ground attrs) and the
# header's minorVersionItems. Reuses the generic fileloader tree.
import fileloader as fl

OTBM_TILE = 5
OTBM_ITEM = 6
OTBM_HOUSETILE = 14

OTBM_ATTR_TILE_FLAGS = 3
OTBM_ATTR_ITEM = 9

# OTBM_TileFlag_t::ZONE (iomap.h). When this bit is set in a tile's TILE_FLAGS
# u32, a zero-terminated list of uint16 zone ids follows the flags (engine:
# mapcache.cpp parseBasicTile / iomap.cpp parseTileArea). _tile_items models
# this list and steps over it; zone ids are not item ids and are left untouched.
TILE_FLAG_ZONE = 1 << 6

MINOR_OFFSET = 12  # u32 minorVersionItems in root props

def load(path):
    with open(path, "rb") as f:
        return fl.read_tree(f.read())

def save(identifier, root, path):
    with open(path, "wb") as f:
        f.write(fl.write_tree(identifier, root))

def _tile_header_len(node_type):
    if node_type == OTBM_TILE:
        return 2          # xoffset, yoffset
    if node_type == OTBM_HOUSETILE:
        return 6          # xoffset, yoffset, houseId(u32)
    return None

def _walk(root):
    """Yield every node (iterative, no recursion)."""
    stack = [root]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(node.children)

def collect_ids(root):
    ids = set()
    for node in _walk(root):
        if node.type == OTBM_ITEM:
            ids.add(int.from_bytes(node.props[0:2], "little"))
        elif node.type in (OTBM_TILE, OTBM_HOUSETILE):
            for _, val in _tile_items(node):
                ids.add(val)
    return ids

def _tile_items(node):
    """Yield (offset_of_item_u16, item_id) for each inline ground OTBM_ATTR_ITEM
    in a tile, stepping correctly over TILE_FLAGS (including the ZONE flag's
    zero-terminated uint16 zone-id list). Raises on any unmodeled attribute."""
    props = node.props
    i = _tile_header_len(node.type)
    n = len(props)
    while i < n:
        attr = props[i]; i += 1
        if attr == OTBM_ATTR_TILE_FLAGS:
            flags = int.from_bytes(props[i:i+4], "little")
            i += 4
            if flags & TILE_FLAG_ZONE:
                # zero-terminated list of uint16 zone ids (engine reads until a 0).
                while True:
                    zone = int.from_bytes(props[i:i+2], "little")
                    i += 2
                    if zone == 0:
                        break
        elif attr == OTBM_ATTR_ITEM:
            yield i, int.from_bytes(props[i:i+2], "little")
            i += 2
        else:
            raise ValueError(f"unexpected tile attr {attr} at offset {i-1} (type {node.type})")

def rewrite(root, mapping, set_minor=2):
    """In-place: rewrite item ids via mapping; if set_minor is not None, set the
    header minorVersionItems to that value."""
    if set_minor is not None:
        props = bytearray(root.props)
        props[MINOR_OFFSET:MINOR_OFFSET+4] = int(set_minor).to_bytes(4, "little")
        root.props = bytes(props)
    for node in _walk(root):
        if node.type == OTBM_ITEM:
            old = int.from_bytes(node.props[0:2], "little")
            new = mapping.get(old)
            if new is not None and new != old:
                p = bytearray(node.props)
                p[0:2] = int(new).to_bytes(2, "little")
                node.props = bytes(p)
        elif node.type in (OTBM_TILE, OTBM_HOUSETILE):
            edits = []
            for off, old in _tile_items(node):
                new = mapping.get(old)
                if new is not None and new != old:
                    edits.append((off, new))
            if edits:
                p = bytearray(node.props)
                for off, new in edits:
                    p[off:off+2] = int(new).to_bytes(2, "little")
                node.props = bytes(p)
