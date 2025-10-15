"""Interactive experiences for the Trif language.

This module powers both the desktop GUI and the web-based editor.  The goal is
to keep Trif approachable without sacrificing performance, so both front-ends
compile code using the existing :class:`~trif_lang.toolchain.Toolchain` and run
programs through :class:`~trif_lang.runtime.Runtime` just like the command line
utilities do.
"""

from __future__ import annotations

import io
import json
import threading
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterable, Optional

from .toolchain import Toolchain


@dataclass
class ExecutionOutcome:
    """Result of running a snippet of Trif source code."""

    ok: bool
    stdout: str
    stderr: str
    duration: float


class InteractiveEngine:
    """Shared utilities for interactive Trif experiences."""

    def __init__(self, toolchain: Toolchain) -> None:
        self.toolchain = toolchain

    # ------------------------------------------------------------------
    # Compilation helpers
    def compile(self, source: str, target: str = "python", *, optimize: bool = True) -> str:
        code = self.toolchain.compiler.compile_source(source, target=target, optimize=optimize)
        if isinstance(code, bytes):  # Only happens for bytecode which we don't surface here
            return code.decode("utf-8", errors="replace")
        return code

    # ------------------------------------------------------------------
    # Execution helpers
    def run(self, source: str, *, optimize: bool = True, argv: Optional[Iterable[str]] = None) -> ExecutionOutcome:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        start = time.perf_counter()
        ok = True
        try:
            python_code = self.toolchain.compiler.compile_source(source, target="python", optimize=optimize)
            assert isinstance(python_code, str)
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                self.toolchain.runtime.execute_python(python_code, argv=list(argv or []))
        except Exception:  # noqa: BLE001 - Surface the traceback to users.
            ok = False
            traceback.print_exc(file=stderr_buffer)
        duration = time.perf_counter() - start
        return ExecutionOutcome(
            ok=ok,
            stdout=stdout_buffer.getvalue(),
            stderr=stderr_buffer.getvalue(),
            duration=duration,
        )


# ---------------------------------------------------------------------------
# Desktop GUI ---------------------------------------------------------------


