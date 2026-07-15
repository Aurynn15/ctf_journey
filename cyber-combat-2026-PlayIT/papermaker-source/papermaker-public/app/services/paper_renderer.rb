require "fileutils"
require "open3"
require "digest"
require "timeout"

class PaperRenderer
  Result = Struct.new(:success?, :id, :error, :output, :cached?, keyword_init: true)

  def initialize(source, user_id)
    @source = source.to_s
    @user_id = user_id
    @id = "#{user_id}_#{::Digest::SHA256.hexdigest(@source)}"
  end

  def render
    return Result.new(success?: false, error: "Invalid Input!", output: "") if _blocked?
    return Result.new(success?: true, id: @id, output: "Cached result used.", cached?: true) if _cached?

    ::FileUtils.mkdir_p(_workdir)
    ::File.write(_tex_path, _document)

    output = _compile
    ::File.file?(_pdf_path) ?
      Result.new(success?: true, id: @id, output: output, cached?: false) :
      Result.new(success?: false, error: "LaTeX compilation failed", output: output)
  rescue ::Timeout::Error
    Result.new(success?: false, error: "LaTeX compilation timed out", output: "")
  rescue ::StandardError => e
    Result.new(success?: false, error: e.message, output: "")
  end

  private

  def _blocked?
    _a = %w[close open new]
    _b = %w[in out put]
    _combo = _a.product(_b).map { |x, y| x + y }
    _tail = %w[| ^^ csname endcsname expandafter immediate includegraphics
               verbatiminput url href \\input file write18 outfile fileline]
    deny = (_combo + _tail).uniq
    
    hay = @source.downcase
    deny.any? { |token| hay[token.downcase] }
  end

  def _cached?
    ::File.file?(_pdf_path)
  end

  def _document
    return @source if @source.match?(/\\documentclass\b/)

    [
      "\\documentclass{article}",
      "\\pdfcompresslevel=0",
      "\\pdfobjcompresslevel=0",
      "\\begin{document}",
      @source,
      "\\end{document}"
    ].join("\n")
  end

  def _compile
    env = {
      "openin_any" => "p",
      "openout_any" => "p",
      "TEXMFOUTPUT" => _workdir.to_s
    }

    cmd = [
      "pdflatex",
      "-halt-on-error",
      "-interaction=nonstopmode",
      "-no-shell-escape",
      "-output-directory=#{_workdir}",
      _tex_path.to_s
    ]

    ::Timeout.timeout(8) do
      _stdout, stderr, status = ::Open3.capture3(env, *cmd, chdir: ::Rails.root.to_s)
      log = ::File.file?(_log_path) ? ::File.binread(_log_path).scrub : ""
      [stderr, log, "exit status: #{status.exitstatus}"].reject { |s| s.to_s.empty? }.join("\n")
    end
  end

  def _workdir
    @_workdir ||= ::Rails.root.join("tmp", "latex", @user_id.to_s, @id)
  end

  def _tex_path;  _workdir.join("document.tex"); end
  def _pdf_path;  _workdir.join("document.pdf"); end
  def _log_path;  _workdir.join("document.log"); end
end