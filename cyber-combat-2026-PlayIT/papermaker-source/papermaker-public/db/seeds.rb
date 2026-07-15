require "securerandom"

User.find_or_create_by!(username: "administrator") do |user|
  user.password = SecureRandom.hex(16)
  user.role = "admin"
end

