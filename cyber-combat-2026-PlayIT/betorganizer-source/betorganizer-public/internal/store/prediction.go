package store

import (
	"betorganizer/internal/model"
)

func GetUserPredictions(userID int) []model.PredictionView {
	rows, err := DB.Query(`
		SELECT p.id, m.home_team, m.away_team, m.match_date, p.prediction, p.bet_amount, p.paid, p.created_at
		FROM predictions p
		JOIN matches m ON m.id = p.match_id
		WHERE p.user_id = ?
		ORDER BY p.created_at DESC`, userID)
	if err != nil {
		return nil
	}
	defer rows.Close()
	var preds []model.PredictionView
	for rows.Next() {
		var p model.PredictionView
		rows.Scan(&p.ID, &p.HomeTeam, &p.AwayTeam, &p.MatchDate, &p.Prediction, &p.BetAmount, &p.Paid, &p.CreatedAt)
		preds = append(preds, p)
	}
	return preds
}
