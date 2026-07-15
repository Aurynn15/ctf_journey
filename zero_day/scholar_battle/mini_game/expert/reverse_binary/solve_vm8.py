#!/usr/bin/env python3
from pathlib import Path

data = Path("vm8_chall").read_bytes()

KEY = 0x77
OFF = 0x20a0
LEN = 0xee  # sampai akhir bytecode dari rodata

bc = bytes(b ^ KEY for b in data[OFF:OFF+LEN])

print("[+] decoded bytecode:")
print(bc.hex(" "))

mem = [0] * 256
stack = []
callstack = []
pc = 0

while pc < len(bc):
    op = bc[pc]

    if op == 0x01:          # PUSH
        stack.append(bc[pc+1])
        pc += 2

    elif op == 0x02:        # XOR
        b = stack.pop()
        a = stack.pop()
        stack.append((a ^ b) & 0xff)
        pc += 1

    elif op == 0x03:        # ADD imm
        val = stack.pop()
        imm = bc[pc+1]
        stack.append((val + imm) & 0xff)
        pc += 2

    elif op == 0x04:        # STORE addr
        addr = bc[pc+1]
        mem[addr] = stack.pop()
        pc += 2

    elif op == 0x05:        # LOAD addr
        addr = bc[pc+1]
        stack.append(mem[addr])
        pc += 2

    elif op == 0x06:        # CALL addr
        addr = bc[pc+1]
        callstack.append(pc + 2)
        pc = addr

    elif op == 0x07:        # RET
        if not callstack:
            break
        pc = callstack.pop()

    elif op == 0x08:        # PRINT
        break

    else:
        raise Exception(f"unknown opcode {op:#x} at pc={pc:#x}")

flag = bytes(mem[:29]).decode()
print("[+] raw VM memory:")
print(flag)

print("[+] binary fake/transformed output would be:")
print(bytes(x ^ 0x55 for x in mem[:29]))
