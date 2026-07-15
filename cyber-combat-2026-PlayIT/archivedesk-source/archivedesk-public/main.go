package main

import (
	"crypto/rsa"
	"html/template"
	"log"
	"net/http"
	"os"
	"path/filepath"

	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

const (
	stateDir = "/opt/ad/state"
	dbPath   = "/opt/ad/state/archivedesk.db"
	flagPath = "/flag.txt"
	keyID    = "archivedesk-prod-2026"
)

type App struct {
	db            *gorm.DB
	rsaKey        *rsa.PrivateKey
	publicPEM     []byte
	hmacSecret    string
	buildNonce    string
	checkerSecret string
	templates     *template.Template
}

func main() {
	if err := os.MkdirAll(stateDir, 0755); err != nil {
		log.Fatal(err)
	}

	db, err := gorm.Open(sqlite.Open(dbPath), &gorm.Config{})
	if err != nil {
		log.Fatal(err)
	}

	app := &App{
		db:            db,
		buildNonce:    loadOrCreateNonce(),
		checkerSecret: readCheckerSecret(),
		templates:     parseTemplates(),
	}
	app.rsaKey = loadOrCreateKey()
	app.publicPEM = publicKeyPEM(&app.rsaKey.PublicKey)
	app.hmacSecret = loadOrCreateHMACSecret()
	clearPlatformSecrets()

	if err := app.boot(); err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()
	app.routes(mux)

	addr := ":8130"
	addr = ":" + servicePort()
	log.Fatal(http.ListenAndServe(addr, mux))
}

func servicePort() string {
	if port := os.Getenv("PORT"); port != "" {
		return port
	}
	if port := os.Getenv("AD_PLATFORM_SERVICE_PORT"); port != "" {
		return port
	}
	return "8130"
}

func (a *App) boot() error {
	if err := a.db.AutoMigrate(&User{}, &ResetRow{}, &Case{}, &Evidence{}, &ReviewReport{}); err != nil {
		return err
	}
	if err := a.ensureAdminResetSeed(); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Join(stateDir, "uploads"), 0755); err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Join(stateDir, "analyzers"), 0755); err != nil {
		return err
	}
	return restoreDefaultAnalyzer()
}

func (a *App) routes(mux *http.ServeMux) {
	mux.HandleFunc("/", a.home)
	mux.HandleFunc("/healthz", a.health)
	mux.HandleFunc("/jwks", a.jwks)
	mux.HandleFunc("/login", a.login)
	mux.HandleFunc("/register", a.register)
	mux.HandleFunc("/logout", a.logout)
	mux.HandleFunc("/reset", a.reset)
	mux.HandleFunc("/cases", a.cases)
	mux.HandleFunc("/cases/", a.caseRoute)
	mux.HandleFunc("/reports/", a.report)
	mux.HandleFunc("/admin/reviews", a.adminReviews)
	mux.HandleFunc("/admin/reviews/", a.adminReviewRoute)
	mux.HandleFunc("/api/cases/", a.apiCaseSummary)
}
