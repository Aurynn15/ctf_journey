package store

import (
	"crypto/md5"
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"log"
)

func SeedDB() {

	var adminExists int
	DB.QueryRow("SELECT COUNT(*) FROM users WHERE username='admin'").Scan(&adminExists)
	if adminExists == 0 {
		randomPassword := generateRandomPassword()
		h := md5.Sum([]byte(randomPassword))
		hash := fmt.Sprintf("%x", h)
		_, err := DB.Exec(
			"INSERT OR IGNORE INTO users (username, password, role, balance) VALUES ('admin', ?, 'admin', 99999)",
			hash,
		)
		if err != nil {
			log.Fatal(err)
		}
		log.Printf("[*] Admin account created (password: %s)", randomPassword)
	}

	var matchCount int
	DB.QueryRow("SELECT COUNT(*) FROM matches").Scan(&matchCount)
	if matchCount == 0 {
		stmts := []string{
			"INSERT OR IGNORE INTO matches (home_team, away_team, match_date, created_by) VALUES ('Manchester United', 'Liverpool', '2025-07-01 20:00', (SELECT id FROM users WHERE username = 'admin'))",
			"INSERT OR IGNORE INTO matches (home_team, away_team, match_date, created_by) VALUES ('Barcelona', 'Real Madrid', '2025-07-05 21:00', (SELECT id FROM users WHERE username = 'admin'))",
			"INSERT OR IGNORE INTO matches (home_team, away_team, match_date, created_by) VALUES ('PSG', 'Bayern Munich', '2025-07-10 19:00', (SELECT id FROM users WHERE username = 'admin'))",
		}
		for _, stmt := range stmts {
			if _, err := DB.Exec(stmt); err != nil {
				log.Fatal(err)
			}
		}
	}

	DB.Exec("UPDATE matches SET created_by = (SELECT id FROM users WHERE username = 'admin') WHERE created_by IS NULL")
}

func generateRandomPassword() string {
	b := make([]byte, 12)
	rand.Read(b)
	return hex.EncodeToString(b)
}
