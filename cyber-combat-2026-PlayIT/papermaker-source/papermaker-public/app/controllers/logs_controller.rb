class LogsController < ApplicationController
  before_action :require_login
  before_action :require_admin

  def index
    @logs = ordered_logs
    @log = Log.new
  end

  def create
    @log = Log.new(log_params)
    @log.author = current_user.username
    @log.created_at = Time.current

    if params[:log][:attachment].present?
      file = params[:log][:attachment]
      
      filename = sanitize_fn(file.original_filename)

      if file.size > 1.megabyte
        return handle_log_error("File size exeeded for <b>#{filename}</b>")
      end

      allowed_types = ["image/png", "image/jpeg", "application/pdf"]
      ext = File.extname(file.original_filename).downcase
      allowed_exts = [".png", ".jpg", ".jpeg", ".pdf"]

      if !allowed_types.include?(file.content_type) || !allowed_exts.include?(ext)
        return handle_log_error("Invalid file type for <b>#{filename}</b>")
      end

      upload_dir = Rails.root.join('tmp', 'uploads')
      FileUtils.mkdir_p(upload_dir)
      begin
        File.open(upload_dir.join(filename), 'wb') do |f|
          f.write(file.read)
        end
        @log.attachment = filename
      rescue => e
        return handle_log_error("Error while storing the <b>#{filename}</b>")
      end
    end

    if @log.save
      message = "<h1>Log successfully created!</h1>"
      if @log.attachment.present?
        message += "To see the #{@log.attachment}, you can access to <a href='#{log_attachment_path(@log)}'>attachment</a>."
      end
      message += "Total unresolve log: <b><%= Log.where(resolved_at: nil).count %></b>"
      
      set_flash(:success, message)
      redirect_to log_path
    else
      handle_log_error("Failed to save log")
    end
  end

  def attachment
    @log = Log.find_by(id: params[:id])
    if @log && @log.attachment.present?
      file_path = Rails.root.join('tmp', 'uploads', @log.attachment)
      if File.exist?(file_path)
        send_file file_path, disposition: 'inline'
      else
        redirect_to log_path, alert: "Attachment file not found on server."
      end
    else
      redirect_to log_path, alert: "No attachment found."
    end
  end

  def resolve
    @log = Log.find_by(id: params[:id])
    if @log
      @log.update(resolved_at: Time.current)
    end
    redirect_to log_path
  end

  def destroy
    @log = Log.find_by(id: params[:id])
    if @log
      if @log.attachment.present?
        file_path = Rails.root.join('tmp', 'uploads', @log.attachment)
        File.delete(file_path) if File.exist?(file_path)
      end
      @log.destroy
      set_flash(:success, "<h1>Log successfully deleted!</h1>")
    end
    redirect_to log_path
  end

  private

  def handle_log_error(tmp)
    @logs = ordered_logs
    message = "<h1>Error!</h1>" + tmp
    set_flash(:error, message)
    render :index, status: :unprocessable_entity
  end

  def set_flash(type, tmp)
    message = ERB.new(tmp).result(binding)
    if type == :error
      flash.now[:log_error] = message
    else
      flash[:log_success] = message
    end
  end

  def sanitize_fn(filename)
    res = filename.chars.select { |c| c.ord >= 32 && c.ord <= 126 }.join
    res = res.gsub(/[\s\n\r]/, '')
    res = res.gsub(/[`'"]/, '')
    res = res.gsub(/\|/, '')
    res = res.gsub(/\b(cat|ls|echo|find|whoami|id|uname|pwd|sh|bash|grep|awk|sed|curl|wget)\b/i, '')
    res = res.gsub(/\b(system|eval|File|open|Kernel|ENV|class|spawn|exec|Dir)\b/i, '')
    res
  end

  def ordered_logs
    Log.all.order(Arel.sql("CASE WHEN resolved_at IS NULL THEN 0 ELSE 1 END"), created_at: :desc)
  end

  def log_params
    params.require(:log).permit(:title, :report)
  end

  def require_admin
    redirect_to root_path, alert: "Unauthorized access" unless current_user&.role == "admin"
  end
end