import struct

from errors import DBError


def coerce(value: str, typ: str):
    if typ == "INTEGER":
        try:
            return int(value)
        except (ValueError, TypeError):
            raise DBError(f"Cannot store {value!r} as INTEGER")
    if typ == "REAL":
        try:
            return float(value)
        except (ValueError, TypeError):
            raise DBError(f"Cannot store {value!r} as REAL")
    if typ == "BOOLEAN":
        if str(value).upper() == "TRUE":
            return True
        if str(value).upper() == "FALSE":
            return False
        raise DBError(f"Cannot store {value!r} as BOOLEAN")
    return str(value)


def display(value, typ: str) -> str:
    if typ == "BOOLEAN":
        return "TRUE" if value else "FALSE"
    return str(value)


def serialize_field(value, typ: str) -> bytes:
    if typ == "INTEGER":
        return struct.pack(">q", int(value))
    if typ == "REAL":
        return struct.pack(">d", float(value))
    if typ == "BOOLEAN":
        return struct.pack(">?", bool(value))
    encoded = str(value).encode("utf-8")
    return struct.pack(">H", len(encoded)) + encoded


def deserialize_field(data: bytes, typ: str, offset: int) -> tuple:
    if typ == "INTEGER":
        return struct.unpack_from(">q", data, offset)[0], offset + 8
    if typ == "REAL":
        return struct.unpack_from(">d", data, offset)[0], offset + 8
    if typ == "BOOLEAN":
        return struct.unpack_from(">?", data, offset)[0], offset + 1
    length = struct.unpack_from(">H", data, offset)[0]
    offset += 2
    return data[offset: offset + length].decode("utf-8"), offset + length


def serialize_row(row: list, types: list) -> bytes:
    return b"".join(serialize_field(v, t) for v, t in zip(row, types))


def deserialize_row(data: bytes, types: list) -> list:
    row, offset = [], 0
    for t in types:
        v, offset = deserialize_field(data, t, offset)
        row.append(v)
    return row
