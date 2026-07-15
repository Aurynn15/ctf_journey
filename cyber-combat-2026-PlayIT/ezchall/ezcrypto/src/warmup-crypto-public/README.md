# RSABox

An interactive RSA encryption oracle. Connect via TCP to explore public-key cryptography — encrypt messages, decrypt ciphertexts, and try to recover the encrypted flag.

## Source

`service.py` — the complete RSA oracle source code.

## Interface

TCP on port 8000:
```
nc <host> 8000
```

Commands:
- `encrypt <hex_value>` — encrypt a hex-encoded integer
- `decrypt <hex_value>` — decrypt a hex-encoded ciphertext
- `pubkey` — show the RSA public key
- `help` — show the command menu
- `quit` — disconnect
