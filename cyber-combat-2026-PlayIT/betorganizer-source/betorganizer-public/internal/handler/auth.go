package handler

import (
	"crypto/md5"
	"fmt"
	"net/http"
	"strings"
	"time"

	"betorganizer/internal/middleware"
	"betorganizer/internal/model"
	"betorganizer/internal/session"
	"betorganizer/internal/store"
	"betorganizer/internal/tmpl"
)

func LoginPageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		tmpl.RenderTemplate(w, "login.html", nil)
		return
	}
	LoginHandler(w, r)
}

func LoginHandler(w http.ResponseWriter, r *http.Request) {
	ip := strings.Split(r.RemoteAddr, ":")[0]
	if middleware.CheckRateLimit(ip) {
		time.Sleep(2 * time.Second)
		tmpl.RenderTemplate(w, "login.html", map[string]any{"Error": "Login failed: invalid credentials"})
		return
	}

	r.ParseForm()
	username := strings.TrimSpace(r.FormValue("username"))
	password := strings.TrimSpace(r.FormValue("password"))

	h := md5.Sum([]byte(password))
	passwordHash := fmt.Sprintf("%x", h)

	if middleware.IsMalicious(username) || middleware.IsMalicious(passwordHash) {
		time.Sleep(500 * time.Millisecond)
		tmpl.RenderTemplate(w, "login.html", map[string]any{"Error": "Login failed: invalid credentials"})
		return
	}

	query := fmt.Sprintf(
		"SELECT id, username, password, role, balance FROM users WHERE username='%s' AND password='%s'",
		username, passwordHash,
	)

	row := store.DB.QueryRow(query)
	var u model.User
	if err := row.Scan(&u.ID, &u.Username, &u.Password, &u.Role, &u.Balance); err != nil {
		time.Sleep(500 * time.Millisecond)
		tmpl.RenderTemplate(w, "login.html", map[string]any{"Error": "Login failed: invalid credentials"})
		return
	}

	session.SetSession(w, r, u)
	http.Redirect(w, r, "/dashboard", http.StatusFound)
}

func RegisterPageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		tmpl.RenderTemplate(w, "register.html", nil)
		return
	}

	r.ParseForm()
	username := strings.TrimSpace(r.FormValue("username"))
	password := r.FormValue("password")

	if username == "" || password == "" {
		tmpl.RenderTemplate(w, "register.html", map[string]any{"Error": "Username and password required"})
		return
	}

	h := md5.Sum([]byte(password))
	hash := fmt.Sprintf("%x", h)

	_, err := store.DB.Exec("INSERT INTO users (username, password, role, balance) VALUES (?,?,?,?)",
		username, hash, "user", 50)
	if err != nil {
		tmpl.RenderTemplate(w, "register.html", map[string]any{"Error": "Username already taken"})
		return
	}

	http.Redirect(w, r, "/login", http.StatusFound)
}

func LogoutHandler(w http.ResponseWriter, r *http.Request) {
	token := session.GetSessionToken(r)
	if token != "" {
		session.DeleteSession(token)
	}
	http.SetCookie(w, &http.Cookie{Name: "session", Value: "", Path: "/", MaxAge: -1})
	http.Redirect(w, r, "/login", http.StatusFound)
}
