#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cwchar>
#include <sstream>
#include <string>
#include <unistd.h>

#include "sealbroker.hpp"

namespace {

std::array<Capsule, kMaxCapsules> capsules{};
std::array<Lease, kMaxLeases> leases{};
uint32_t next_capsule_id = 1000;
uint32_t next_lease_id = 5000;
volatile void *heap_warmup_hold = nullptr;

bool send_all(const std::string &data) {
  return std::fwrite(data.data(), 1, data.size(), stdout) == data.size() && std::fflush(stdout) == 0;
}

bool recv_line(char *line, size_t cap) {
  size_t used = 0;
  char c = 0;
  while (used + 1 < cap) {
    ssize_t n = read(STDIN_FILENO, &c, 1);
    if (n <= 0) {
      return false;
    }
    if (c == '\n') {
      line[used] = '\0';
      return true;
    }
    if (c != '\r') {
      line[used++] = c;
    }
  }
  return false;
}

Capsule *find_capsule(uint32_t id) {
  for (auto &cap : capsules) {
    if (cap.used && cap.id == id) {
      return &cap;
    }
  }
  return nullptr;
}

Lease *find_lease(uint32_t id) {
  for (auto &lease : leases) {
    if (lease.used && lease.id == id) {
      return &lease;
    }
  }
  return nullptr;
}

std::string cmd_auth(Tokens &args, bool &authed) {
  char *user = args.next();
  char *pass = args.next();
  if (!user || !pass || !args.empty() || std::strlen(user) < 3 || std::strlen(pass) < 3) {
    return "ERR auth\n";
  }
  authed = true;
  return "OK auth\n";
}

std::string cmd_new(Tokens &args) {
  char *name = args.next();
  size_t size = 0;
  if (!args.next_size(size) || !args.empty() || !name || *name == '\0' || std::strlen(name) > 64 || size == 0 || size > 0x1000) {
    return "ERR new\n";
  }
  for (auto &cap : capsules) {
    if (!cap.used) {
      cap.used = true;
      cap.sealed = false;
      cap.id = next_capsule_id++;
      cap.capacity = size;
      cap.length = 0;
      cap.body = new char[size];
      if (size != 0x88) {
        std::memset(cap.body, 0, size);
      }
      cap.name = name;
      cap.nonce.clear();
      return "OK new " + std::to_string(cap.id) + "\n";
    }
  }
  return "ERR full\n";
}

std::string cmd_write(Tokens &args) {
  uint32_t id = 0;
  size_t offset = 0;
  if (!args.next_u32(id) || !args.next_size(offset)) {
    return "ERR write\n";
  }
  char *hex = args.next();
  Capsule *cap = find_capsule(id);
  size_t decoded_len = 0;
  if (!cap || cap->sealed || !args.empty() || !hex_decoded_length(hex, decoded_len) || offset > cap->capacity || decoded_len > cap->capacity - offset) {
    return "ERR write\n";
  }
  std::string data = hex_decode(hex);
  if (data.empty()) {
    return "ERR write\n";
  }
  std::memcpy(cap->body + offset, data.data(), data.size());
  if (offset + data.size() > cap->length) {
    cap->length = offset + data.size();
  }
  return "OK write\n";
}

std::string cmd_seal(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id)) {
    return "ERR seal\n";
  }
  char *nonce = args.next();
  Capsule *cap = find_capsule(id);
  if (!cap || !nonce || !args.empty() || *nonce == '\0' || std::strlen(nonce) > 64) {
    return "ERR seal\n";
  }
  cap->sealed = true;
  cap->nonce = nonce;
  return "OK seal\n";
}

