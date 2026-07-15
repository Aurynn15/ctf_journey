package handler

import (
	"bytes"
	"database/sql"
	"encoding/csv"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"time"

	"betorganizer/internal/session"
	"betorganizer/internal/store"
)

func GenerateMatchReportHandler(w http.ResponseWriter, r *http.Request) {
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

	var homeTeam, awayTeam, matchDate, status, result string
	var createdBy sql.NullInt64
	var organizerName string
	err = store.DB.QueryRow(`
		SELECT m.home_team, m.away_team, m.match_date, m.status, COALESCE(m.result, ''), m.created_by, COALESCE(u.username, 'System')
		FROM matches m
		LEFT JOIN users u ON u.id = m.created_by
		WHERE m.id = ?`, matchID,
	).Scan(&homeTeam, &awayTeam, &matchDate, &status, &result, &createdBy, &organizerName)
	if err != nil {
		http.Error(w, "Match not found", 404)
		return
	}

	if user.Role == "organizer" {
		if !createdBy.Valid || int(createdBy.Int64) != user.ID {
			http.Error(w, "You can only generate reports for your own matches", 403)
			return
		}
	}

	var totalBettors int
	store.DB.QueryRow("SELECT COUNT(*) FROM predictions WHERE match_id=?", matchID).Scan(&totalBettors)

	var totalWagered int
	store.DB.QueryRow("SELECT COALESCE(SUM(bet_amount), 0) FROM predictions WHERE match_id=?", matchID).Scan(&totalWagered)

	var avgBet float64 = 0.0
	if totalBettors > 0 {
		avgBet = float64(totalWagered) / float64(totalBettors)
	}
	avgBetVal := fmt.Sprintf("%.1f", avgBet)

	var distHomeCount, distHomeCoins int
	var distDrawCount, distDrawCoins int
	var distAwayCount, distAwayCoins int

	store.DB.QueryRow("SELECT COUNT(*), COALESCE(SUM(bet_amount), 0) FROM predictions WHERE match_id=? AND prediction='home'", matchID).Scan(&distHomeCount, &distHomeCoins)
	store.DB.QueryRow("SELECT COUNT(*), COALESCE(SUM(bet_amount), 0) FROM predictions WHERE match_id=? AND prediction='draw'", matchID).Scan(&distDrawCount, &distDrawCoins)
	store.DB.QueryRow("SELECT COUNT(*), COALESCE(SUM(bet_amount), 0) FROM predictions WHERE match_id=? AND prediction='away'", matchID).Scan(&distAwayCount, &distAwayCoins)

	var distHomePct, distDrawPct, distAwayPct float64 = 0.0, 0.0, 0.0
	if totalBettors > 0 {
		distHomePct = float64(distHomeCount) / float64(totalBettors) * 100
		distDrawPct = float64(distDrawCount) / float64(totalBettors) * 100
		distAwayPct = float64(distAwayCount) / float64(totalBettors) * 100
	}
	distHomePctVal := fmt.Sprintf("%.1f", distHomePct)
	distDrawPctVal := fmt.Sprintf("%.1f", distDrawPct)
	distAwayPctVal := fmt.Sprintf("%.1f", distAwayPct)

	displayResult := "Pending Settlement"
	if result != "" {
		if result == "home" {
			displayResult = fmt.Sprintf("%s Win", homeTeam)
		} else if result == "away" {
			displayResult = fmt.Sprintf("%s Win", awayTeam)
		} else if result == "draw" {
			displayResult = "Draw"
		} else {
			displayResult = result
		}
	}

	escapeShellString := func(s string) string {
		s = strings.ReplaceAll(s, `'`, `'\''`)
		s = strings.ReplaceAll(s, "%", "%%%%")
		return s
	}

	var bettorRows strings.Builder
	pRows, qErr := store.DB.Query(`
		SELECT u.username, p.prediction, p.bet_amount, p.paid, p.created_at
		FROM predictions p
		JOIN users u ON u.id = p.user_id
		WHERE p.match_id = ?
		ORDER BY p.created_at DESC`, matchID)
	if qErr == nil {
		defer pRows.Close()
		for pRows.Next() {
			var bUsername, bPrediction, bCreatedAt string
			var bBetAmount, bPaid int
			if err := pRows.Scan(&bUsername, &bPrediction, &bBetAmount, &bPaid, &bCreatedAt); err == nil {
				badgeClass := ""
				badgeLabel := ""
				switch bPaid {
				case 0:
					badgeClass = "badge-pending"
					badgeLabel = "Pending"
				case 1:
					badgeClass = "badge-won-unclaimed"
					badgeLabel = "Won (Unclaimed)"
				case 2:
					badgeClass = "badge-won-claimed"
					badgeLabel = "Won (Claimed)"
				case -1:
					badgeClass = "badge-lost"
					badgeLabel = "Lost"
				}

				predText := bPrediction
				if predText == "home" {
					predText = "Home Win"
				} else if predText == "away" {
					predText = "Away Win"
				} else if predText == "draw" {
					predText = "Draw"
				}

				bettorRows.WriteString(fmt.Sprintf(
					`<tr>`+
						`<td>%s</td>`+
						`<td>%s</td>`+
						`<td>%d Coins</td>`+
						`<td><span class="badge %s">%s</span></td>`+
						`<td>%s</td>`+
						`</tr>`,
					bUsername, predText, bBetAmount, badgeClass, badgeLabel, bCreatedAt,
				))
			}
		}
	}

	if bettorRows.Len() == 0 {
		bettorRows.WriteString(`<tr><td colspan="5" style="text-align: center; color: #a3a3a3;">No bets placed on this match yet.</td></tr>`)
	}

	safeBettorRows := escapeShellString(bettorRows.String())

	outFileHTML := fmt.Sprintf("/tmp/report_%d_%d.html", matchID, time.Now().Unix())
	outFilePDF := fmt.Sprintf("/tmp/report_%d_%d.pdf", matchID, time.Now().Unix())

	htmlTemplate := `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Match Report - BetOrganizer</title>
<style>
  body {
    background-color: #0a0a0a;
    color: #ffffff;
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    margin: 0;
    padding: 40px;
    line-height: 1.6;
  }
  .container {
    max-width: 800px;
    margin: 0 auto;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 2px solid #39FF14;
    padding-bottom: 20px;
    margin-bottom: 30px;
  }
  .logo {
    font-size: 24px;
    font-weight: 800;
    color: #39FF14;
    text-transform: uppercase;
    letter-spacing: 1.5px;
  }
  .title {
    font-size: 20px;
    color: #a3a3a3;
    font-weight: 500;
  }
  .card {
    background-color: #121212;
    border: 1px solid #262626;
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 24px;
  }
  .card-title {
    font-size: 18px;
    color: #39FF14;
    margin-top: 0;
    margin-bottom: 20px;
    font-weight: 600;
    border-left: 4px solid #39FF14;
    padding-left: 10px;
  }
  .grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
  }
  .grid-3 {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 20px;
  }
  .info-item {
    margin-bottom: 12px;
  }
  .info-label {
    color: #a3a3a3;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .info-value {
    font-size: 16px;
    font-weight: 500;
  }
  .stat-card {
    text-align: center;
    background-color: #1a1a1a;
    padding: 15px;
    border-radius: 6px;
    border: 1px solid #2d2d2d;
  }
  .stat-val {
    font-size: 24px;
    font-weight: 700;
    color: #39FF14;
    margin-top: 5px;
  }
  .table {
    width: 100%%%%;
    border-collapse: collapse;
    margin-top: 10px;
  }
  .table th, .table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #262626;
  }
  .table th {
    background-color: #1a1a1a;
    color: #a3a3a3;
    font-weight: 600;
    font-size: 14px;
  }
  .table td {
    font-size: 14px;
  }
  .badge {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
  }
  .badge-pending {
    background: rgba(234, 179, 8, 0.15);
    color: #eab308;
    border: 1px solid rgba(234, 179, 8, 0.3);
  }
  .badge-won-unclaimed {
    background: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
    border: 1px solid rgba(59, 130, 246, 0.3);
  }
  .badge-won-claimed {
    background: rgba(34, 197, 94, 0.15);
    color: #22c55e;
    border: 1px solid rgba(34, 197, 94, 0.3);
  }
  .badge-lost {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
  }
  .badge-status {
    background: rgba(57, 255, 20, 0.15);
    color: #39FF14;
    border: 1px solid rgba(57, 255, 20, 0.3);
  }
  .footer {
    text-align: center;
    color: #525252;
    font-size: 12px;
    margin-top: 40px;
    border-top: 1px solid #262626;
    padding-top: 20px;
  }
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="logo">BetOrganizer</div>
    <div class="title">Match Report</div>
  </div>

  <div class="card">
    <div class="card-title">Match Details</div>
    <div class="grid-2">
      <div>
        <div class="info-item">
          <div class="info-label">Match ID</div>
          <div class="info-value">#%d</div>
        </div>
        <div class="info-item">
          <div class="info-label">Teams</div>
          <div class="info-value" style="font-weight: 700; color: #39FF14;">%s VS %s</div>
        </div>
        <div class="info-item">
          <div class="info-label">Date & Time</div>
          <div class="info-value">%s</div>
        </div>
      </div>
      <div>
        <div class="info-item">
          <div class="info-label">Status</div>
          <div class="info-value"><span class="badge badge-status">%s</span></div>
        </div>
        <div class="info-item">
          <div class="info-label">Result</div>
          <div class="info-value">%s</div>
        </div>
        <div class="info-item">
          <div class="info-label">Organizer</div>
          <div class="info-value">%s</div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Betting Summary</div>
    <div class="grid-3">
      <div class="stat-card">
        <div class="info-label">Total Bettors</div>
        <div class="stat-val">%d</div>
      </div>
      <div class="stat-card">
        <div class="info-label">Total Wagered</div>
        <div class="stat-val">%d Coins</div>
      </div>
      <div class="stat-card">
        <div class="info-label">Avg Bet Size</div>
        <div class="stat-val">%s Coins</div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="card-title">Prediction Distribution</div>
    <table class="table">
      <thead>
        <tr>
          <th>Prediction</th>
          <th>Bettors Count</th>
          <th>Total Wagered</th>
          <th>Percentage</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td style="font-weight: 600; color: #39FF14;">Home Win (%s)</td>
          <td>%d</td>
          <td>%d Coins</td>
          <td>%s%%%%</td>
        </tr>
        <tr>
          <td style="font-weight: 600; color: #a3a3a3;">Draw</td>
          <td>%d</td>
          <td>%d Coins</td>
          <td>%s%%%%</td>
        </tr>
        <tr>
          <td style="font-weight: 600; color: #3b82f6;">Away Win (%s)</td>
          <td>%d</td>
          <td>%d Coins</td>
          <td>%s%%%%</td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="card">
    <div class="card-title">Bettor Log</div>
    <table class="table">
      <thead>
        <tr>
          <th>Bettor</th>
          <th>Prediction</th>
          <th>Wager</th>
          <th>Status</th>
          <th>Placed At</th>
        </tr>
      </thead>
      <tbody>
        %s
      </tbody>
    </table>
  </div>

  <div class="footer">
    Generated by BetOrganizer Core Platform • Generated: '"$(date '+%%Y-%%m-%%d %%H:%%M:%%S')"'
  </div>
</div>
</body>
</html>`

	script := fmt.Sprintf(
		`printf '`+htmlTemplate+`\n' > %s && wkhtmltopdf --quiet %s %s`,
		matchID,
		homeTeam, awayTeam,
		matchDate,
		status,
		displayResult,
		organizerName,
		totalBettors,
		totalWagered,
		avgBetVal,
		homeTeam, distHomeCount, distHomeCoins, distHomePctVal,
		distDrawCount, distDrawCoins, distDrawPctVal,
		awayTeam, distAwayCount, distAwayCoins, distAwayPctVal,
		safeBettorRows,
		outFileHTML,
		outFileHTML,
		outFilePDF,
	)

	cmd := exec.Command("sh", "-c", script)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		http.Error(w, "Report generation failed: "+err.Error()+" | "+stderr.String(), 500)
		return
	}
	defer os.Remove(outFileHTML)
	defer os.Remove(outFilePDF)

	pdfData, err := os.ReadFile(outFilePDF)
	if err != nil {
		http.Error(w, "Failed to read report PDF", 500)
		return
	}

	filename := fmt.Sprintf("match_report_%d.pdf", matchID)
	w.Header().Set("Content-Type", "application/pdf")
	w.Header().Set("Content-Disposition", "attachment; filename="+filename)
	w.Write(pdfData)
}

