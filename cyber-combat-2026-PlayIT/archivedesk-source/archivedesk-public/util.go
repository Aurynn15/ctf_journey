package main

import (
	"crypto/rand"
	"crypto/sha1"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
)

func writeJSON(w http.ResponseWriter, status int, payload any) {
	body, _ := json.MarshalIndent(payload, "", "  ")
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	w.Write(body)
}

func splitPath(path string) []string {
	raw := strings.Split(strings.Trim(path, "/"), "/")
	out := make([]string, 0, len(raw))
	for _, item := range raw {
		if item != "" {
			out = append(out, item)
		}
	}
	return out
}

func hashPassword(s string) string {
	sum := sha256.Sum256([]byte("archivedesk:" + s))
	return hex.EncodeToString(sum[:])
}

func sha1Hex(s string) string {
	sum := sha1.Sum([]byte(s))
	return hex.EncodeToString(sum[:])
}

func weakResetToken(userID uint, rowID uint, minute int64, nonce string) string {
	return sha1Hex(fmt.Sprintf("%d:%d:%d:%s", userID, rowID, minute, nonce))
}

func b64url(v []byte) string {
	return base64.RawURLEncoding.EncodeToString(v)
}

func randomHex(n int) string {
	buf := make([]byte, n)
	if _, err := rand.Read(buf); err != nil {
		panic(err)
	}
	return hex.EncodeToString(buf)
}

func loadOrCreateNonce() string {
	path := filepath.Join(stateDir, "build.nonce")
	if body, err := os.ReadFile(path); err == nil && strings.TrimSpace(string(body)) != "" {
		return strings.TrimSpace(string(body))
	}
	nonce := randomHex(8)
	_ = os.WriteFile(path, []byte(nonce), 0644)
	return nonce
}

func readCheckerSecret() string {
	return strings.TrimSpace(os.Getenv("AD_CHECKER_TOKEN"))
}

func clearPlatformSecrets() {
	for _, key := range []string{"AD_PLATFORM_ROOT_PASSWORD", "AD_ROOT_PASSWORD", "AD_PLATFORM_UNLOCK_PROOF", "AD_CHECKER_TOKEN"} {
		os.Unsetenv(key)
	}
}

func truncate(s string, limit int) string {
	s = strings.TrimSpace(s)
	if len(s) <= limit {
		return s
	}
	return s[:limit]
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
