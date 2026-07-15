import hashlib

# Nilai hash target dari GDB
target_hash = bytes([
    0x5e, 0xa5, 0xe6, 0x7c, 0xcb, 0x9b, 0x15, 0xd1,
    0x7c, 0x8f, 0x5b, 0x0b, 0xb1, 0x97, 0x64, 0x2e,
    0x74, 0x5f, 0x31, 0xd4, 0xe9, 0xea, 0x6e, 0xce,
    0xa0, 0xc9, 0x94, 0x2b, 0x68, 0x25, 0x0b, 0xf6
])

salt = b"ZeroDayS4lt2026!"

with open("indonesian_phrases", "r") as f:
    for line in f:
        phrase = line.strip().encode('utf-8')
        # PBKDF2 dengan 1000 iterasi
        computed = hashlib.pbkdf2_hmac('sha256', phrase, salt, 1000)
        if computed == target_hash:
            print(f"Ketemu! Phrase: {line.strip()}")
            print(f"Flag: DSG{{{computed.hex()}}}")
            break
