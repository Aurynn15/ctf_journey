#!/usr/bin/env python3

from pathlib import Path
import string

data = Path("vm_chall").read_bytes()

def run_vm(code, start):
    stack = []
    out = []
    ip = start
    steps = 0

    while ip < len(code) and steps < 10000:
        steps += 1
        op = code[ip]
        ip += 1

        if op == 0x01:  # PUSH byte
            if ip >= len(code):
                return None
            stack.append(code[ip])
            ip += 1

        elif op == 0x02:  # XOR
            if len(stack) < 2:
                return None
            b = stack.pop()
            a = stack.pop()
            stack.append(a ^ b)

        elif op == 0x03:  # PRINT
            if not stack:
                return None
            ch = stack.pop()
            if ch not in range(0x20, 0x7f) and ch not in (0x0a, 0x0d, 0x09):
                return None
            out.append(chr(ch))

        elif op == 0x04:  # HALT
            text = "".join(out)
            if len(text) >= 5:
                return text
            return None

        else:
            return None

    return None


results = []

for i in range(len(data)):
    text = run_vm(data, i)
    if text:
        score = 0
        if "flag" in text.lower():
            score += 10
        if "{" in text and "}" in text:
            score += 10
        if all(c in string.printable for c in text):
            score += 1

        results.append((score, i, text))

results.sort(reverse=True)

for score, offset, text in results[:50]:
    print("=" * 60)
    print(f"offset: {hex(offset)} | score: {score}")
    print(repr(text))
