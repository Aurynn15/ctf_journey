package store

import (
	"database/sql"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

var DB *sql.DB

func InitDB() {
	var err error
	DB, err = sql.Open("sqlite3", "/opt/ad/state/bet.db")
	if err != nil {
		log.Fatal(err)
	}

	schema := `
CREATE TABLE IF NOT EXISTS users (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	username   TEXT UNIQUE NOT NULL,
	password   TEXT NOT NULL,
	role       TEXT DEFAULT 'user',
	balance    INTEGER DEFAULT 50,
	last_claim DATETIME DEFAULT NULL,
	badge      TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS matches (
	id          INTEGER PRIMARY KEY AUTOINCREMENT,
	home_team   TEXT NOT NULL,
	away_team   TEXT NOT NULL,
	match_date  TEXT NOT NULL,
	status      TEXT DEFAULT 'upcoming',
	result      TEXT DEFAULT NULL,
	created_by  INTEGER DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS predictions (
	id         INTEGER PRIMARY KEY AUTOINCREMENT,
	user_id    INTEGER NOT NULL,
	match_id   INTEGER NOT NULL,
	prediction TEXT NOT NULL,
	bet_amount INTEGER NOT NULL DEFAULT 0,
	paid       INTEGER NOT NULL DEFAULT 0,
	created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
`
	if _, err := DB.Exec(schema); err != nil {
		log.Fatal(err)
	}

	SeedDB()
}