std::string cmd_lease(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id)) {
    return "ERR lease\n";
  }
  char *name = args.next();
  size_t size = 0;
  if (!args.next_size(size)) {
    return "ERR lease\n";
  }
  Capsule *cap = find_capsule(id);
  if (!cap || !name || !args.empty() || *name == '\0' || std::strlen(name) > 64 || size == 0 || size > 0x400) {
    return "ERR lease\n";
  }
  for (auto &lease : leases) {
    if (!lease.used) {
      lease.used = true;
      lease.borrowed = false;
      lease.id = next_lease_id++;
      lease.capsule_id = id;
      lease.length = size;
      lease.memo = new char[size];
      std::memset(lease.memo, 0x41, size);
      lease.name = name;
      return "OK lease " + std::to_string(lease.id) + "\n";
    }
  }
  return "ERR leases\n";
}

std::string cmd_slice(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id)) {
    return "ERR slice\n";
  }
  char *name = args.next();
  long long offset = 0;
  size_t length = 0;
  if (!args.next_i64(offset) || !args.next_size(length)) {
    return "ERR slice\n";
  }
  Capsule *cap = find_capsule(id);
  if (!cap || !name || !args.empty() || *name == '\0' || std::strlen(name) > 64 || length == 0 || length > 0x400 || offset < -0x10) {
    return "ERR slice\n";
  }
  long long end = offset + static_cast<long long>(length);
  if (end < 0 || end > static_cast<long long>(cap->capacity)) {
    return "ERR slice\n";
  }
  for (auto &lease : leases) {
    if (!lease.used) {
      lease.used = true;
      lease.borrowed = true;
      lease.id = next_lease_id++;
      lease.capsule_id = id;
      lease.length = length;
      lease.memo = cap->body + offset;
      lease.name = name;
      return "OK slice " + std::to_string(lease.id) + "\n";
    }
  }
  return "ERR leases\n";
}

std::string cmd_note(Tokens &args) {
  uint32_t id = 0;
  size_t offset = 0;
  if (!args.next_u32(id) || !args.next_size(offset)) {
    return "ERR note\n";
  }
  char *hex = args.next();
  Lease *lease = find_lease(id);
  size_t decoded_len = 0;
  if (!lease || !args.empty() || !hex_decoded_length(hex, decoded_len) || offset > lease->length || decoded_len > lease->length - offset) {
    return "ERR note\n";
  }
  std::string data = hex_decode(hex);
  if (data.empty()) {
    return "ERR note\n";
  }
  std::memcpy(lease->memo + offset, data.data(), data.size());
  return "OK note\n";
}

std::string cmd_unlease(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id) || !args.empty()) {
    return "ERR unlease\n";
  }
  for (auto &lease : leases) {
    if (lease.used && lease.id == id) {
      if (!lease.borrowed) {
        delete[] lease.memo;
      }
      lease = Lease{};
      return "OK unlease\n";
    }
  }
  return "ERR unlease\n";
}

std::string cmd_audit(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id) || !args.empty()) {
    return "ERR audit\n";
  }
  Capsule *cap = find_capsule(id);
  if (!cap) {
    return "ERR audit\n";
  }
  std::ostringstream out;
  out << "OK audit id=" << cap->id
      << " name=" << cap->name
      << " cap=" << cap->capacity
      << " len=" << cap->length
      << " sealed=" << (cap->sealed ? 1 : 0)
      << "\n";
  return out.str();
}

std::string cmd_export(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id) || !args.empty()) {
    return "ERR export\n";
  }
  Capsule *cap = find_capsule(id);
  if (!cap || !cap->sealed) {
    return "ERR export\n";
  }
  std::string data(cap->body, cap->body + cap->length);
  std::ostringstream out;
  out << "OK export " << cap->nonce << " " << hex_encode(data) << "\n";
  return out.str();
}

