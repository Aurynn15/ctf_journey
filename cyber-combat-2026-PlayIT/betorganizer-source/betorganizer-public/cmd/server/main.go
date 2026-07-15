package main

import (
	"log"
	"net/http"
	"os"

	"betorganizer/internal/handler"
	"betorganizer/internal/resolver"
	"betorganizer/internal/session"
	"betorganizer/internal/store"
	"betorganizer/internal/tmpl"
)

func main() {
	store.InitDB()
	tmpl.InitTemplates()
	resolver.StartAutoResolver()

	mux := http.NewServeMux()

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		if u := session.GetSessionUser(r); u != nil {
			http.Redirect(w, r, "/dashboard", http.StatusFound)
		} else {
			http.Redirect(w, r, "/login", http.StatusFound)
		}
	})

	mux.HandleFunc("/login", handler.LoginPageHandler)
	mux.HandleFunc("/register", handler.RegisterPageHandler)
	mux.HandleFunc("/logout", handler.LogoutHandler)
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(200)
		w.Write([]byte("OK"))
	})

	mux.HandleFunc("/dashboard", handler.DashboardHandler)
	mux.HandleFunc("/balance", handler.BalanceHandler)
	mux.HandleFunc("/claim-reward", handler.ClaimRewardHandler)
	mux.HandleFunc("/claim-win", handler.ClaimWinHandler)
	mux.HandleFunc("/shop/buy-ticket", handler.BuyTicketHandler)
	mux.HandleFunc("/predict", handler.PredictHandler)
	mux.HandleFunc("/profile/upload-badge", handler.UploadBadgeHandler)
	mux.HandleFunc("/profile/preview-badge", handler.PreviewBadgeHandler)

	mux.HandleFunc("/admin", handler.AdminHandler)
	mux.HandleFunc("/admin/report-pdf", handler.DownloadReportHandler)
	mux.HandleFunc("/admin/generate-report", handler.GenerateMatchReportHandler)
	mux.HandleFunc("/admin/set-result", handler.SetResultHandler)
	mux.HandleFunc("/admin/add-match", handler.AddMatchHandler)
	mux.HandleFunc("/admin/delete-match", handler.DeleteMatchHandler)

	mux.Handle("/uploads/", http.StripPrefix("/uploads/", http.FileServer(http.Dir("templates"))))

	port := os.Getenv("PORT")
	if port == "" {
		port = os.Getenv("AD_PLATFORM_SERVICE_PORT")
	}
	if port == "" {
		port = "8140"
	}
	log.Println("[*] BetOrganizer running on :" + port)
	log.Fatal(http.ListenAndServe(":"+port, mux))
}
