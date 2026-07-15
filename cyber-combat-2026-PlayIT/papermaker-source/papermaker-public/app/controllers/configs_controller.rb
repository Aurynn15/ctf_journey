require 'yaml'
require 'securerandom'
require 'fileutils'
require 'rubygems/package'
require 'net/http'

class ConfigsController < ApplicationController
  before_action :require_login
  before_action :require_admin

  METADATA_DIR = Rails.root.join('tmp', 'metadata').freeze

  SNAPSHOT_TEMPLATE = <<~TEMPLATE
    # Application Metadata Snapshot
    app_metadata:
      name: "%{s_name}"
      version: "%{s_version}"
      build_number: "%{s_build}"
      environment: "%{s_environment}"

    snapshot:
      snapshot_id: "%{s_snap_id}"
      type: "%{s_snap_type}"

    application_info:
      description: "%{s_description}"
      author: "%{s_author}"
      license: "%{s_license}"
      repository: "%{s_repository}"
  TEMPLATE

  def index
  end

  def submit
    token = SecureRandom.hex(16)
    FileUtils.mkdir_p(METADATA_DIR)

    yaml_content = SNAPSHOT_TEMPLATE % {
      s_name:        params[:name].to_s,
      s_version:     params[:version].to_s,
      s_build:       params[:build].to_s,
      s_environment: params[:environment].to_s,
      s_snap_id:     params[:snap_id].to_s,
      s_snap_type:   params[:snap_type].to_s,
      s_description: params[:description].to_s,
      s_author:      params[:author].to_s,
      s_license:     params[:license].to_s,
      s_repository:  params[:repository].to_s,
    }

    File.write(METADATA_DIR.join("snapshot_#{token}"), yaml_content)

    render json: {
      status:  'pending',
      message: 'Snapshot staged. Apply with the provided token.',
      token:   token,
      apply:   "/config/apply/#{token}"
    }
  end

  def apply
    token = params[:token].to_s.gsub(/[^a-f0-9]/, '')
    tmp_path = METADATA_DIR.join("snapshot_#{token}")

    unless File.exist?(tmp_path)
      render json: { status: 'error', message: 'Invalid token' }, status: :not_found
      return
    end

    yaml_str  = File.read(tmp_path)
    File.delete(tmp_path)

    sidecar = Pathname.new("/tmp/snap_load_#{Process.pid}")

    begin
      data = YAML.unsafe_load(yaml_str)

      snapshot_path = Rails.root.join('snapshot.yaml')
      File.write(snapshot_path, yaml_str)

      keys = data.is_a?(Hash) ? data.keys.map(&:to_s) : []
      render json: {
        status:  'ok',
        message: "Loaded keys: #{keys.join(', ')}"
      }
    rescue => e
      detail = File.exist?(sidecar) ? File.read(sidecar).strip : e.message.split("\n").first
      render json: {
        status:  'error',
        message: "YAML parse error: #{detail}"
      }, status: :unprocessable_entity
    ensure
      File.delete(sidecar) if File.exist?(sidecar)
    end
  end

  private

  def require_admin
    redirect_to root_path, alert: 'Unauthorized access' unless current_user&.role == 'admin'
  end
end
