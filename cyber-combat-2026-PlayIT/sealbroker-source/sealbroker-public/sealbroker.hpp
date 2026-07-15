#pragma once

#include <array>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <string>

constexpr size_t kMaxCapsules = 32;
constexpr size_t kMaxLeases = 64;

struct Capsule {
  bool used;
  bool sealed;
  uint32_t id;
  size_t capacity;
  size_t length;
  char *body;
  std::string name;
  std::string nonce;
};

struct Lease {
  bool used;
  bool borrowed;
  uint32_t id;
  uint32_t capsule_id;
  size_t length;
  char *memo;
  std::string name;
};

struct Tokens {
  char *cursor;

  explicit Tokens(char *line) : cursor(line) {}

  char *next() {
    while (*cursor == ' ' || *cursor == '\t') {
      cursor++;
    }
    if (*cursor == '\0') {
      return nullptr;
    }
    char *out = cursor;
    while (*cursor != '\0' && *cursor != ' ' && *cursor != '\t') {
      cursor++;
    }
    if (*cursor != '\0') {
      *cursor++ = '\0';
    }
    return out;
  }

  bool next_u32(uint32_t &out) {
    char *raw = next();
    if (!raw || raw[0] == '-' || raw[0] == '+') {
      return false;
    }
    errno = 0;
    char *end = nullptr;
    unsigned long value = std::strtoul(raw, &end, 10);
    if (errno != 0 || !end || *end != '\0' || value > UINT32_MAX) {
      return false;
    }
    out = static_cast<uint32_t>(value);
    return true;
  }

  bool next_size(size_t &out) {
    char *raw = next();
    if (!raw || raw[0] == '-' || raw[0] == '+') {
      return false;
    }
    errno = 0;
    char *end = nullptr;
    unsigned long long value = std::strtoull(raw, &end, 10);
    if (errno != 0 || !end || *end != '\0') {
      return false;
    }
    out = static_cast<size_t>(value);
    return true;
  }

  bool next_i64(long long &out) {
    char *raw = next();
    if (!raw) {
      return false;
    }
    errno = 0;
    char *end = nullptr;
    long long value = std::strtoll(raw, &end, 10);
    if (errno != 0 || !end || *end != '\0') {
      return false;
    }
    out = value;
    return true;
  }

  bool empty() {
    while (*cursor == ' ' || *cursor == '\t') {
      cursor++;
    }
    return *cursor == '\0';
  }
};

inline std::string hex_encode(const std::string &in) {
  static const char *alphabet = "0123456789abcdef";
  std::string out;
  out.reserve(in.size() * 2);
  for (unsigned char c : in) {
    out.push_back(alphabet[c >> 4]);
    out.push_back(alphabet[c & 0xf]);
  }
  return out;
}

inline int hex_value(char c) {
  if (c >= '0' && c <= '9') {
    return c - '0';
  }
  if (c >= 'a' && c <= 'f') {
    return c - 'a' + 10;
  }
  if (c >= 'A' && c <= 'F') {
    return c - 'A' + 10;
  }
  return -1;
}

inline std::string hex_decode(const char *hex) {
  std::string out;
  if (!hex) {
    return out;
  }
  size_t hex_len = std::strlen(hex);
  if (hex_len % 2 != 0) {
    return out;
  }
  out.reserve(hex_len / 2);
  for (size_t i = 0; i < hex_len; i += 2) {
    int hi = hex_value(hex[i]);
    int lo = hex_value(hex[i + 1]);
    if (hi < 0 || lo < 0) {
      return "";
    }
    out.push_back(static_cast<char>((hi << 4) | lo));
  }
  return out;
}

inline bool hex_decoded_length(const char *hex, size_t &decoded_len) {
  if (!hex) {
    return false;
  }
  size_t hex_len = std::strlen(hex);
  if (hex_len == 0 || hex_len % 2 != 0) {
    return false;
  }
  decoded_len = hex_len / 2;
  return true;
}
