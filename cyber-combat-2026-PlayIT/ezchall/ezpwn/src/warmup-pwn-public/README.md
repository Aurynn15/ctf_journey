# Smoothie Shop

A TCP-based smoothie ordering service. Connect via netcat to order drinks and chat with the cashier.

## What's in this bundle

- `smoothie.c` — service source code
- `smoothie` — pre-compiled ELF binary (linux/amd64, glibc-linked, built from this Dockerfile)
- `README.md` — this file

## Mitigations

Run `checksec` on the binary to inspect:

```
Arch:       amd64-64-little
RELRO:      No RELRO
Stack:      No canary found
NX:         NX enabled
PIE:        No PIE (0x400000)
```

The binary was compiled with:
```
gcc -no-pie -Wl,-z,norelro -fno-stack-protector -D_FORTIFY_SOURCE=0
```

## Build

The bundled binary was built with the service's own Dockerfile:
```bash
docker build --platform linux/amd64 \
  -t smoothie-builder ../warmup-pwn/service
docker create --name tmp --platform linux/amd64 smoothie-builder
docker cp tmp:/app/smoothie ./smoothie
docker rm tmp
```

This produces a binary byte-identical to the one running in the service container, so addresses (e.g. `secret_recipe`, `puts@GOT`, format-string offset) match exactly.

## Interface

TCP on port 31337:
```
nc <host> 31337
```

Commands:
- `1` — order a smoothie (asks for name and ingredient)
- `2` — view the menu
- `3` — exit
