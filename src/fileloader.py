# fileloader.py — generic OTB/OTBM node-tree (de)serializer with escape handling.
NODE_START = 0xFE
NODE_END = 0xFF
ESCAPE = 0xFD

class Node:
    __slots__ = ("type", "props", "children")
    def __init__(self, ntype, props, children):
        self.type = ntype
        self.props = props          # bytes (de-escaped)
        self.children = children    # list[Node]

def read_tree(data):
    """Return (identifier_bytes, root_node)."""
    if len(data) < 6:
        raise ValueError("file too small to be a node tree")
    identifier = data[0:4]
    pos = 4
    if data[pos] != NODE_START:
        raise ValueError("missing root NODE_START")
    pos += 1
    root = Node(data[pos], bytearray(), [])
    pos += 1
    stack = [root]
    while stack:
        node = stack[-1]
        b = data[pos]
        if b == NODE_START:
            pos += 1
            child = Node(data[pos], bytearray(), [])
            pos += 1
            node.children.append(child)
            stack.append(child)
        elif b == NODE_END:
            pos += 1
            node.props = bytes(node.props)
            stack.pop()
        elif b == ESCAPE:
            pos += 1
            node.props.append(data[pos]); pos += 1
        else:
            node.props.append(b); pos += 1
    return identifier, root

def write_tree(identifier, root):
    out = bytearray(identifier)
    out.append(NODE_START)
    stack = [[root, -1]]
    while stack:
        frame = stack[-1]
        node, idx = frame[0], frame[1]
        if idx == -1:
            out.append(node.type)
            for byte in node.props:
                if byte == NODE_START or byte == NODE_END or byte == ESCAPE:
                    out.append(ESCAPE)
                out.append(byte)
            frame[1] = 0
            continue
        if idx < len(node.children):
            frame[1] = idx + 1
            out.append(NODE_START)
            stack.append([node.children[idx], -1])
            continue
        out.append(NODE_END)
        stack.pop()
    return bytes(out)
