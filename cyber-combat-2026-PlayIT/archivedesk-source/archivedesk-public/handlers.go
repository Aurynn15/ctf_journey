package main

import (
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"gorm.io/gorm/clause"
)

func (a *App) home(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.NotFound(w, r)
		return
	}
	if a.currentUser(r) != nil {
		http.Redirect(w, r, "/cases", http.StatusFound)
		return
	}
	a.render(w, "login", map[string]any{"Title": "ArchiveDesk", "Nonce": a.buildNonce})
}

func (a *App) health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "build_nonce": a.buildNonce})
}

func (a *App) jwks(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"keys": []map[string]any{{
		"kty": "RSA", "kid": keyID, "alg": "RS256", "use": "sig", "pem": string(a.publicPEM),
	}}})
}

func (a *App) login(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		a.render(w, "login", map[string]any{"Title": "Sign in", "Nonce": a.buildNonce})
		return
	}
	username := strings.TrimSpace(r.FormValue("username"))
	password := r.FormValue("password")
	var user User
	if err := a.db.Where("username = ?", username).First(&user).Error; err != nil || user.PasswordHash != hashPassword(password) {
		a.render(w, "login", map[string]any{"Title": "Sign in", "Error": "Invalid credentials", "Nonce": a.buildNonce})
		return
	}
	a.setSession(w, user)
	http.Redirect(w, r, "/cases", http.StatusFound)
}

func (a *App) register(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		a.render(w, "register", map[string]any{"Title": "Create account"})
		return
	}
	username := strings.TrimSpace(r.FormValue("username"))
	password := r.FormValue("password")
	if len(username) < 3 || len(password) < 6 {
		a.render(w, "register", map[string]any{"Title": "Create account", "Error": "Use at least 3 username characters and 6 password characters"})
		return
	}
	user := User{Username: username, PasswordHash: hashPassword(password), Role: "user"}
	if err := a.db.Create(&user).Error; err != nil {
		a.render(w, "register", map[string]any{"Title": "Create account", "Error": "Username already exists"})
		return
	}
	a.setSession(w, user)
	http.Redirect(w, r, "/cases", http.StatusFound)
}

func (a *App) reset(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		a.render(w, "reset", map[string]any{"Title": "Reset password"})
		return
	}
	userID, _ := strconv.ParseUint(r.FormValue("user_id"), 10, 64)
	token := r.FormValue("token")
	password := r.FormValue("password")
	var row ResetRow
	if err := a.db.Where("user_id = ? AND used = ?", userID, false).First(&row).Error; err != nil || row.TokenHash != sha1Hex(token) || len(password) < 6 {
		a.render(w, "reset", map[string]any{"Title": "Reset password", "Error": "Reset request rejected"})
		return
	}
	a.db.Model(&User{}).Where("id = ?", userID).Update("password_hash", hashPassword(password))
	a.db.Model(&row).Update("used", true)
	a.render(w, "reset", map[string]any{"Title": "Reset password", "Notice": "Password updated"})
}

func (a *App) logout(w http.ResponseWriter, r *http.Request) {
	http.SetCookie(w, &http.Cookie{Name: "ad_session", Value: "", Path: "/", MaxAge: -1, HttpOnly: true, SameSite: http.SameSiteLaxMode})
	http.Redirect(w, r, "/", http.StatusFound)
}

func (a *App) cases(w http.ResponseWriter, r *http.Request) {
	user := a.requireUser(w, r)
	if user == nil {
		return
	}
	if r.Method == http.MethodPost {
		c := Case{Title: fallbackTitle(r.FormValue("title")), OwnerID: user.ID, Status: "draft", Marker: randomHex(8)}
		a.db.Create(&c)
		http.Redirect(w, r, fmt.Sprintf("/cases/%d", c.ID), http.StatusFound)
		return
	}
	var cases []Case
	query := a.db.Order("id desc").Preload("Evidence").Preload("Reports")
	if user.Role != "admin" {
		query = query.Where("owner_id = ?", user.ID)
	}
	query.Find(&cases)
	a.render(w, "cases", map[string]any{"Title": "Cases", "User": user, "Cases": cases})
}

func (a *App) caseRoute(w http.ResponseWriter, r *http.Request) {
	user := a.requireUser(w, r)
	if user == nil {
		return
	}
	parts := splitPath(r.URL.Path)
	if len(parts) < 2 {
		http.NotFound(w, r)
		return
	}
	caseID, _ := strconv.Atoi(parts[1])
	if len(parts) == 3 && parts[2] == "upload" && r.Method == http.MethodPost {
		a.upload(w, r, user, uint(caseID))
		return
	}
	if len(parts) == 3 && parts[2] == "reindex" && r.Method == http.MethodPost {
		a.reindex(w, r, user, uint(caseID))
		return
	}
	var c Case
	if !a.loadCaseFor(user, uint(caseID), &c) {
		http.NotFound(w, r)
		return
	}
	a.render(w, "case", map[string]any{"Title": c.Title, "User": user, "Case": c})
}

func (a *App) upload(w http.ResponseWriter, r *http.Request, user *User, caseID uint) {
	var c Case
	if !a.loadCaseFor(user, caseID, &c) {
		http.NotFound(w, r)
		return
	}
	if err := r.ParseMultipartForm(8 << 20); err != nil {
		http.Error(w, "upload rejected", http.StatusBadRequest)
		return
	}
	file, header, err := r.FormFile("archive")
	if err != nil {
		http.Error(w, "archive required", http.StatusBadRequest)
		return
	}
	defer file.Close()
	if err := a.processArchive(c.ID, file, header); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	a.db.Model(&c).Update("status", "uploaded")
	http.Redirect(w, r, fmt.Sprintf("/cases/%d", c.ID), http.StatusFound)
}

