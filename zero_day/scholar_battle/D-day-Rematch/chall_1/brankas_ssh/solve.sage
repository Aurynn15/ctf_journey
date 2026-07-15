#!/usr/bin/env sage
"""
Clean HNP lattice attack for ECDSA P-521 nonce bias recovery.
Uses the Howgrave-Graham & Smart elimination formulation + Kannan embedding.

Given ECDSA signatures where nonces k_i < B (B = 2^(521-L) for L bits of bias):
1. Eliminate d using a pivot signature
2. Set up HNP in k_0
3. Use Kannan embedding to convert CVP to SVP
4. LLL/BKZ finds k_0, from which d is recovered
"""

import json, binascii, hashlib, sys

n = 6864797660130609714981900799081393217269435300143305409394463459185543183397656052122559640661454554977296311391480858037121987999716643812574028291115057151

def load_sigs():
    with open('signatures.json') as f:
        sigs = json.load(f)
    
    session = []
    for sig in sigs:
        msg = binascii.unhexlify(sig['msg'])
        if b'session' in msg:
            h = int(int.from_bytes(hashlib.sha512(msg).digest(), 'big'))
            session.append((h, int(sig['r']), int(sig['s'])))
    return session

def try_attack(session_sigs, L, m):
    """
    Try HNP attack assuming top L bits of nonces are zero.
    Uses m signatures.
    """
    B = ZZ(2)**(521 - L)  # Bound on nonce
    
    sigs = session_sigs[:m]
    
    # Compute a_i = r_i * s_i^{-1} mod n, b_i = h_i * s_i^{-1} mod n
    # k_i = a_i * d + b_i mod n, with k_i < B
    a = []
    b = []
    for h, r, s in sigs:
        s_inv = inverse_mod(ZZ(s), ZZ(n))
        a.append((ZZ(r) * s_inv) % n)
        b.append((ZZ(h) * s_inv) % n)
    
    # Eliminate d using sig 0 as pivot:
    # k_i = alpha_i * k_0 + beta_i mod n
    a0_inv = inverse_mod(a[0], ZZ(n))
    alpha = [(a[i] * a0_inv) % n for i in range(1, m)]  # m-1 values
    beta = [(b[i] - alpha[i-1] * b[0]) % n for i in range(1, m)]  # m-1 values
    
    # Kannan embedding lattice: (m+1) x (m+1) matrix
    # Rows 0..m-2: n * e_j  (n in column j)
    # Row m-1: (alpha_1, ..., alpha_{m-1}, 1, 0)
    # Row m: (-beta_1, ..., -beta_{m-1}, 0, B)
    
    dim = m + 1
    M = Matrix(ZZ, dim, dim)
    
    for j in range(m - 1):
        M[j, j] = n
    
    for j in range(m - 1):
        M[m - 1, j] = alpha[j]
    M[m - 1, m - 1] = 1
    
    for j in range(m - 1):
        M[m, j] = -beta[j]
    M[m, m] = B
    
    # LLL reduction
    M_red = M.LLL()
    
    # Look for short vector with last component = ±B
    for row in M_red:
        if abs(row[m]) == B:
            sign = 1 if row[m] == -B else -1  # c_m = -1 gives last = -W
            # Actually: if row[m] = -B, then c_m = -1, and k_0 = row[m-1] * (-1) * (-1) = row[m-1]
            # if row[m] = +B, then this is the negated vector, so k_0 = -row[m-1]
            
            if row[m] == -B:
                k0 = ZZ(row[m - 1])
            else:  # row[m] == +B
                k0 = ZZ(-row[m - 1])
            
            # Ensure k0 is in [0, B)
            k0 = k0 % n
            if k0 >= B:
                # Try negative
                k0 = (-k0) % n
                if k0 >= B:
                    continue
            
            # Recover d
            d_candidate = ((k0 - b[0]) * a0_inv) % n
            
            # Verify with another signature
            k1 = (a[1] * d_candidate + b[1]) % n
            if k1 < B:
                return int(d_candidate)
    
    return None

def verify_d(d_val):
    """Verify d against public key"""
    from cryptography.hazmat.primitives.serialization import load_pem_public_key
    from cryptography.hazmat.primitives.asymmetric.ec import SECP521R1, derive_private_key
    
    with open('pubkey.pem', 'rb') as f:
        pub_key = load_pem_public_key(f.read())
    pub_numbers = pub_key.public_numbers()
    
    try:
        priv_key = derive_private_key(d_val, SECP521R1())
        priv_pub = priv_key.public_key().public_numbers()
        return priv_pub.x == pub_numbers.x and priv_pub.y == pub_numbers.y
    except:
        return False

def decrypt_flag(d_val):
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives.padding import PKCS7
    
    key_material = f"BRANKAS-v2|{d_val}|BK-2024-OPS".encode('ascii')
    K = hashlib.sha256(key_material).digest()
    
    with open('secret.enc', 'rb') as f:
        data = f.read()
    
    iv = data[:16]
    ciphertext = data[16:]
    
    cipher = Cipher(algorithms.AES(K), modes.CBC(iv))
    decryptor = cipher.decryptor()
    plaintext_padded = decryptor.update(ciphertext) + decryptor.finalize()
    
    unpadder = PKCS7(128).unpadder()
    plaintext = unpadder.update(plaintext_padded) + unpadder.finalize()
    return plaintext.decode('utf-8')

if __name__ == '__main__':
    session_sigs = load_sigs()
    print(f"Loaded {len(session_sigs)} session signatures")
    
    # Try different bias values
    for L in [9, 10, 11, 12, 16, 20, 24, 32, 64, 128, 256]:
        # Use as many sigs as needed: m > ceil(521/L) + margin
        m_needed = max(int(521 / L) + 5, 6)
        m = min(m_needed, len(session_sigs))
        
        print(f"\n=== Trying L={L} bits bias (B=2^{521-L}), m={m} sigs ===")
        
        d = try_attack(session_sigs, L, m)
        
        if d is not None:
            print(f"  Candidate d = {d}")
            print(f"  d bits = {d.bit_length()}")
            
            if verify_d(d):
                print(f"\n*** CORRECT KEY FOUND! ***")
                print(f"d = {d}")
                try:
                    flag = decrypt_flag(d)
                    print(f"\nFLAG: {flag}")
                except Exception as e:
                    print(f"Decryption error: {e}")
                sys.exit(0)
            else:
                print(f"  Does NOT match public key.")
        else:
            print(f"  No candidate found.")
    
    print("\nAll bias values failed.")
