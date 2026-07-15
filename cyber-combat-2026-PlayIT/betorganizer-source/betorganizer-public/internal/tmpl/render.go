package tmpl

import (
	"html/template"
	"log"
	"net/http"
	"os"
	"sync"
)

var (
	templates *template.Template
	tmplMu    sync.RWMutex
)

func buildFuncMap() template.FuncMap {
	return template.FuncMap{
		"int64":    func(i int) int64 { return int64(i) },
		"inBetted": func(m map[int]bool, id int) bool { return m[id] },
		"mul":      func(a, b int) int { return a * b },
		"readFile": func(path string) string {
			data, err := os.ReadFile(path)
			if err != nil {
				return ""
			}
			return string(data)
		},
	}
}

func InitTemplates() {
	t, err := template.New("").Funcs(buildFuncMap()).ParseGlob("templates/*")
	if err != nil {
		log.Fatal("template parse error:", err)
	}
	templates = t
}

func ReloadTemplates() error {
	t, err := template.New("").Funcs(buildFuncMap()).ParseGlob("templates/*")
	if err != nil {
		return err
	}
	tmplMu.Lock()
	templates = t
	tmplMu.Unlock()
	return nil
}

func RenderTemplate(w http.ResponseWriter, name string, data any) {
	tmplMu.RLock()
	defer tmplMu.RUnlock()
	if err := templates.ExecuteTemplate(w, name, data); err != nil {
		http.Error(w, "Template error: "+err.Error(), 500)
	}
}
