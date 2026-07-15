key = 42

with open("encoded.bin", "rb") as f:
    encoded = f.read()

decoded = bytes((b - key) % 256 for b in encoded)

with open("recovered.bin", "wb") as f:
    f.write(decoded)

print(f"[+] Saved recovered file: recovered.bin")
print(f"[+] Size: {len(decoded)} bytes")
