package session

import (
	"crypto/md5"
	"fmt"
	"net/http"
	"sync"
	"time"

	"betorganizer/internal/model"
)

var (
	sessions   = map[string]model.User{}
	sessionsMu sync.RWMutex
)

func SetSession(w http.ResponseWriter, r *http.Request, u model.User) {
	raw := fmt.Sprintf("%d-%d", u.ID, time.Now().UnixNano())
	h := md5.Sum([]byte(raw))
	token := fmt.Sprintf("%x", h)
	sessionsMu.Lock()
	sessions[token] = u
	sessionsMu.Unlock()
	http.SetCookie(w, &http.Cookie{
		Name:  "session",
		Value: token,
		Path:  "/",
	})
}

func GetSessionUser(r *http.Request) *model.User {
	c, err := r.Cookie("session")
	if err != nil {
		return nil
	}
	sessionsMu.RLock()
	u, ok := sessions[c.Value]
	sessionsMu.RUnlock()
	if !ok {
		return nil
	}
	return &u
}

func RefreshSession(token string, u model.User) {
	sessionsMu.Lock()
	sessions[token] = u
	sessionsMu.Unlock()
}

func GetSessionToken(r *http.Request) string {
	c, err := r.Cookie("session")
	if err != nil {
		return ""
	}
	return c.Value
}

func DeleteSession(token string) {
	sessionsMu.Lock()
	delete(sessions, token)
	sessionsMu.Unlock()
}
