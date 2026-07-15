class HistoriesController < ApplicationController
  before_action :require_login
  before_action :require_user

  def index
    @histories = current_user.histories.order(updated_at: :desc)
  end

  def destroy
    @history = current_user.histories.find_by(id: params[:id])
    if @history
      dir = Rails.root.join("tmp", "latex", @history.user_id.to_s, @history.id)
      FileUtils.rm_rf(dir)
      @history.destroy
      flash[:notice] = "History successfully deleted!"
    end
    redirect_to history_path
  end


  private

  def require_user
    redirect_to root_path, alert: "Unauthorized access" if current_user&.role == "admin"
  end
end
