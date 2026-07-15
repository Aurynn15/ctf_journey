Rails.application.routes.draw do
  root "pages#index"

  get  "/register", to: "users#new"
  post "/register", to: "users#create"
  get  "/login",    to: "sessions#new"
  post "/login",    to: "sessions#create"
  delete "/logout", to: "sessions#destroy"

  get  "/render",        to: "render#new",      as: :render
  post "/render",        to: "render#create"
  get  "/history",       to: "histories#index", as: :history
  delete "/history/:id", to: "histories#destroy", as: :delete_history

  get "/result/download/:id", to: "render#download", as: :result_download

  get    "/log",                to: "logs#index",      as: :log
  post   "/log",                to: "logs#create"
  get    "/log/:id/attachment", to: "logs#attachment", as: :log_attachment
  patch  "/log/:id/resolve",    to: "logs#resolve",    as: :resolve_log
  delete "/log/:id",            to: "logs#destroy",    as: :delete_log

  get  "/config",              to: "configs#index",  as: :config_index
  post "/config",              to: "configs#submit"
  get  "/config/apply/:token", to: "configs#apply",  as: :config_apply
end
