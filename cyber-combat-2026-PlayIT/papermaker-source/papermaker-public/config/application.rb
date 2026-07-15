require "logger"
require_relative "boot"

require "rails"
require "active_model/railtie"
require "active_job/railtie"
require "active_record/railtie"
require "action_controller/railtie"
require "action_view/railtie"
require "sprockets/railtie"

Bundler.require(*Rails.groups)

module AdRuby
  class Application < Rails::Application
    config.load_defaults 6.1
    config.secret_key_base = ENV.fetch("SECRET_KEY_BASE", "default_key_base")
    config.time_zone = "UTC"
  end
end
