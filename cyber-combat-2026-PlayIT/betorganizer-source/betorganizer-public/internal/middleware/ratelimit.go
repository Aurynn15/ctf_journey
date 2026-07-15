package middleware

import (
	"regexp"
	"strings"
	"sync"
	"time"
)

var sqlKeywords = []string{
	"and", "union", "select", "from", "where",
	"insert", "update", "delete", "drop", "--", "#", "/*",
	"sleep", "benchmark", "having", "group", "order", "by",
	"case", "when", "then", "cast", "convert", "char", "hex",
}

var inputFilter = regexp.MustCompile(`(?m)^[a-zA-Z0-9_\s]+$`)

var (
	loginAttempts = map[string][]time.Time{}
	loginMu       sync.Mutex
)

func CheckRateLimit(ip string) bool {
	loginMu.Lock()
	defer loginMu.Unlock()
	now := time.Now()
	var recent []time.Time
	for _, t := range loginAttempts[ip] {
		if now.Sub(t) < time.Minute {
			recent = append(recent, t)
		}
	}
	loginAttempts[ip] = append(recent, now)
	return len(recent) >= 20
}

func IsMalicious(input string) bool {
	lower := strings.ToLower(input)
	for _, kw := range sqlKeywords {
		if strings.Contains(lower, kw) {
			return true
		}
	}
	return !inputFilter.MatchString(input)
}
