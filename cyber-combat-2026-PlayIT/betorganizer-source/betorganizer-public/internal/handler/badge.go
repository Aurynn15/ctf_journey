package handler

import (
	"bytes"
	"crypto/md5"
	"fmt"
	"image"
	_ "image/jpeg"
	_ "image/png"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"time"

	"betorganizer/internal/session"
	"betorganizer/internal/store"
	"betorganizer/internal/tmpl"
)

func UploadBadgeHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}
	if user.Role != "admin" && user.Role != "organizer" {
		http.Error(w, "Forbidden", 403)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", 405)
		return
	}

	if err := r.ParseMultipartForm(2 << 20); err != nil {
		http.Error(w, "File terlalu besar (maks 2MB)", 400)
		return
	}

	file, header, err := r.FormFile("badge")
	if err != nil {
		http.Error(w, "Tidak ada file yang diunggah", 400)
		return
	}
	defer file.Close()

	ext := strings.ToLower(filepath.Ext(header.Filename))
	allowed := map[string]bool{".png": true, ".jpg": true, ".jpeg": true}
	if !allowed[ext] {
		http.Error(w, "Format tidak didukung. Gunakan PNG, JPG, atau JPEG.", 400)
		return
	}

	content, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, "Gagal membaca file", 500)
		return
	}

	if _, _, err := image.Decode(bytes.NewReader(content)); err != nil {
		http.Error(w, "File bukan gambar yang valid", 400)
		return
	}

	h := md5.Sum([]byte(fmt.Sprintf("%d-%d", user.ID, time.Now().UnixNano())))
	filename := fmt.Sprintf("z_badge_%d_%x%s", user.ID, h[:4], ext)
	dest := filepath.Join("templates", filename)

	if err := os.WriteFile(dest, content, 0644); err != nil {
		http.Error(w, "Gagal menyimpan file", 500)
		return
	}

	if err := tmpl.ReloadTemplates(); err != nil {
		os.Remove(dest)
		http.Error(w, "Gagal memuat ulang konfigurasi", 500)
		return
	}

	store.DB.Exec("UPDATE users SET badge = ? WHERE id = ?", filename, user.ID)

	w.Header().Set("HX-Trigger", "badgeUpdate")
	w.Write([]byte("Badge berhasil diunggah."))
}

func PreviewBadgeHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}
	if user.Role != "admin" && user.Role != "organizer" {
		http.Error(w, "Forbidden", 403)
		return
	}

	var badge string
	store.DB.QueryRow("SELECT COALESCE(badge, '') FROM users WHERE id = ?", user.ID).Scan(&badge)

	tmpl.RenderTemplate(w, "preview.html", map[string]any{
		"User":  user,
		"Badge": badge,
	})
}
