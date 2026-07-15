class CreateLogs < ActiveRecord::Migration[6.1]
  def change
    create_table :logs do |t|
      t.string :author
      t.string :title
      t.text :report
      t.string :attachment
      t.datetime :resolved_at

      t.timestamps
    end
  end
end
