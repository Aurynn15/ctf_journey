"""RSABox — interactive RSA encryption oracle over TCP."""

import os
import socket
import sys
import threading
from pathlib import Path

from Crypto.Util.number import bytes_to_long, getPrime, inverse
from Crypto.Util.number import long_to_bytes

FLAG_PATH = Path("/flag.txt")
SERVICE_PORT = int(os.environ.get("PORT", os.environ.get("AD_PLATFORM_SERVICE_PORT", "8000")))
E = 65537

P = getPrime(512)
Q = getPrime(512)
N = P * Q
D = inverse(E, (P - 1) * (Q - 1))

BANNER_TEMPLATE = """\
+----------------------------------------------+
|              RSABox v1.0                     |
|       Secure Message Encryption Oracle       |
+----------------------------------------------+

  Public key (n, e):
    n = {n}
    e = {e}

  Encrypted flag:
    c = {flag_ct}

  Commands:
    encrypt <hex>  - encrypt a hex-encoded message
    decrypt <hex>  - decrypt a hex-encoded ciphertext
    prove <flag>   - submit the flag to receive the unlock proof
    pubkey         - show the public key
    help           - show this menu
    quit           - disconnect

  NOTE: The encrypted flag cannot be decrypted directly.
"""

def load_flag() -> str:
    try:
        return FLAG_PATH.read_text().strip()
    except FileNotFoundError:
        return "PLAYIT{placeholder}"

def encrypt(m: int) -> int:
    return pow(m, E, N)

def decrypt(c: int) -> int:
    return pow(c, D, N)

def handle_client(conn: socket.socket, addr: tuple) -> None:
    flag_text = load_flag()
    flag_int = bytes_to_long(flag_text.encode("utf-8"))
    flag_ct = encrypt(flag_int)

    banner = BANNER_TEMPLATE.format(n=N, e=E, flag_ct=flag_ct)

    try:
        conn.settimeout(30)
        conn.sendall(banner.encode())

        while True:
            conn.sendall(b"\nrsa> ")
            try:
                data = conn.recv(4096)
                if not data:
                    break
            except socket.timeout:
                conn.sendall(b"\n[timeout] disconnecting.\n")
                break

            line = data.decode("utf-8", errors="replace").strip()
            if not line:
                continue

            parts = line.split(maxsplit=1)
            cmd = parts[0].lower()

            if cmd in ("quit", "exit"):
                conn.sendall(b"Goodbye.\n")
                break
            elif cmd == "help":
                conn.sendall(banner.encode())
            elif cmd == "pubkey":
                conn.sendall(f"n = {N}\ne = {E}\n".encode())
            elif cmd == "encrypt":
                if len(parts) < 2:
                    conn.sendall(b"[error] usage: encrypt <hex_value>\n")
                    continue
                try:
                    val = int(parts[1], 16)
                except ValueError:
                    conn.sendall(b"[error] invalid hex value\n")
                    continue
                if val <= 0 or val >= N:
                    conn.sendall(b"[error] value must be 0 < m < n\n")
                    continue
                ct = encrypt(val)
                conn.sendall(f"c = {ct}\n".encode())
            elif cmd == "decrypt":
                if len(parts) < 2:
                    conn.sendall(b"[error] usage: decrypt <hex_value>\n")
                    continue
                try:
                    ct = int(parts[1], 16)
                except ValueError:
                    conn.sendall(b"[error] invalid hex value\n")
                    continue
                if ct <= 0 or ct >= N:
                    conn.sendall(b"[error] ciphertext must be 0 < c < n\n")
                    continue
                if ct == flag_ct:
                    conn.sendall(b"[denied] direct decryption of this ciphertext is not permitted.\n")
                    continue
                pt = decrypt(ct)
                conn.sendall(f"m = {hex(pt)}\nm = {pt}\n".encode())

            elif cmd == "prove":
                submitted = parts[1] if len(parts) > 1 else ""
                stored = load_flag()
                if submitted != stored:
                    conn.sendall(b"[denied] invalid flag\n")
                    continue
                try:
                    proof = Path("/proof.txt").read_text().strip()
                except FileNotFoundError:
                    proof = ""
                if not proof:
                    proof = os.environ.get("AD_PLATFORM_UNLOCK_PROOF", "")
                conn.sendall(f"proof: {proof}\n".encode())

            else:
                conn.sendall(b"[error] unknown command. type 'help' for the menu.\n")
    except Exception as exc:
        try:
            conn.sendall(f"\n[error] {exc}\n".encode())
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass

def main() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", SERVICE_PORT))
    server.listen(10)
    print(f"RSABox listening on port {SERVICE_PORT}", flush=True)

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
