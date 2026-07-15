class SessionsController < ApplicationController
  def new
  end

  def create
    user = User.find_by(username: params[:username].to_s)

    if user && user.password == params[:password].to_s
      session[:user_id] = user.id
      redirect_to render_path, notice: "Logged in"
    else
      flash.now[:alert] = "Invalid username or password"
      render :new, status: :unprocessable_entity
    end
  end

  def destroy
    reset_session
    redirect_to login_path, notice: "Logged out"
  end
end
