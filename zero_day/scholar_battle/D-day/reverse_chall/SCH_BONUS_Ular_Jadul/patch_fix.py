#!/usr/bin/env python3
import os

binary = "game"
patched = "game_patched"

with open(binary, "rb") as f:
    data = bytearray(f.read())

# daftar (offset, old_bytes, new_bytes)
patches = [
    (0x4158, b'\x7e\x19', b'\x90\x90'),  # jle 4173 → nop nop
    (0x4165, b'\x7e\x0c', b'\x90\x90'),  # jle 4173 → nop nop
    (0x2e3c, b'\x75\x3c', b'\x90\x90'),  # jne 2e7a → nop nop
    (0x2e49, b'\x75\x2f', b'\x90\x90'),  # jne 2e7a → nop nop
    (0x2e57, b'\x74\x21', b'\x90\x90'),  # je 2e7a → nop nop
]

for offset, old, new in patches:
    if data[offset:offset+len(old)] != old:
        print(f"❌ Warning: at 0x{offset:x}, expected {old.hex()} but got {data[offset:offset+len(old)].hex()}")
        print("   Binary mungkin sudah rusak. Pastikan menggunakan file game asli.")
        exit(1)
    else:
        data[offset:offset+len(new)] = new
        print(f"✅ Patched 0x{offset:x}: {old.hex()} → {new.hex()}")

with open(patched, "wb") as f:
    f.write(data)

os.chmod(patched, 0o755)
print(f"✅ Binary patched tersimpan: {patched}")