def launch_desktop_gui(
    toolchain: Toolchain,
    *,
    path: Optional[Path] = None,
    optimize: bool = True,
) -> None:
    """Start the Tkinter-based Trif desktop editor."""

    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
    except Exception as exc:  # noqa: BLE001 - propagate friendly error
        raise SystemExit(
            "Tkinter is required for the Trif GUI. Install a Python build "
            f"with Tk support ({exc})."
        ) from exc

    engine = InteractiveEngine(toolchain)

    root = tk.Tk()
    root.title("Trif Studio")
    root.geometry("1100x720")

    # Configure layout
    root.columnconfigure(0, weight=3)
    root.columnconfigure(1, weight=2)
    root.rowconfigure(1, weight=1)

    header = ttk.Frame(root, padding=(12, 8))
    header.grid(row=0, column=0, columnspan=2, sticky="nsew")

    title_label = ttk.Label(header, text="Trif Studio", font=("Segoe UI", 16, "bold"))
    title_label.pack(side=tk.LEFT)

    status_var = tk.StringVar(value="Ready")
    status_label = ttk.Label(header, textvariable=status_var, anchor="e")
    status_label.pack(side=tk.RIGHT)

    body = ttk.Panedwindow(root, orient=tk.HORIZONTAL)
    body.grid(row=1, column=0, columnspan=2, sticky="nsew")

    editor_container = ttk.Frame(body, padding=8)
    editor_container.columnconfigure(0, weight=1)
    editor_container.rowconfigure(0, weight=1)
    body.add(editor_container, weight=3)

    output_container = ttk.Frame(body, padding=8)
    output_container.columnconfigure(0, weight=1)
    output_container.rowconfigure(0, weight=1)
    body.add(output_container, weight=2)

    editor = tk.Text(editor_container, wrap="none", undo=True, font=("Fira Code", 11))
    editor.grid(row=0, column=0, sticky="nsew")

    x_scroll = ttk.Scrollbar(editor_container, orient="horizontal", command=editor.xview)
    x_scroll.grid(row=1, column=0, sticky="ew")
    y_scroll = ttk.Scrollbar(editor_container, orient="vertical", command=editor.yview)
    y_scroll.grid(row=0, column=1, sticky="ns")
    editor.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)

    output = tk.Text(output_container, wrap="word", state="disabled", font=("Consolas", 11))
    output.grid(row=0, column=0, sticky="nsew")

    output_scroll = ttk.Scrollbar(output_container, orient="vertical", command=output.yview)
    output_scroll.grid(row=0, column=1, sticky="ns")
    output.configure(yscrollcommand=output_scroll.set)

    button_bar = ttk.Frame(header)
    button_bar.pack(side=tk.RIGHT, padx=(16, 0))

    running_lock = threading.Lock()

    def set_output(text: str) -> None:
        output.configure(state="normal")
        output.delete("1.0", tk.END)
        output.insert(tk.END, text)
        output.configure(state="disabled")

    def run_source() -> None:
        if not running_lock.acquire(blocking=False):
            return

        status_var.set("Running...")
        source = editor.get("1.0", tk.END)

        def worker() -> None:
            try:
                result = engine.run(source, optimize=optimize)
                summary = [
                    f"Completed in {result.duration * 1000:.1f} ms",
                    "",
                ]
                if result.stdout:
                    summary.append(result.stdout.rstrip())
                if result.stderr:
                    if result.stdout:
                        summary.append("\n")
                    summary.append(result.stderr.rstrip())
                text = "\n".join(summary).strip()
                if not text:
                    text = "Program finished with no output."
                root.after(0, lambda: set_output(text))
                root.after(0, lambda: status_var.set("Success" if result.ok else "Errors encountered"))
            finally:
                running_lock.release()

        threading.Thread(target=worker, daemon=True).start()

    def compile_to_python() -> None:
        source = editor.get("1.0", tk.END)
        try:
            code = engine.compile(source, target="python", optimize=optimize)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Compilation error", str(exc))
            return
        set_output(code)
        status_var.set("Generated Python")

    def compile_to_js() -> None:
        source = editor.get("1.0", tk.END)
        try:
            code = engine.compile(source, target="javascript", optimize=optimize)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Compilation error", str(exc))
            return
        set_output(code)
        status_var.set("Generated JavaScript")

    def new_document() -> None:
        editor.delete("1.0", tk.END)
        editor.insert(
            "1.0",
            "import std.io as io;\n\nexport function main() {\n    io.println(\"Hello from Trif Studio!\");\n}\n",
        )
        status_var.set("Ready")

    current_path: Optional[Path] = None

    def open_file() -> None:
        nonlocal current_path
        filename = filedialog.askopenfilename(
            filetypes=[("Trif files", "*.trif"), ("All files", "*.*")],
            initialdir=path.parent if path else toolchain.project_root,
        )
        if not filename:
            return
        file_path = Path(filename)
        editor.delete("1.0", tk.END)
        editor.insert("1.0", file_path.read_text(encoding="utf-8"))
        current_path = file_path
        status_var.set(f"Opened {file_path.name}")

    def save_file() -> None:
        nonlocal current_path
        if current_path is None:
            filename = filedialog.asksaveasfilename(
                defaultextension=".trif",
                filetypes=[("Trif files", "*.trif"), ("All files", "*.*")],
                initialdir=toolchain.project_root,
            )
            if not filename:
                return
            current_path = Path(filename)
        current_path.write_text(editor.get("1.0", tk.END), encoding="utf-8")
        status_var.set(f"Saved {current_path.name}")

    ttk.Button(button_bar, text="Run", command=run_source).pack(side=tk.LEFT, padx=4)
    ttk.Button(button_bar, text="Compile → Python", command=compile_to_python).pack(side=tk.LEFT, padx=4)
    ttk.Button(button_bar, text="Compile → JS", command=compile_to_js).pack(side=tk.LEFT, padx=4)

    menu = tk.Menu(root)
    file_menu = tk.Menu(menu, tearoff=False)
    file_menu.add_command(label="New", command=new_document)
    file_menu.add_command(label="Open…", command=open_file)
    file_menu.add_command(label="Save", command=save_file)
    menu.add_cascade(label="File", menu=file_menu)
    root.config(menu=menu)

    new_document()

    if path and path.exists():
        editor.delete("1.0", tk.END)
        editor.insert("1.0", path.read_text(encoding="utf-8"))
        current_path = path.resolve()
        status_var.set(f"Opened {path.name}")

    root.mainloop()