func DownloadReportHandler(w http.ResponseWriter, r *http.Request) {
	user := session.GetSessionUser(r)
	if user == nil || (user.Role != "admin" && user.Role != "organizer") {
		http.Error(w, "Forbidden", 403)
		return
	}

	filename := fmt.Sprintf("report_%s.csv", time.Now().Format("20060102_150405"))
	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", "attachment; filename="+filename)

	cw := csv.NewWriter(w)
	cw.Write([]string{"=== MATCHES ==="})
	cw.Write([]string{"ID", "Home Team", "Away Team", "Match Date", "Status", "Result", "Organizer"})

	rows, err := store.DB.Query(`
		SELECT m.id, m.home_team, m.away_team, m.match_date, m.status,
		       COALESCE(m.result, ''), COALESCE(u.username, '')
		FROM matches m
		LEFT JOIN users u ON u.id = m.created_by
		ORDER BY m.id DESC
	`)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var id int
			var home, away, date, status, result, organizer string
			rows.Scan(&id, &home, &away, &date, &status, &result, &organizer)
			cw.Write([]string{strconv.Itoa(id), home, away, date, status, result, organizer})
		}
	}

	cw.Write([]string{})
	cw.Write([]string{"=== PREDICTIONS ==="})
	cw.Write([]string{"ID", "User", "Home Team", "Away Team", "Pick", "Bet Amount", "Status"})

	prows, err := store.DB.Query(`
		SELECT p.id, u.username, m.home_team, m.away_team, p.prediction, p.bet_amount, p.paid
		FROM predictions p
		JOIN users u ON u.id = p.user_id
		JOIN matches m ON m.id = p.match_id
		ORDER BY p.id DESC
	`)
	if err == nil {
		defer prows.Close()
		for prows.Next() {
			var id, betAmount, paid int
			var username, home, away, prediction string
			prows.Scan(&id, &username, &home, &away, &prediction, &betAmount, &paid)

			status := "pending"
			switch paid {
			case 1:
				status = "won (unclaimed)"
			case 2:
				status = "won (claimed)"
			case -1:
				status = "lost"
			}
			cw.Write([]string{strconv.Itoa(id), username, home, away, prediction, strconv.Itoa(betAmount), status})
		}
	}
	cw.Flush()
}
