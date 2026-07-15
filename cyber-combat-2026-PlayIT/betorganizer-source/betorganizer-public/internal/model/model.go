package model

import "database/sql"

type User struct {
	ID       int
	Username string
	Password string
	Role     string
	Balance  int
}

type Match struct {
	ID             int
	HomeTeam       string
	AwayTeam       string
	MatchDate      string
	Status         string
	Result         sql.NullString
	CreatedBy      sql.NullInt64
	OrganizerName  sql.NullString
	OrganizerBadge sql.NullString
}

type PredictionView struct {
	ID         int
	HomeTeam   string
	AwayTeam   string
	MatchDate  string
	Prediction string
	BetAmount  int
	Paid       int
	CreatedAt  string
}
