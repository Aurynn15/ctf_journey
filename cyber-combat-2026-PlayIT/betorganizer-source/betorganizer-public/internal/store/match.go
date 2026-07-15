package store

import (
	"betorganizer/internal/model"
)

func GetAllMatches() []model.Match {
	rows, err := DB.Query(`
		SELECT m.id, m.home_team, m.away_team, m.match_date, m.status, m.result, m.created_by,
		       u.username, u.badge
		FROM matches m
		LEFT JOIN users u ON u.id = m.created_by
		ORDER BY m.id`)
	if err != nil {
		return nil
	}
	defer rows.Close()
	var matches []model.Match
	for rows.Next() {
		var m model.Match
		rows.Scan(&m.ID, &m.HomeTeam, &m.AwayTeam, &m.MatchDate, &m.Status, &m.Result, &m.CreatedBy, &m.OrganizerName, &m.OrganizerBadge)
		matches = append(matches, m)
	}
	return matches
}
