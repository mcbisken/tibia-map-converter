# appearances.py — minimal pure-stdlib reader for Canary's appearances.dat
# (a serialized protobuf "Appearances" message). Extracts only each object's
# id (field 1, varint) and name (field 4, bytes); all other fields are skipped
# by wire type. No protobuf library required.

def _read_varint(buf, i):
    shift = 0
    result = 0
    while True:
        if i >= len(buf):
            raise ValueError("truncated varint in appearances.dat")
        b = buf[i]; i += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, i
        shift += 7
        if shift > 63:
            raise ValueError("varint too long in appearances.dat")

def _skip_field(buf, i, wire):
    if wire == 0:                      # varint
        _, i = _read_varint(buf, i); return i
    if wire == 1:                      # 64-bit
        return i + 8
    if wire == 2:                      # length-delimited
        ln, i = _read_varint(buf, i); return i + ln
    if wire == 5:                      # 32-bit
        return i + 4
    raise ValueError(f"unsupported protobuf wire type {wire} in appearances.dat")

def _decode_name(b):
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError:
        return b.decode("latin-1")

def _parse_appearance(buf, start, end):
    i = start
    aid = None
    name = ""
    while i < end:
        tag, i = _read_varint(buf, i)
        field, wire = tag >> 3, tag & 7
        if field == 1 and wire == 0:
            aid, i = _read_varint(buf, i)
        elif field == 4 and wire == 2:
            ln, i = _read_varint(buf, i)
            name = _decode_name(buf[i:i + ln]); i += ln
        else:
            i = _skip_field(buf, i, wire)
    return aid, name

def read_appearances(path):
    """Return [(appearanceId:int, name:str)] for every object appearance."""
    with open(path, "rb") as f:
        buf = f.read()
    out = []
    i, n = 0, len(buf)
    while i < n:
        tag, i = _read_varint(buf, i)
        field, wire = tag >> 3, tag & 7
        if field == 1 and wire == 2:                 # Appearances.object
            ln, i = _read_varint(buf, i)
            aid, name = _parse_appearance(buf, i, i + ln)
            i += ln
            if aid is not None:
                out.append((aid, name))
        else:
            i = _skip_field(buf, i, wire)
    return out
