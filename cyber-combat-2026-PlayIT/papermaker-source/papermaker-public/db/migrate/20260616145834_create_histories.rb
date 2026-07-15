class CreateHistories < ActiveRecord::Migration[6.1]
  def change
    create_table :histories, id: false do |t|
      t.string :id, primary_key: true
      t.integer :user_id, null: false
      t.text :content
      t.timestamps
    end
    add_index :histories, :user_id
  end
end
