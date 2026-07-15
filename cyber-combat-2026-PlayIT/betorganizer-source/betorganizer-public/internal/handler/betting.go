package handler

import (
	"database/sql"
	"fmt"
	"net/http"
	"strconv"
	"time"

	"betorganizer/internal/session"
	"betorganizer/internal/store"
)

func ClaimRewardHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}

	var lastClaim sql.NullTime
	store.DB.QueryRow("SELECT last_claim FROM users WHERE id=?", user.ID).Scan(&lastClaim)

	if lastClaim.Valid && time.Since(lastClaim.Time) < 5*time.Minute {
		remaining := 5*time.Minute - time.Since(lastClaim.Time)
		w.Write([]byte(fmt.Sprintf("Next claim in: %v", remaining.Round(time.Second))))
		return
	}

	store.DB.Exec("UPDATE users SET balance = balance + 100, last_claim = ? WHERE id=?",
		time.Now(), user.ID)

	w.Header().Set("HX-Trigger", "balanceUpdate")
	w.Write([]byte("Claimed! +100 coins"))
}

func BuyTicketHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}

	fresh := store.GetUserByID(user.ID)
	if fresh == nil {
		http.Error(w, "User not found", 500)
		return
	}

	if fresh.Balance < 50000 {
		w.WriteHeader(400)
		w.Write([]byte(fmt.Sprintf("Insufficient balance. Need 50000, have %d", fresh.Balance)))
		return
	}
	if fresh.Role != "user" {
		w.Write([]byte("You already have elevated access"))
		return
	}

	store.DB.Exec("UPDATE users SET balance = balance - 50000, role = 'organizer' WHERE id=?", fresh.ID)

	token := session.GetSessionToken(r)
	fresh.Balance -= 50000
	fresh.Role = "organizer"
	session.RefreshSession(token, *fresh)

	w.Header().Set("HX-Trigger", "balanceUpdate, roleUpdate")
	w.Write([]byte("Organizer Ticket purchased! Reload to access panel."))
}

func PredictHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", 405)
		return
	}

	r.ParseForm()
	matchID, err := strconv.Atoi(r.FormValue("match_id"))
	if err != nil || r.FormValue("prediction") == "" {
		http.Error(w, "Invalid input", 400)
		return
	}

	prediction := r.FormValue("prediction")
	betAmount, err := strconv.Atoi(r.FormValue("bet_amount"))
	if err != nil || betAmount < 1 {
		w.WriteHeader(400)
		w.Write([]byte("Bet amount must be at least 1"))
		return
	}

	var createdBy sql.NullInt64
	store.DB.QueryRow("SELECT created_by FROM matches WHERE id=?", matchID).Scan(&createdBy)
	if createdBy.Valid && int(createdBy.Int64) == user.ID {
		w.WriteHeader(403)
		w.Write([]byte("You cannot predict your own match"))
		return
	}

	var existing int
	store.DB.QueryRow("SELECT COUNT(*) FROM predictions WHERE user_id=? AND match_id=?", user.ID, matchID).Scan(&existing)
	if existing > 0 {
		w.WriteHeader(400)
		w.Write([]byte("You already placed a bet on this match"))
		return
	}

	fresh := store.GetUserByID(user.ID)
	if fresh == nil || fresh.Balance < betAmount {
		w.WriteHeader(400)
		w.Write([]byte(fmt.Sprintf("Insufficient balance. Have %d, need %d", fresh.Balance, betAmount)))
		return
	}

	store.DB.Exec("UPDATE users SET balance = balance - ? WHERE id=?", betAmount, user.ID)
	store.DB.Exec("INSERT INTO predictions (user_id, match_id, prediction, bet_amount) VALUES (?,?,?,?)",
		user.ID, matchID, prediction, betAmount)

	fresh.Balance -= betAmount
	session.RefreshSession(session.GetSessionToken(r), *fresh)

	w.Header().Set("HX-Trigger", "balanceUpdate")
	w.Write([]byte(fmt.Sprintf("Bet placed! -%d coins on %s", betAmount, prediction)))
}

func ClaimWinHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil {
		http.Redirect(w, r, "/login", http.StatusFound)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "Method Not Allowed", 405)
		return
	}

	predID, err := strconv.Atoi(r.FormValue("pred_id"))
	if err != nil {
		http.Error(w, "Invalid pred_id", 400)
		return
	}

	var betAmount, ownerID int
	if err := store.DB.QueryRow("SELECT user_id, bet_amount FROM predictions WHERE id=? AND paid=1", predID).
		Scan(&ownerID, &betAmount); err != nil {
		w.WriteHeader(400)
		w.Write([]byte("Nothing to claim"))
		return
	}
	if ownerID != user.ID {
		w.WriteHeader(403)
		w.Write([]byte("Forbidden"))
		return
	}

	store.DB.Exec("UPDATE predictions SET paid=2 WHERE id=?", predID)
	store.DB.Exec("UPDATE users SET balance = balance + ? WHERE id=?", betAmount*2, user.ID)

	if fresh := store.GetUserByID(user.ID); fresh != nil {
		session.RefreshSession(session.GetSessionToken(r), *fresh)
	}

	w.Header().Set("HX-Trigger", "balanceUpdate")
	w.Write([]byte(fmt.Sprintf("+%d coins claimed!", betAmount*2)))
}
