package main

import "time"

type User struct {
	ID           uint   `gorm:"primaryKey" json:"id"`
	Username     string `gorm:"uniqueIndex" json:"username"`
	PasswordHash string `json:"-"`
	Role         string `json:"role"`
	ResetRows    []ResetRow
}

type ResetRow struct {
	ID         uint `gorm:"primaryKey" json:"id"`
	UserID     uint `json:"user_id"`
	TokenHash  string
	HashPrefix string `json:"hash_prefix"`
	CreatedMin int64  `json:"created_minute"`
	Used       bool   `json:"used"`
}

type Case struct {
	ID        uint `gorm:"primaryKey" json:"id"`
	Title     string
	OwnerID   uint
	Owner     User
	Status    string
	Marker    string
	CreatedAt time.Time
	Evidence  []Evidence
	Reports   []ReviewReport
}

type Evidence struct {
	ID          uint `gorm:"primaryKey" json:"id"`
	CaseID      uint
	Filename    string
	StoragePath string
	Summary     string
}

type ReviewReport struct {
	ID          uint `gorm:"primaryKey" json:"id"`
	CaseID      uint
	Kind        string
	ShareToken  string `gorm:"index"`
	Diagnostics string
	CreatedAt   time.Time
}

type Claims struct {
	Sub  uint   `json:"sub"`
	User string `json:"user"`
	Role string `json:"role"`
	Exp  int64  `json:"exp"`
}

type AnalyzerResult struct {
	Title   string `json:"title"`
	Mime    string `json:"mime"`
	Summary string `json:"summary"`
}
