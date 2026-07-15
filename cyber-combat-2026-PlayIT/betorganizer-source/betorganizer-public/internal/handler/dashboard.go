package handler

import (
	"fmt"
	"net/http"

	"betorganizer/internal/session"
	"betorganizer/internal/store"
	"betorganizer/internal/tmpl"
)

func BalanceHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		w.Write([]byte("0"))
		return
	}
	fresh := store.GetUserByID(user.ID)
	if fresh == nil {
		w.Write([]byte("0"))
		return
	}
	session.RefreshSession(session.GetSessionToken(r), *fresh)
	fmt.Fprintf(w, "%d", fresh.Balance)
}

func DashboardHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}

	fresh := store.GetUserByID(user.ID)
	if fresh != nil {
		token := session.GetSessionToken(r)
		session.RefreshSession(token, *fresh)
		user = fresh
	}

	matches := store.GetAllMatches()
	preds := store.GetUserPredictions(user.ID)

	bettedMatches := map[int]bool{}
	rows, _ := store.DB.Query("SELECT match_id FROM predictions WHERE user_id=?", user.ID)
	if rows != nil {
		for rows.Next() {
			var mid int
			rows.Scan(&mid)
			bettedMatches[mid] = true
		}
		rows.Close()
	}

	tmpl.RenderTemplate(w, "dashboard.html", map[string]any{
		"User":          user,
		"Matches":       matches,
		"Predictions":   preds,
		"BettedMatches": bettedMatches,
	})
}
