Rails.application.configure do
  config.cache_classes = true
  config.eager_load = true
  config.consider_all_requests_local = false
  config.public_file_server.enabled = true
  config.active_support.report_deprecations = false
  config.action_controller.perform_caching = true
end
