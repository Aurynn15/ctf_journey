package main

import (
	"crypto"
	"crypto/hmac"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

func (a *App) setSession(w http.ResponseWriter, user User) {
	token, _ := a.signJWT(Claims{
		Sub:  user.ID,
		User: user.Username,
		Role: user.Role,
		Exp:  time.Now().Add(6 * time.Hour).Unix(),
	})
	http.SetCookie(w, &http.Cookie{
		Name:     "ad_session",
		Value:    token,
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})
}

func (a *App) currentUser(r *http.Request) *User {
	cookie, err := r.Cookie("ad_session")
	if err != nil {
		return nil
	}
	claims, err := a.verifyJWT(cookie.Value)
	if err != nil || claims.Exp < time.Now().Unix() {
		return nil
	}
	var user User
	if err := a.db.First(&user, claims.Sub).Error; err != nil {
		return nil
	}
	user.Role = claims.Role
	return &user
}

func (a *App) requireUser(w http.ResponseWriter, r *http.Request) *User {
	user := a.currentUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return nil
	}
	return user
}

func (a *App) requireAdmin(w http.ResponseWriter, r *http.Request) *User {
	user := a.requireUser(w, r)
	if user == nil {
		return nil
	}
	if user.Role != "admin" {
		http.Error(w, "admin review access required", http.StatusForbidden)
		return nil
	}
	return user
}

func (a *App) signJWT(claims Claims) (string, error) {
	header := map[string]string{"typ": "JWT", "alg": "RS256", "kid": keyID}
	hb, _ := json.Marshal(header)
	cb, _ := json.Marshal(claims)
	msg := b64url(hb) + "." + b64url(cb)
	digest := sha256.Sum256([]byte(msg))
	sig, err := rsa.SignPKCS1v15(rand.Reader, a.rsaKey, crypto.SHA256, digest[:])
	if err != nil {
		return "", err
	}
	return msg + "." + b64url(sig), nil
}

func (a *App) verifyJWT(token string) (*Claims, error) {
	parts := splitJWT(token)
	if len(parts) != 3 {
		return nil, errors.New("bad jwt")
	}
	header, err := decodeJWTHeader(parts[0])
	if err != nil {
		return nil, err
	}
	if header["kid"] != keyID {
		return nil, errors.New("bad kid")
	}
	msg := parts[0] + "." + parts[1]
	sig, err := base64.RawURLEncoding.DecodeString(parts[2])
	if err != nil {
		return nil, err
	}
	if err := a.verifyJWTSignature(header["alg"], msg, sig); err != nil {
		return nil, err
	}
	bodyRaw, err := base64.RawURLEncoding.DecodeString(parts[1])
	if err != nil {
		return nil, err
	}
	var claims Claims
	if err := json.Unmarshal(bodyRaw, &claims); err != nil {
		return nil, err
	}
	return &claims, nil
}

func (a *App) verifyJWTSignature(alg string, msg string, sig []byte) error {
	switch alg {
	case "RS256":
		digest := sha256.Sum256([]byte(msg))
		return rsa.VerifyPKCS1v15(&a.rsaKey.PublicKey, crypto.SHA256, digest[:], sig)
	case "HS256":

		if a.hmacSecret != "" && hmacMatches([]byte(a.hmacSecret), msg, sig) {
			return nil
		}

		if hmacMatches(a.publicPEM, msg, sig) {
			return nil
		}
		return errors.New("bad hmac")
	default:
		return errors.New("bad alg")
	}
}

func hmacMatches(key []byte, msg string, sig []byte) bool {
	mac := hmac.New(sha256.New, key)
	mac.Write([]byte(msg))
	return hmac.Equal(sig, mac.Sum(nil))
}

func decodeJWTHeader(part string) (map[string]string, error) {
	raw, err := base64.RawURLEncoding.DecodeString(part)
	if err != nil {
		return nil, err
	}
	var header map[string]string
	return header, json.Unmarshal(raw, &header)
}

func splitJWT(token string) []string {
	var parts []string
	start := 0
	for i := 0; i <= len(token); i++ {
		if i == len(token) || token[i] == '.' {
			parts = append(parts, token[start:i])
			start = i + 1
		}
	}
	return parts
}

func loadOrCreateKey() *rsa.PrivateKey {
	path := filepath.Join(stateDir, "jwt.key")
	if key := readPrivateKey(path); key != nil {
		return key
	}
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		panic(err)
	}
	der := x509.MarshalPKCS1PrivateKey(key)
	_ = os.WriteFile(path, pem.EncodeToMemory(&pem.Block{Type: "RSA PRIVATE KEY", Bytes: der}), 0600)
	return key
}

func readPrivateKey(path string) *rsa.PrivateKey {
	body, err := os.ReadFile(path)
	if err != nil {
		return nil
	}
	block, _ := pem.Decode(body)
	if block == nil {
		return nil
	}
	key, err := x509.ParsePKCS1PrivateKey(block.Bytes)
	if err != nil {
		return nil
	}
	return key
}

func publicKeyPEM(key *rsa.PublicKey) []byte {
	der, _ := x509.MarshalPKIXPublicKey(key)
	return pem.EncodeToMemory(&pem.Block{Type: "PUBLIC KEY", Bytes: der})
}

func loadOrCreateHMACSecret() string {
	path := filepath.Join(stateDir, "hmac.key")
	if body, err := os.ReadFile(path); err == nil && len(body) >= 32 {
		return string(body)
	}
	secret := randomHex(32)
	_ = os.WriteFile(path, []byte(secret), 0600)
	return secret
}
