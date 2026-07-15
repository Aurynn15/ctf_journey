package resolver

import (
	"log"
	"math/rand"
	"time"

	"betorganizer/internal/store"
)

var resultOptions = []string{"home", "draw", "away"}

func StartAutoResolver() {
	go func() {
		for {
			time.Sleep(3 * time.Minute)
			resolveFinishedMatches()
		}
	}()
	log.Println("[*] Auto-resolver started (interval: 3 minutes)")
}

func resolveFinishedMatches() {
	rows, err := store.DB.Query(`
		SELECT id, home_team, away_team
		FROM matches
		WHERE result IS NULL
		  AND status != 'finished'
		  AND match_date <= datetime('now', 'localtime')
	`)
	if err != nil {
		log.Println("[resolver] query error:", err)
		return
	}

	type pendingMatch struct {
		id   int
		home string
		away string
	}
	var pending []pendingMatch
	for rows.Next() {
		var m pendingMatch
		rows.Scan(&m.id, &m.home, &m.away)
		pending = append(pending, m)
	}
	rows.Close()

	for _, m := range pending {
		result := resultOptions[rand.Intn(3)]

		store.DB.Exec("UPDATE matches SET result=?, status='finished' WHERE id=?", result, m.id)

		type predRow struct {
			id         int
			prediction string
		}
		var preds []predRow
		prows, _ := store.DB.Query(
			"SELECT id, prediction FROM predictions WHERE match_id=? AND paid=0", m.id,
		)
		if prows != nil {
			for prows.Next() {
				var p predRow
				prows.Scan(&p.id, &p.prediction)
				preds = append(preds, p)
			}
			prows.Close()
		}
		for _, p := range preds {
			if p.prediction == result {
				store.DB.Exec("UPDATE predictions SET paid=1 WHERE id=?", p.id)
			} else {
				store.DB.Exec("UPDATE predictions SET paid=-1 WHERE id=?", p.id)
			}
		}

		log.Printf("[resolver] match %d (%s vs %s) → %s (%d predictions settled)",
			m.id, m.home, m.away, result, len(preds))
	}
}
