package store

import (
	"betorganizer/internal/model"
)

func GetUserByID(id int) *model.User {
	row := DB.QueryRow("SELECT id, username, password, role, balance FROM users WHERE id=?", id)
	var u model.User
	if err := row.Scan(&u.ID, &u.Username, &u.Password, &u.Role, &u.Balance); err != nil {
		return nil
	}
	return &u
}
