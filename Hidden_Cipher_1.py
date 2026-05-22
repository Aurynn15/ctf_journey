from itertools import cycle

cipher_hex = "235a201d702015483b1d412b265d3313501f0c072d135f0d2002302d5011305120100a452e"
key = b"S3Cr3t"

cipher = bytes.fromhex(cipher_hex)

plain = bytes([
    c ^ k
    for c, k in zip(cipher, cycle(key))
])

print(plain.decode())