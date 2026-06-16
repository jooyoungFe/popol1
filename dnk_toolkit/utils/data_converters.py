import struct

def p32(value: int) -> bytes:
    return struct.pack("<I", value & 0xFFFFFFFF)

def p64(value: int) -> bytes:
    return struct.pack("<Q", value & 0xFFFFFFFFFFFFFFFF)

def u32(value: bytes) -> int:
    return struct.unpack("<I", value)[0]

def u64(value: bytes) -> int:
    return struct.unpack("<Q", value)[0]