# ---------------------------------------------------------------------------
# Web editor ----------------------------------------------------------------


class _WebEditorHandler(BaseHTTPRequestHandler):
    """Request handler for the bundled web editor."""

    engine: InteractiveEngine
    optimize: bool

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path in {"/", "/index.html"}:
            self._send_html(_WEB_EDITOR_HTML)
            return
        if self.path == "/health":
            self._send_json({"status": "ok"})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON payload"}, status=HTTPStatus.BAD_REQUEST)
            return

        if self.path == "/api/run":
            source = data.get("source", "")
            argv = data.get("argv") or []
            result = self.engine.run(source, optimize=self.optimize, argv=argv)
            self._send_json(
                {
                    "ok": result.ok,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "duration_ms": round(result.duration * 1000, 2),
                }
            )
            return

        if self.path == "/api/compile":
            source = data.get("source", "")
            target = data.get("target", "python")
            try:
                code = self.engine.compile(source, target=target, optimize=self.optimize)
            except Exception:  # noqa: BLE001
                self._send_json(
                    {
                        "ok": False,
                        "error": traceback.format_exc(),
                    },
                    status=HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return
            self._send_json({"ok": True, "code": code})
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    # ------------------------------------------------------------------
    def _send_html(self, body: str, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def launch_web_editor(
    toolchain: Toolchain,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    optimize: bool = True,
    open_browser: bool = True,
) -> None:
    """Start the lightweight Trif web editor."""

    engine = InteractiveEngine(toolchain)

    class Handler(_WebEditorHandler):
        pass

    Handler.engine = engine  # type: ignore[attr-defined]
    Handler.optimize = optimize  # type: ignore[attr-defined]

    server = ThreadingHTTPServer((host, port), Handler)

    url = f"http://{host}:{port}"
    print(f"Trif web editor available at {url}")

    if open_browser:
        import webbrowser

        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Stopping web editor")
    finally:
        server.server_close()


_WEB_EDITOR_HTML = """<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>Trif Studio (Web)</title>
    <style>
      :root {
        color-scheme: light dark;
        --bg: #0f172a;
        --panel: rgba(15, 23, 42, 0.9);
        --fg: #e2e8f0;
        --accent: #38bdf8;
        --accent-dark: #0ea5e9;
        --mono: 'Fira Code', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
        --sans: 'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif;
      }
      body {
        margin: 0;
        font-family: var(--sans);
        background: linear-gradient(160deg, #020617 0%, #1e293b 100%);
        color: var(--fg);
        min-height: 100vh;
        display: flex;
        flex-direction: column;
      }
      header {
        padding: 1.2rem 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(15, 23, 42, 0.85);
        backdrop-filter: blur(12px);
        border-bottom: 1px solid rgba(148, 163, 184, 0.2);
      }
      header h1 {
        margin: 0;
        font-size: 1.5rem;
        font-weight: 700;
      }
      header .status {
        font-size: 0.9rem;
        color: rgba(226, 232, 240, 0.75);
      }
      main {
        flex: 1;
        display: grid;
        grid-template-columns: 1fr minmax(320px, 30%);
        gap: 1.2rem;
        padding: 1.2rem 2rem 2rem;
      }
      textarea {
        width: 100%;
        height: 100%;
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background: rgba(15, 23, 42, 0.65);
        color: var(--fg);
        padding: 1.2rem;
        font-family: var(--mono);
        font-size: 0.95rem;
        resize: none;
        box-shadow: inset 0 0 30px rgba(2, 6, 23, 0.35);
      }
      textarea:focus {
        outline: 2px solid var(--accent);
        border-color: transparent;
      }
      .panel {
        background: rgba(15, 23, 42, 0.78);
        border-radius: 16px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        padding: 1.2rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.35);
      }
      .panel button {
        appearance: none;
        border: none;
        padding: 0.8rem 1rem;
        border-radius: 999px;
        background: linear-gradient(135deg, var(--accent), var(--accent-dark));
        color: #0f172a;
        font-weight: 600;
        font-size: 0.95rem;
        cursor: pointer;
        transition: transform 0.1s ease, box-shadow 0.2s ease;
        box-shadow: 0 10px 25px rgba(14, 165, 233, 0.35);
      }
      .panel button.secondary {
        background: rgba(148, 163, 184, 0.15);
        color: var(--fg);
        box-shadow: none;
      }
      .panel button:hover {
        transform: translateY(-1px);
        box-shadow: 0 16px 32px rgba(56, 189, 248, 0.35);
      }
      .panel pre {
        margin: 0;
        font-family: var(--mono);
        font-size: 0.9rem;
        padding: 1rem;
        background: rgba(2, 6, 23, 0.55);
        border-radius: 12px;
        overflow: auto;
        max-height: 50vh;
      }
      .panel label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: rgba(226, 232, 240, 0.7);
      }
      .panel select {
        padding: 0.6rem 0.75rem;
        border-radius: 12px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        background: rgba(15, 23, 42, 0.6);
        color: var(--fg);
        font-weight: 500;
      }
      footer {
        padding: 0.75rem 2rem 1.5rem;
        font-size: 0.85rem;
        color: rgba(226, 232, 240, 0.65);
        text-align: center;
      }
      @media (max-width: 960px) {
        main {
          grid-template-columns: 1fr;
        }
        .panel {
          max-height: 60vh;
        }
      }
    </style>
  </head>
  <body>
    <header>
      <h1>Trif Studio</h1>
      <div class=\"status\" id=\"status\">Ready</div>
    </header>
    <main>
      <textarea id=\"source\" spellcheck=\"false\">import std.io as io;

export function main() {
    io.println("Hello from Trif Studio (web)!");
}
</textarea>
      <aside class=\"panel\">
        <div>
          <label for=\"compile-target\">Compile target</label>
          <select id=\"compile-target\">
            <option value=\"python\">Python</option>
            <option value=\"javascript\">JavaScript</option>
          </select>
        </div>
        <button id=\"run-button\">Run program</button>
        <button class=\"secondary\" id=\"compile-button\">Compile</button>
        <pre id=\"output\">// Output will appear here.</pre>
      </aside>
    </main>
    <footer>
      Trif Studio keeps everything local – no code ever leaves your machine.
    </footer>
    <script>
      const status = document.getElementById('status');
      const output = document.getElementById('output');
      const source = document.getElementById('source');
      const runButton = document.getElementById('run-button');
      const compileButton = document.getElementById('compile-button');
      const targetSelect = document.getElementById('compile-target');

      async function postJSON(url, payload) {
        const response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) {
          throw new Error(data.error || 'Unexpected error');
        }
        return data;
      }

      runButton.addEventListener('click', async () => {
        const code = source.value;
        status.textContent = 'Running…';
        runButton.disabled = true;
        compileButton.disabled = true;
        try {
          const result = await postJSON('/api/run', { source: code });
          let message = `⏱  ${result.duration_ms.toFixed(2)} ms`;
          if (result.stdout) {
            message += `\n\n${result.stdout}`;
          }
          if (result.stderr) {
            message += `\n\n⚠️ ${result.stderr}`;
          }
          output.textContent = message;
          status.textContent = result.ok ? 'Finished' : 'Errors occurred';
        } catch (error) {
          output.textContent = error.message;
          status.textContent = 'Failed';
        } finally {
          runButton.disabled = false;
          compileButton.disabled = false;
        }
      });

      compileButton.addEventListener('click', async () => {
        const code = source.value;
        const target = targetSelect.value;
        status.textContent = `Compiling to ${target}…`;
        runButton.disabled = true;
        compileButton.disabled = true;
        try {
          const result = await postJSON('/api/compile', { source: code, target });
          output.textContent = result.code;
          status.textContent = 'Compiled';
        } catch (error) {
          output.textContent = error.message;
          status.textContent = 'Failed';
        } finally {
          runButton.disabled = false;
          compileButton.disabled = false;
        }
      });
    </script>
  </body>
</html>
"""


__all__ = [
    "ExecutionOutcome",
    "InteractiveEngine",
    "launch_desktop_gui",
    "launch_web_editor",
]

