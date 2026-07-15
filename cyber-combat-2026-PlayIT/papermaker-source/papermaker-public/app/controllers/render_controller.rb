class RenderController < ApplicationController
  before_action :require_login
  before_action :require_user

  def new
    @source = default_source
  end

  def create
    @source = params[:source].to_s
    result = PaperRenderer.new(@source, current_user.id).render

    if result.success?
      @pdf_id = result.id
      history = History.find_or_initialize_by(id: @pdf_id)
      history.user = current_user
      history.content = @source
      history.touch if history.persisted? # Update updated_at if it already exists
      history.save
      
      render :new, status: :ok
    else
      @error = result.error
      render :new, status: :unprocessable_entity
    end
  end

  def download
    id = params[:id].to_s
    path = Rails.root.join("tmp", "latex", current_user.id.to_s, id, "document.pdf")

    unless id.match?(/\A\d+_[a-f0-9]{64}\z/) && path.file?
      redirect_to render_path, alert: "PDF not found"
      return
    end

    send_file path, filename: "rendered.pdf", type: "application/pdf", disposition: "inline"
  end

  private

  def require_user
    redirect_to root_path, alert: "Unauthorized access" if current_user&.role == "admin"
  end

  def default_source
    <<~RAW
      \\section*{Example Document}
      Lorem ipsum dolor sit amet, consectetur adipiscing elit. Fusce aliquam nibh id ante interdum elementum. Donec interdum metus ipsum, quis vehicula libero facilisis non. Cras turpis ligula, viverra quis nunc id, auctor porta tortor. Pellentesque nec eros at sapien tempor vehicula. Nam elit sem, rhoncus ac molestie at, fermentum ut sem. Proin quis nunc non ex volutpat tempus. Curabitur quis ex venenatis, tincidunt ante vitae, euismod nisl. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae.

    RAW
  end
end
