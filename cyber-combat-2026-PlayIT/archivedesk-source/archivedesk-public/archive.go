package main

import (
	"archive/zip"
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"mime/multipart"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const analyzerMarker = "ARCHIVEDESK_ANALYZER_V1"

func (a *App) processArchive(caseID uint, file multipart.File, _ *multipart.FileHeader) error {
	body, err := io.ReadAll(io.LimitReader(file, 7<<20))
	if err != nil {
		return err
	}
	zr, err := zip.NewReader(bytes.NewReader(body), int64(len(body)))
	if err != nil {
		return errors.New("invalid zip archive")
	}
	if len(zr.File) > 24 {
		return errors.New("too many archive entries")
	}
	base := filepath.Join(stateDir, "uploads", randomHex(12))
	if err := os.MkdirAll(base, 0755); err != nil {
		return err
	}

	var seen archiveSeen
	for _, entry := range zr.File {
		if entry.FileInfo().IsDir() {
			continue
		}
		if err := a.extractEntry(caseID, base, entry, &seen); err != nil {
			return err
		}
	}
	if !seen.manifest || !seen.evidence {
		return errors.New("archive requires manifest.xml and evidence file")
	}
	return nil
}

type archiveSeen struct {
	manifest bool
	evidence bool
}

func (a *App) extractEntry(caseID uint, base string, entry *zip.File, seen *archiveSeen) error {
	if entry.UncompressedSize64 > 1<<20 {
		return errors.New("archive entry too large")
	}
	name := strings.TrimLeft(entry.Name, "/")
	ext := strings.ToLower(filepath.Ext(name))
	if filepath.Base(name) == "manifest.xml" {
		seen.manifest = true
	} else if ext != ".pdf" && ext != ".txt" && ext != ".meta" && filepath.Base(name) != "metadata" {
		return errors.New("unsupported evidence type")
	}
	target := filepath.Join(base, name)
	if !allowedArchiveTarget(base, target) {
		return errors.New("archive entry escapes allowed workspace")
	}
	if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
		return err
	}
	data, err := readZipEntry(entry)
	if err != nil {
		return err
	}
	mode := entry.Mode()
	if mode == 0 {
		mode = 0644
	}
	if err := os.WriteFile(target, data, mode); err != nil {
		return err
	}
	if ext == ".pdf" || ext == ".txt" || ext == ".meta" {
		seen.evidence = true
		a.db.Create(&Evidence{CaseID: caseID, Filename: filepath.Base(name), StoragePath: target, Summary: "pending analysis"})
	}
	return nil
}

func readZipEntry(entry *zip.File) ([]byte, error) {
	src, err := entry.Open()
	if err != nil {
		return nil, err
	}
	defer src.Close()
	return io.ReadAll(io.LimitReader(src, 1<<20))
}

func defaultAnalyzerBody() []byte {
	return []byte("#!/bin/sh\n# " + analyzerMarker + "\nprintf '{\"title\":\"%s\",\"mime\":\"text/plain\",\"summary\":\"clean evidence\"}\\n' \"$(basename \"$1\")\"\n")
}

func restoreDefaultAnalyzer() error {
	return os.WriteFile(analyzerPath(), defaultAnalyzerBody(), 0755)
}

func runAnalyzer(path string) (*AnalyzerResult, error) {
	defer func() { _ = restoreDefaultAnalyzer() }()
	info, err := os.Stat(analyzerPath())
	if err != nil || info.Mode()&0111 == 0 {
		return nil, errors.New("analyzer unavailable")
	}
	header, _ := os.ReadFile(analyzerPath())
	if !strings.Contains(string(header[:min(len(header), 96)]), analyzerMarker) {
		return nil, errors.New("analyzer integrity marker missing")
	}
	out, err := exec.Command(analyzerPath(), path).Output()
	if err != nil {
		return nil, err
	}
	var result AnalyzerResult
	if err := json.Unmarshal(out, &result); err != nil {
		return nil, err
	}
	if result.Title == "" || result.Mime == "" || result.Summary == "" {
		return nil, errors.New("invalid analyzer result")
	}
	return &result, nil
}

func archiveFirewall(path string) error {
	raw, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	needle := strings.ToLower(string(raw))
	for _, blocked := range []string{"<!entity", "system", "file://", "/flag.txt"} {
		if strings.Contains(needle, blocked) {
			return errors.New("manifest blocked by archive firewall")
		}
	}
	return nil
}

func runXMLParser(path string) (string, error) {
	out, err := exec.Command("xmllint", "--noent", "--recover", path).CombinedOutput()
	if err != nil && len(out) == 0 {
		return "", errors.New("manifest parser failed")
	}
	return strings.TrimSpace(string(out)), nil
}

func analyzerPath() string {
	return filepath.Join(stateDir, "analyzers", "metadata")
}

func allowedArchiveTarget(base string, target string) bool {
	cleanBase := filepath.Clean(base) + string(os.PathSeparator)
	cleanTarget := filepath.Clean(target)
	if strings.HasPrefix(cleanTarget, cleanBase) {
		return true
	}
	return cleanTarget == analyzerPath()
}
