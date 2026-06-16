def create_nop_sled(size: int) -> bytes:
    return b'\x90' * size

def create_padding(size: int, char: bytes = b'A') -> bytes:
    if len(char) != 1:
        raise ValueError("Padding character must be a single byte.")
    return char * size

def generate_shellcode_placeholder(arch: str, os_type: str, shellcode_type: str) -> str:
    return f"플레이스홀더: {arch}/{os_type} {shellcode_type} 셸코드 생성 (미구현)"

