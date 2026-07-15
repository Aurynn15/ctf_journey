class User < ApplicationRecord
  has_many :histories, dependent: :destroy
  validates :username, presence: true, uniqueness: true, length: { maximum: 40 }
  validates :password, presence: true, length: { minimum: 6 }
end
