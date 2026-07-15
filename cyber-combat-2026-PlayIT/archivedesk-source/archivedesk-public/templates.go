package main

import (
	"bytes"
	"embed"
	"html/template"
	"net/http"
)

//go:embed templates/*.html static/*.css
var assets embed.FS

func parseTemplates() *template.Template {
	return template.Must(template.ParseFS(assets, "templates/*.html"))
}

func staticCSS() string {
	body, _ := assets.ReadFile("static/app.css")
	return string(body)
}

func (a *App) render(w http.ResponseWriter, name string, data map[string]any) {
	var body bytes.Buffer
	if err := a.templates.ExecuteTemplate(&body, name, data); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	data["Body"] = template.HTML(body.String())
	data["CSS"] = template.CSS(staticCSS())
	if err := a.templates.ExecuteTemplate(w, "base", data); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
