import socket 
import re;

HOST = "mysterious-sea.picoctf.net"
PORT = 60824

PROMPT = b"What's the secret?:"

def recv_until(sock, marker, buffer = b""):
    while marker not in buffer:
        data = sock.recv(65536)
        if not data:
            return buffer, b"", False
        buffer += data

    idx = buffer.index(marker) + len(marker)
    return buffer[:idx],buffer[idx:], True

def extract_secret(hex_data):
    blob = bytes.fromhex(hex_data.decode())

    pattern = rb"\xc7\x45[\x80-\xff](.{4})\xc7\x45[\x80-\xff]\x00\x00\x00\x00"
    match = re.search(pattern, blob, re.DOTALL) 

    if match:
        secret_bytes = match.group(1)
        return int.from_bytes(secret_bytes, "little", signed=False)
    
    marker = b"\xc7\x45\xfc"
    idx = blob.find(marker)

    if idx != -1:
        secret_bytes = blob[idx + 3 : idx + 7 ]
        return int.from_bytes(secret_bytes, "little", signed=False  )
    
    raise ValueError("secret tidak ditemukan di binary")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((HOST, PORT))


    buffer = b""
    

    for round_no in range (1, 25):
        chunk, buffer, ok = recv_until(sock, PROMPT, buffer)

        if not ok:
            print(chunk.decode(errors="ignore"))
            break
        
        hex_candidate = re.findall(rb"[0-9a-fA-F]{1000,}", chunk)

        if not hex_candidate:
            print("tidak menemukan hex binary.")
            print(chunk.decode(errors="ignore"))
            break 

        hex_data = hex_candidate[-1]
        secret = extract_secret(hex_data)
        print(f"Round {round_no}: secret = {secret}")
        sock.sendall(str(secret).encode() + b"\n")

    try: 
        while True:
            data = sock.recv(4096)
            if not data:
                break
            print(data.decode(errors="ignore"), end="")
    except socket.timeout:
        pass

    sock.close()

if __name__ == "__main__":
    main()