func (a *App) reindex(w http.ResponseWriter, r *http.Request, user *User, caseID uint) {
	var c Case
	if !a.loadCaseFor(user, caseID, &c) {
		http.NotFound(w, r)
		return
	}
	var evidence []Evidence
	a.db.Where("case_id = ?", c.ID).Find(&evidence)
	for _, ev := range evidence {
		if result, err := runAnalyzer(ev.StoragePath); err == nil {
			a.db.Model(&ev).Update("summary", result.Summary)
		}
	}
	a.db.Create(&ReviewReport{CaseID: c.ID, Kind: "analysis", ShareToken: randomHex(16), Diagnostics: "Evidence analyzer completed"})
	http.Redirect(w, r, fmt.Sprintf("/cases/%d", c.ID), http.StatusFound)
}

func (a *App) adminReviews(w http.ResponseWriter, r *http.Request) {
	user := a.requireAdmin(w, r)
	if user == nil {
		return
	}
	var cases []Case
	a.db.Order("id desc").Preload("Owner").Preload("Reports").Find(&cases)
	a.render(w, "admin", map[string]any{"Title": "Review queue", "User": user, "Cases": cases})
}

func (a *App) adminReviewRoute(w http.ResponseWriter, r *http.Request) {
	user := a.requireAdmin(w, r)
	if user == nil {
		return
	}
	parts := splitPath(r.URL.Path)
	if len(parts) != 4 || parts[3] != "parse" || r.Method != http.MethodPost {
		http.NotFound(w, r)
		return
	}
	caseID, _ := strconv.Atoi(parts[2])
	report, err := a.parseManifest(uint(caseID))
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	http.Redirect(w, r, "/reports/"+report.ShareToken, http.StatusFound)
}

func (a *App) report(w http.ResponseWriter, r *http.Request) {
	user := a.requireUser(w, r)
	if user == nil {
		return
	}
	token := strings.TrimPrefix(r.URL.Path, "/reports/")
	var report ReviewReport
	if err := a.db.Where("share_token = ?", token).First(&report).Error; err != nil {
		http.NotFound(w, r)
		return
	}
	var c Case
	if user.Role != "admin" && !a.loadCaseFor(user, report.CaseID, &c) {
		http.NotFound(w, r)
		return
	}
	a.render(w, "report", map[string]any{"Title": "Report", "User": user, "Report": report})
}

func (a *App) apiCaseSummary(w http.ResponseWriter, r *http.Request) {
	user := a.requireUser(w, r)
	if user == nil {
		return
	}
	parts := splitPath(r.URL.Path)
	if len(parts) != 4 || parts[3] != "summary" {
		http.NotFound(w, r)
		return
	}
	caseID, _ := strconv.Atoi(parts[2])
	var c Case
	if !a.loadCaseFor(user, uint(caseID), &c) {
		http.NotFound(w, r)
		return
	}
	var leaked Case
	a.db.Preload(clause.Associations).Preload("Owner.ResetRows").First(&leaked, c.ID)
	writeJSON(w, http.StatusOK, leaked)
}

func (a *App) loadCaseFor(user *User, id uint, c *Case) bool {
	query := a.db.Preload("Owner").Preload("Evidence").Preload("Reports")
	if user.Role != "admin" {
		query = query.Where("owner_id = ?", user.ID)
	}
	return query.First(c, id).Error == nil
}

func fallbackTitle(title string) string {
	if title = strings.TrimSpace(title); title != "" {
		return title
	}
	return "Untitled evidence case"
}

func (a *App) ensureAdminResetSeed() error {
	var count int64
	a.db.Model(&User{}).Where("role = ?", "admin").Count(&count)
	if count != 0 {
		return nil
	}
	admin := User{Username: "admin", PasswordHash: hashPassword(randomHex(12)), Role: "admin"}
	if err := a.db.Create(&admin).Error; err != nil {
		return err
	}
	minute := time.Now().Unix() / 60
	token := weakResetToken(admin.ID, 1, minute, a.buildNonce)
	reset := ResetRow{UserID: admin.ID, TokenHash: sha1Hex(token), HashPrefix: sha1Hex(token)[:12], CreatedMin: minute}
	return a.db.Create(&reset).Error
}

func (a *App) parseManifest(caseID uint) (*ReviewReport, error) {
	manifest, err := a.findManifest(caseID)
	if err != nil {
		return nil, err
	}
	if err := archiveFirewall(manifest); err != nil {
		return nil, err
	}
	out, err := runXMLParser(manifest)
	if err != nil {
		return nil, err
	}
	report := ReviewReport{CaseID: caseID, Kind: "xml-review", ShareToken: randomHex(16), Diagnostics: truncate(out, 4096)}
	if err := a.db.Create(&report).Error; err != nil {
		return nil, err
	}
	return &report, nil
}

func (a *App) findManifest(caseID uint) (string, error) {
	var evidence []Evidence
	a.db.Where("case_id = ?", caseID).Find(&evidence)
	for _, ev := range evidence {
		candidate := filepath.Join(filepath.Dir(ev.StoragePath), "manifest.xml")
		if _, err := os.Stat(candidate); err == nil {
			return candidate, nil
		}
	}
	return "", fmt.Errorf("manifest not found")
}
