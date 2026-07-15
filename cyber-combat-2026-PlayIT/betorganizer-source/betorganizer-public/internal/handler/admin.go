package handler

import (
	"database/sql"
	"net/http"
	"strconv"
	"strings"

	"betorganizer/internal/session"
	"betorganizer/internal/store"
	"betorganizer/internal/tmpl"
)

func AdminHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}
	if user.Role != "admin" && user.Role != "organizer" {
		http.Error(w, "Forbidden", 403)
		return
	}

	fresh := store.GetUserByID(user.ID)
	if fresh != nil {
		token := session.GetSessionToken(r)
		session.RefreshSession(token, *fresh)
		user = fresh
	}

	tmpl.RenderTemplate(w, "admin.html", map[string]any{
		"User":    user,
		"Matches": store.GetAllMatches(),
	})
}

func DeleteMatchHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil || (user.Role != "admin" && user.Role != "organizer") {
		http.Error(w, "Forbidden", 403)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", 405)
		return
	}

	matchID, err := strconv.Atoi(r.FormValue("match_id"))
	if err != nil {
		http.Error(w, "Invalid match_id", 400)
		return
	}

	var createdBy sql.NullInt64
	store.DB.QueryRow("SELECT created_by FROM matches WHERE id=?", matchID).Scan(&createdBy)

	if user.Role == "organizer" {
		if !createdBy.Valid || int(createdBy.Int64) != user.ID {
			w.WriteHeader(403)
			w.Write([]byte("You can only delete your own matches"))
			return
		}
	}

	store.DB.Exec("DELETE FROM predictions WHERE match_id=?", matchID)
	store.DB.Exec("DELETE FROM matches WHERE id=?", matchID)
	w.Write([]byte("deleted"))
}

func AddMatchHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil || (user.Role != "admin" && user.Role != "organizer") {
		http.Error(w, "Forbidden", 403)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", 405)
		return
	}

	r.ParseForm()
	homeTeam := strings.TrimSpace(r.FormValue("home_team"))
	awayTeam := strings.TrimSpace(r.FormValue("away_team"))
	matchDate := strings.TrimSpace(r.FormValue("match_date"))

	if homeTeam == "" || awayTeam == "" || matchDate == "" {
		w.WriteHeader(400)
		w.Write([]byte("All fields are required"))
		return
	}

	store.DB.Exec("INSERT INTO matches (home_team, away_team, match_date, created_by) VALUES (?,?,?,?)",
		homeTeam, awayTeam, matchDate, user.ID)

	w.Write([]byte("✓ Match added: " + homeTeam + " vs " + awayTeam))
}

func SetResultHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil || (user.Role != "admin" && user.Role != "organizer") {
		http.Error(w, "Forbidden", 403)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", 405)
		return
	}

	r.ParseForm()
	matchID, err := strconv.Atoi(r.FormValue("match_id"))
	if err != nil {
		http.Error(w, "Invalid match_id", 400)
		return
	}

	result := r.FormValue("result")
	if result != "home" && result != "draw" && result != "away" {
		http.Error(w, "Invalid result", 400)
		return
	}

	var createdBy sql.NullInt64
	store.DB.QueryRow("SELECT created_by FROM matches WHERE id=?", matchID).Scan(&createdBy)

	if user.Role == "organizer" {
		if !createdBy.Valid || int(createdBy.Int64) != user.ID {
			w.WriteHeader(403)
			w.Write([]byte("You can only set results for your own matches"))
			return
		}
	}

	store.DB.Exec("UPDATE matches SET result=?, status='finished' WHERE id=?", result, matchID)

	type predRow struct {
		id         int
		prediction string
	}
	var toUpdate []predRow
	rows, _ := store.DB.Query("SELECT id, prediction FROM predictions WHERE match_id=? AND paid=0", matchID)
	if rows != nil {
		for rows.Next() {
			var pr predRow
			rows.Scan(&pr.id, &pr.prediction)
			toUpdate = append(toUpdate, pr)
		}
		rows.Close()
	}

	for _, pr := range toUpdate {
		if pr.prediction == result {
			store.DB.Exec("UPDATE predictions SET paid=1 WHERE id=?", pr.id)
		} else {
			store.DB.Exec("UPDATE predictions SET paid=-1 WHERE id=?", pr.id)
		}
	}

	w.Write([]byte("Result set: " + result))
}
