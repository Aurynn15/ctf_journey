import base64, hashlib, zlib

A = "a3f1c92b"        
B = "5e7d" + "40b6"   

key = hashlib.sha256(bytes.fromhex(A + B)).digest()[:16]

body_b64 = "vWKaHCBXJKC4imWSZUH5XzX3ndMRWqKQIr9L9Waql9yzzeb2MFdPQf+NoyYqZbN9K2l+PR+Z8k0lhmM8OgSO+wef3+SnF/acg3RYBrkALA=="
body = base64.b64decode(body_b64)          

xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(body)) 

secret = zlib.decompress(xored)
print(secret.decode())
