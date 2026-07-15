namespace :cleanup do
  desc "Clean up LaTeX history in database and tmp/latex files"
  task latex: :environment do
    puts "[Cleanup] Starting LaTeX history cleanup..."
    
    begin
      count = History.count
      History.delete_all
      puts "[Cleanup] Deleted #{count} database history records."
    rescue => e
      puts "[Cleanup] Error clearing database: #{e.message}"
    end

    begin
      latex_dir = Rails.root.join("tmp", "latex")
      if Dir.exist?(latex_dir)
        files = Dir.glob(File.join(latex_dir, "*"))
        FileUtils.rm_rf(files)
        puts "[Cleanup] Deleted #{files.size} items from tmp/latex."
      else
        puts "[Cleanup] Directory tmp/latex does not exist."
      end
    rescue => e
      puts "[Cleanup] Error clearing tmp/latex files: #{e.message}"
    end
    
    puts "[Cleanup] Cleanup finished."
  end
end
