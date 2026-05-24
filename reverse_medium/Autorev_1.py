import socket                                       
import re;                                          #import library socket untuk komunikasi jaringan, dan re untuk operasi regex dalam mengekstrak data dari binary

HOST = "mysterious-sea.picoctf.net"
PORT = 60824                                        #port yang diberikan oleh soal

PROMPT = b"What's the secret?:"                     #marker yang digunakan untuk menandai akhir dari data yang dikirim oleh server, sehingga program tahu kapan harus mulai memproses data yang diterima

def recv_until(sock, marker, buffer = b""):         #fungsi untuk menerima data dari socket hingga marker ditemukan, dan menyimpan sisa data yang belum diproses dalam buffer
    while marker not in buffer:                     #selama marker belum ditemukan dalam buffer, terus menerima data dari socket dan menambahkannya ke buffer
        data = sock.recv(65536)
        if not data:                                #jika tidak ada data yang diterima, berarti koneksi telah ditutup, sehingga
            return buffer, b"", False               #mengembalikan buffer yang ada, buffer kosong untuk sisa data, dan False untuk menandakan bahwa marker tidak ditemukan
        buffer += data                              #jika marker ditemukan dalam buffer, maka memisahkan buffer menjadi dua bagian: bagian sebelum marker (chunk) dan bagian setelah marker (sisa buffer), dan mengembalikan keduanya beserta True untuk menandakan bahwa marker ditemukan

    idx = buffer.index(marker) + len(marker)
    return buffer[:idx],buffer[idx:], True

def extract_secret(hex_data):                       #fungsi untuk mengekstrak secret dari data hex yang diterima, dengan mencari pola tertentu dalam binary data yang dihasilkan dari hex tersebut
    blob = bytes.fromhex(hex_data.decode())

    pattern = rb"\xc7\x45[\x80-\xff](.{4})\xc7\x45[\x80-\xff]\x00\x00\x00\x00"
    match = re.search(pattern, blob, re.DOTALL) 

    if match:                                       #jika pola ditemukan dalam binary data, maka secret dapat diekstrak dari grup pertama dalam regex, yang merupakan 4 byte yang mengikuti pola tertentu dalam binary
        secret_bytes = match.group(1)
        return int.from_bytes(secret_bytes, "little", signed=False)
    
    marker = b"\xc7\x45\xfc"
    idx = blob.find(marker)

    if idx != -1:
        secret_bytes = blob[idx + 3 : idx + 7 ]
        return int.from_bytes(secret_bytes, "little", signed=False  )
    
    raise ValueError("secret tidak ditemukan di binary")

def main():                                         #fungsi utama untuk menjalankan program, yang akan membuat koneksi ke server, menerima data, mengekstrak secret, dan mengirimkannya kembali ke server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)                               #mengatur timeout untuk socket agar tidak menunggu terlalu lama jika server tidak merespons, sehingga program dapat menangani situasi di mana koneksi terputus atau server tidak merespons dengan lebih baik
    sock.connect((HOST, PORT))


    buffer = b""
    

    for round_no in range (1, 25):                     #loop untuk menjalankan 24 round, dimana setiap round akan menerima data dari server, mengekstrak secret, dan mengirimkannya kembali ke server
        chunk, buffer, ok = recv_until(sock, PROMPT, buffer)    #menerima data dari server hingga marker PROMPT ditemukan, dan menyimpan sisa data yang belum diproses dalam buffer untuk round berikutnya

        if not ok:
            print(chunk.decode(errors="ignore"))
            break
        
        hex_candidate = re.findall(rb"[0-9a-fA-F]{1000,}", chunk)

        if not hex_candidate:                           #jika tidak ditemukan data hex yang valid dalam chunk yang diterima, maka mencetak pesan error dan isi chunk untuk membantu debugging, kemudian keluar dari loop
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

if __name__ == "__main__":                             #memanggil fungsi main untuk menjalankan program
    main()