std::string cmd_patch(Tokens &args) {
  uint32_t id = 0;
  size_t offset = 0;
  uint32_t serialized_len = 0;
  if (!args.next_u32(id) || !args.next_size(offset) || !args.next_u32(serialized_len)) {
    return "ERR patch\n";
  }
  char *delta_hex = args.next();
  Capsule *cap = find_capsule(id);
  size_t decoded_len = 0;
  if (!cap || !args.empty() || !hex_decoded_length(delta_hex, decoded_len) || decoded_len > 0x20 || offset > 0x20000 || serialized_len > 0x7000) {
    return "ERR patch\n";
  }
  std::string delta = hex_decode(delta_hex);
  if (delta.empty()) {
    return "ERR patch\n";
  }
  if (serialized_len == 0 && offset > cap->capacity + 0x20) {
    return "ERR patch\n";
  }
  if (serialized_len != 0 && decoded_len > serialized_len) {
    return "ERR patch\n";
  }
  if (offset + static_cast<size_t>(serialized_len) > cap->capacity) {
    return "ERR patch\n";
  }
  std::memcpy(cap->body + offset, delta.data(), delta.size());
  if (offset + delta.size() > cap->length) {
    cap->length = offset + delta.size();
  }
  return "OK patch\n";
}

std::string cmd_drop(Tokens &args) {
  uint32_t id = 0;
  if (!args.next_u32(id) || !args.empty()) {
    return "ERR drop\n";
  }
  for (auto &cap : capsules) {
    if (cap.used && cap.id == id) {
      delete[] cap.body;
      cap = Capsule{};
      return "OK drop\n";
    }
  }
  return "ERR drop\n";
}

void handle_client() {
  bool authed = false;
  send_all("SealBroker/0.1\n");
  char line[8192];
  while (recv_line(line, sizeof(line))) {
    Tokens stream(line);
    char *cmd = stream.next();
    if (!cmd) {
      continue;
    }
    std::string reply;
    if (std::strcmp(cmd, "PING") == 0) {
      reply = stream.empty() ? "OK pong\n" : "ERR command\n";
    } else if (std::strcmp(cmd, "AUTH") == 0) {
      reply = cmd_auth(stream, authed);
    } else if (std::strcmp(cmd, "QUIT") == 0) {
      if (!stream.empty()) {
        reply = "ERR command\n";
      } else {
        send_all("OK bye\n");
        std::fputwc(L'\n', stderr);
        std::fflush(stderr);
        _exit(0);
      }
    } else if (!authed) {
      reply = "ERR unauth\n";
    } else if (std::strcmp(cmd, "NEW") == 0) {
      reply = cmd_new(stream);
    } else if (std::strcmp(cmd, "WRITE") == 0) {
      reply = cmd_write(stream);
    } else if (std::strcmp(cmd, "SEAL") == 0) {
      reply = cmd_seal(stream);
    } else if (std::strcmp(cmd, "LEASE") == 0) {
      reply = cmd_lease(stream);
    } else if (std::strcmp(cmd, "SLICE") == 0) {
      reply = cmd_slice(stream);
    } else if (std::strcmp(cmd, "NOTE") == 0) {
      reply = cmd_note(stream);
    } else if (std::strcmp(cmd, "UNLEASE") == 0) {
      reply = cmd_unlease(stream);
    } else if (std::strcmp(cmd, "PATCH") == 0) {
      reply = cmd_patch(stream);
    } else if (std::strcmp(cmd, "AUDIT") == 0) {
      reply = cmd_audit(stream);
    } else if (std::strcmp(cmd, "EXPORT") == 0) {
      reply = cmd_export(stream);
    } else if (std::strcmp(cmd, "DROP") == 0) {
      reply = cmd_drop(stream);
    } else {
      reply = "ERR command\n";
    }
    if (!reply.empty() && !send_all(reply)) {
      break;
    }
  }
  _exit(0);
}

}

int main() {
  std::setvbuf(stdout, nullptr, _IONBF, 0);
  void *heap_warmup = std::malloc(0x280);
  if (heap_warmup) {
    std::memset(heap_warmup, 0, 0x280);
    heap_warmup_hold = heap_warmup;
  }
  handle_client();
  return 0;
}
