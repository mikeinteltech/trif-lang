"""Static documentation builder for the Trif language."""
from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Iterable


CLI_COMMANDS = [
    {
        "signature": "trif compile <source>",
        "description": "Compile a Trif file to Python, JavaScript, or bytecode.",
        "details": [
            "Use <code>-t/--target</code> to pick <code>python</code>, <code>javascript</code>, or <code>bytecode</code>.",
            "<code>-o/--output</code> writes the compiled artifact to a custom path.",
            "<code>--encrypt &lt;passphrase&gt;</code> encrypts the generated source with simple XOR obfuscation.",
            "<code>--no-opt</code> disables optimiser passes for easier debugging.",
        ],
    },
    {
        "signature": "trif run <source> [--no-opt] [-- args...]",
        "description": "Compile a file to Python in-memory and execute it immediately.",
        "details": [
            "Arguments after <code>--</code> are forwarded to <code>main()</code> via <code>sys.argv</code>.",
        ],
    },
    {
        "signature": "trif create <name> [--template lib|web|mobile|memory|reverse]",
        "description": "Scaffold a new workspace with batteries-included templates.",
        "details": [
            "Templates configure <code>trif.json</code>, <code>src/main.trif</code>, and any ancillary assets.",
            "Web projects include an Express-style HTTP server; mobile projects emit a manifest + bundle stub.",
        ],
    },
    {
        "signature": "trif docs",
        "description": "Build this handbook at <code>docs/build/index.html</code>.",
    },
    {
        "signature": "trif repl",
        "description": "Interactive shell that compiles lines on the fly. Use <code>:quit</code> to exit.",
    },
]


PACKAGE_COMMANDS = [
    {
        "signature": "trif package init [path]",
        "description": "Create <code>trif.json</code>, <code>src/main.trif</code>, and an empty <code>trif_pkg/</code> folder.",
    },
    {
        "signature": "trif package install &lt;name[@version]&gt;",
        "description": "Install from the active registry (offline or HTTP) into <code>trif_pkg/</code>.",
        "details": [
            "The compiler eagerly transpiles downloaded <code>.trif</code> files to Python for runtime loading.",
            "If the spec begins with <code>file:</code> or points at a path, the package is copied locally with no registry call.",
        ],
    },
    {
        "signature": "trif package install-local &lt;path&gt;",
        "description": "Shorthand for installing a package from a directory without hitting the registry.",
    },
    {
        "signature": "trif package publish [path]",
        "description": "Bundle the package and push it to <code>~/.trif/registry</code> for sharing.",
        "details": [
            "Creates a <code>package.zip</code> plus metadata entry in <code>index.json</code>.",
        ],
    },
    {
        "signature": "trif package list",
        "description": "Print installed packages and versions discovered in <code>trif_pkg/</code>.",
    },
    {
        "signature": "trif package use &lt;url&gt;",
        "description": "Switch the active registry endpoint (file://, http://, https:// supported).",
    },
    {
        "signature": "trif package serve [--port 4873] [--directory &lt;path&gt;]",
        "description": "Serve a registry directory over HTTP for npm-style workflows.",
    },
    {
        "signature": "trif package offline",
        "description": "Print the bundled offline registry path (ships with <code>hello_console</code>).",
    },
]


LANGUAGE_SECTIONS = [
    {
        "title": "Syntax essentials",
        "items": [
            "<code>let</code> declares mutable bindings, <code>const</code> declares immutable ones.",
            "Functions use <code>function name(param, ...)</code> blocks with braces and <code>return</code>.",
            "Numbers, strings, booleans, <code>null</code>, lists <code>[...]</code>, and object literals <code>{ key: value }</code> mirror JavaScript.",
            "<code>if</code>, <code>while</code>, and <code>for (let item in list)</code> match familiar syntax.",
            "<code>spawn</code> executes a call asynchronously using the runtime thread helpers.",
        ],
        "example": """let counter = 0;\nconst banner = \"Ready\";\n\nfunction tick(step) {\n    counter = counter + step;\n    return counter;\n}\n""",
    },
    {
        "title": "Modules & exports",
        "items": [
            "Import entire modules with <code>import std.io as io;</code> or <code>import \"./util.trif\";</code>.",
            "Use ES modules style: <code>import main, { helper as alias } from \"./helpers\";</code>.",
            "<code>export function</code> and <code>export let</code> expose named bindings; <code>export default</code> publishes a single default value.",
            "Re-export modules with <code>export { name } from \"./other\";</code> or <code>export * from \"./shared\";</code>.",
        ],
        "example": """import std.io as io;\nimport logger, { formatTime } from \"./time\";\n\nexport function main() {\n    io.println(formatTime(logger.now()));\n}\n""",
    },
    {
        "title": "Control flow & patterns",
        "items": [
            "Pattern match with chained <code>if/else</code> or guard loops using <code>while</code>.",
            "<code>for (let item in collection)</code> iterates arrays, lists, and runtime-provided iterables.",
            "Use destructuring-style assignments via <code>let</code> with object accessors: <code>let host = config.host;</code>.",
            "Throw and catch Python exceptions via compiled output; integrate with <code>std.managers.ResourceManager</code> for cleanup.",
        ],
    },
]


STD_LIBRARY = {
    "std.io": [
        {"signature": "println(value: Any) -> None", "description": "Print a value to stdout immediately."},
        {"signature": "read_text(path: str) -> str", "description": "Read a UTF-8 file into memory."},
        {"signature": "write_text(path: str, data: str) -> None", "description": "Write a UTF-8 file, creating parents as needed."},
        {"signature": "read_json(path: str) -> Any", "description": "Parse JSON from disk using <code>read_text</code>."},
        {"signature": "write_json(path: str, data: Any) -> None", "description": "Pretty-print JSON to disk."},
        {"signature": "prompt(message: str) -> str", "description": "Request console input from the user."},
    ],
    "std.net": [
        {"signature": "start_tcp_server(host: str, port: int, handler) -> None", "description": "Spawn a threaded TCP server invoking <code>handler(client, address)</code> for each connection."},
        {"signature": "send_tcp_message(host: str, port: int, message: str) -> None", "description": "Connect and send a UTF-8 message."},
        {"signature": "broadcast_json(host: str, port: int, payload: Any) -> None", "description": "Serialize JSON and deliver it via TCP."},
    ],
    "std.data": [
        {"signature": "load_csv(path: str) -> List[Dict[str, str]]", "description": "Read CSV rows into dictionaries."},
        {"signature": "save_csv(path: str, rows: Iterable[Dict[str, Any]]) -> None", "description": "Persist dictionaries as CSV with headers."},
        {"signature": "filter_rows(rows, predicate) -> List[Dict[str, Any]]", "description": "Return rows where <code>predicate(row)</code> is truthy."},
        {"signature": "map_rows(rows, mapper) -> List[Dict[str, Any]]", "description": "Transform rows with <code>mapper</code>."},
        {"signature": "to_json(data: Any) -> str", "description": "Pretty-print arbitrary data to JSON."},
    ],
    "std.threading": [
        {"signature": "spawn(fn: () -> Any) -> None", "description": "Schedule <code>fn</code> on the shared thread pool."},
        {"signature": "parallel_map(fn, items: list[Any]) -> list[Any]", "description": "Map concurrently using worker threads."},
        {"signature": "sleep(seconds: float) -> None", "description": "Block the current thread for a duration."},
    ],
    "std.http": [
        {
            "signature": "class HttpServer(host: str = '0.0.0.0', port: int = 5000)",
            "description": "Express-style HTTP server with a built-in router.",
            "details": [
                "<code>get/post/put/delete(path, handler)</code> register route handlers receiving <code>HttpContext</code>.",
                "<code>listen()</code> boots a background server thread; <code>close()</code> shuts it down gracefully.",
            ],
        },
        {
            "signature": "class HttpContext",
            "description": "Wrapper around the request with helpers for crafting responses.",
            "details": [
                "<code>text(value, status=200)</code>, <code>html(markup)</code>, and <code>json(payload)</code> return <code>HttpResponse</code>.",
                "<code>send(body, status=200, content_type)</code> streams arbitrary bytes.",
            ],
        },
        {"signature": "createServer(config?) -> HttpServer", "description": "Factory that respects <code>host</code> and <code>port</code> keys."},
        {"signature": "now() -> str", "description": "Utility returning the current timestamp (ISO 8601)."},
        {"signature": "class HttpResponse", "description": "Lightweight data class storing status, headers, and body."},
    ],
    "std.mobile": [
        {
            "signature": "createApp(config?) -> MobileApp",
            "description": "Prepare a PWA-oriented mobile app container with title/metadata settings.",
        },
        {
            "signature": "class MobileApp",
            "description": "Collect screens and export a structured bundle.",
            "details": [
                "<code>screen(name, builder)</code> registers screens via a callback receiving <code>MobileScreen</code>.",
                "<code>export()</code> returns the manifest consumed by <code>mobile.build</code>.",
            ],
        },
        {
            "signature": "class MobileScreen",
            "description": "Builder surface for composing UI primitives.",
            "details": [
                "<code>header(text)</code>, <code>text(body)</code>, <code>button(label, action)</code> push declarative components.",
            ],
        },
        {
            "signature": "build(app, options?) -> Path",
            "description": "Emit <code>bundle.json</code> with metadata, screen definitions, and platform target (default <code>pwa</code>).",
        },
    ],
    "std.memory": [
        {"signature": "openBuffer(size: int) -> MemoryRegion", "description": "Allocate a zero-filled buffer for manual reads/writes."},
        {
            "signature": "class MemoryRegion",
            "description": "Perform typed reads and writes on a mutable buffer.",
            "details": [
                "<code>write32(offset, value)</code> / <code>read32(offset)</code> access 32-bit unsigned integers.",
                "<code>write_bytes(offset, data)</code> and <code>read_bytes(offset, length)</code> move arbitrary slices.",
                "<code>fill(value)</code> initialises all bytes; <code>search(pattern)</code> finds sub-sequences.",
                "<code>to_bytes()</code> exports the raw data as immutable bytes." ,
            ],
        },
        {"signature": "formatHex(value: int, width: int = 8) -> str", "description": "Render values as zero-padded hexadecimal strings."},
    ],
    "std.reverse": [
        {"signature": "inspectExecutable(path: str) -> ExecutableInfo", "description": "Detect ELF/PE binaries and extract section metadata."},
        {"signature": "hexdump(data: bytes, width: int = 16) -> str", "description": "Produce a traditional hex + ASCII dump."},
        {
            "signature": "class ExecutableInfo",
            "description": "Data class exposing <code>path</code>, <code>format</code>, and <code>sections</code> list.",
        },
    ],
    "std.managers": [
        {
            "signature": "class TaskManager",
            "description": "Register named callables and execute them sequentially.",
            "details": [
                "<code>add(name, fn)</code> queues a unit of work.",
                "<code>run_all(context=None)</code> executes tasks and returns <code>{ task, result }</code> dictionaries.",
            ],
        },
        {
            "signature": "class StateManager",
            "description": "Mutable state container with history tracking.",
            "details": [
                "<code>update(**changes)</code> merges new values and records snapshots.",
                "<code>undo()</code> restores the previous snapshot if available.",
            ],
        },
        {
            "signature": "class ResourceManager",
            "description": "Pair manual resource acquisition/release callbacks.",
            "details": [
                "<code>manage(enter, exit)</code> registers complementary handlers.",
                "<code>execute(action)</code> opens resources, runs <code>action(resources)</code>, and then unwinds safely.",
            ],
        },
        {
            "signature": "class EventManager",
            "description": "Publish/subscribe hub with explicit handler management.",
            "details": [
                "<code>on(event, handler)</code>, <code>off(event, handler?)</code>, and <code>clear()</code> govern listeners.",
                "<code>emit(event, payload)</code> invokes handlers and returns collected results.",
            ],
        },
        {
            "signature": "class LifecycleManager",
            "description": "Coordinate ordered lifecycle phases (start, ready, stop, etc.).",
            "details": [
                "<code>hook(phase, handler)</code> registers callbacks.",
                "<code>run(phase)</code> executes handlers and returns their results; <code>phases()</code> enumerates registered phases.",
            ],
        },
        {
            "signature": "class ResourcePool",
            "description": "Manage expensive resources (e.g., connections) with manual pooling.",
            "details": [
                "<code>acquire()</code> returns a resource from the pool or constructs a new one until <code>max_size</code> is reached.",
                "<code>release(resource)</code> returns it to the idle queue; <code>drain()</code> disposes of all resources via the destroy callback.",
            ],
        },
        {
            "signature": "class PipelineManager",
            "description": "Compose ordered transformation steps that can be run on demand.",
            "details": [
                "<code>step(handler)</code> appends a stage.",
                "<code>run(payload)</code> flows a value through all registered stages; <code>clear()</code> removes stages.",
            ],
        },
        {
            "signature": "class ConfigurationManager",
            "description": "Layer configuration dictionaries with manual overrides.",
            "details": [
                "<code>push(overrides)</code> / <code>pop()</code> manage the stack of config layers.",
                "<code>get(key, default)</code> resolves values from highest-priority layer to lowest; <code>merged()</code> returns the merged view.",
            ],
        },
    ],
}


RUNTIME_APIS = [
    {
        "signature": "Runtime.import_module(name: str) -> ModuleProxy",
        "description": "Resolve stdlib modules, compiled Python artefacts, or on-demand <code>.trif</code> modules under <code>trif_pkg/</code>.",
    },
    {
        "signature": "Runtime.execute_python(code: str, argv: list[str] | None = None) -> None",
        "description": "Execute compiled Python code inside a sandboxed module and run <code>main()</code> or the default export.",
    },
    {
        "signature": "Runtime.spawn(callable) -> None",
        "description": "Launch a daemon thread executing <code>callable</code> (used by the <code>spawn</code> statement).",
    },
    {
        "signature": "Runtime.register_module_exports(name, exports, default) -> None",
        "description": "Expose explicit export tables to the module proxy system for interop.",
    },
    {
        "signature": "Runtime.extract_export(proxy, name) -> Any",
        "description": "Retrieve a named export from a module proxy (used internally by compiled code).",
    },
    {
        "signature": "Runtime.extract_default(proxy) -> Any",
        "description": "Return the default export if supplied, otherwise the wrapped module object.",
    },
    {
        "signature": "Runtime.prepare_project_environment(root: Path) -> None",
        "description": "Add project roots and <code>trif_pkg/</code> directories to <code>sys.path</code> for module discovery.",
    },
    {
        "signature": "ModuleProxy.get_export(name) -> Any",
        "description": "Lookup helper exposed to user-land for dynamic module inspection.",
    },
]


def _unordered(items: Iterable[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _render_table(rows: Iterable[dict[str, object]]) -> str:
    body = []
    for row in rows:
        signature = escape(str(row["signature"]))
        description = row.get("description", "")
        details = row.get("details")
        if details:
            description = f"{description}{_unordered(details)}"
        body.append(f"<tr><td><code>{signature}</code></td><td>{description}</td></tr>")
    return "<table><thead><tr><th>API</th><th>Description</th></tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def _render_language_sections() -> str:
    parts: list[str] = []
    for section in LANGUAGE_SECTIONS:
        parts.append(f"<h3>{section['title']}</h3>")
        parts.append(_unordered(section["items"]))
        example = section.get("example")
        if example:
            parts.append("<pre><code>" + escape(example) + "</code></pre>")
    return "\n".join(parts)


def _render_stdlib() -> str:
    parts: list[str] = []
    for module, entries in STD_LIBRARY.items():
        parts.append(f"<h3><code>{module}</code></h3>")
        parts.append(_render_table(entries))
    return "\n".join(parts)


def _render_runtime() -> str:
    return _render_table(RUNTIME_APIS)


def build_docs() -> Path:
    docs_root = Path("docs/build")
    docs_root.mkdir(parents=True, exist_ok=True)
    index = docs_root / "index.html"
    html = f"""
<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <title>Trif Language Handbook</title>
    <style>
      body {{ font-family: 'Segoe UI', system-ui, sans-serif; max-width: 1100px; margin: auto; padding: 2rem; line-height: 1.7; }}
      pre {{ background: #0f172a; color: #e2e8f0; padding: 1rem; overflow-x: auto; border-radius: 8px; }}
      code {{ background: #e2e8f0; padding: 0.2rem 0.4rem; border-radius: 4px; }}
      nav {{ margin-bottom: 2rem; display: flex; flex-wrap: wrap; gap: 1rem; }}
      nav a {{ text-decoration: none; color: #2563eb; font-weight: 600; }}
      table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }}
      th, td {{ border: 1px solid #cbd5f5; padding: 0.6rem; text-align: left; vertical-align: top; }}
      h1, h2, h3 {{ color: #0f172a; }}
      section {{ margin-bottom: 3rem; }}
    </style>
  </head>
  <body>
    <h1>Trif Language Handbook</h1>
    <p>Trif delivers a JavaScript-inspired developer experience with native deployment targets and no runtime dependencies
    beyond the toolchain itself. Use this handbook as an exhaustive reference for the language syntax, CLI, package manager,
    runtime, and standard library modules.</p>
    <nav>
      <a href=\"#getting-started\">Getting started</a>
      <a href=\"#language\">Language guide</a>
      <a href=\"#cli\">CLI reference</a>
      <a href=\"#packages\">Package manager</a>
      <a href=\"#stdlib\">Standard library</a>
      <a href=\"#runtime\">Runtime API</a>
      <a href=\"#tooling\">Tooling & workflows</a>
    </nav>

    <section id=\"getting-started\">
      <h2>Getting started</h2>
      <ol>
        <li>Install Trif with the platform script in <code>README.md</code> (macOS/Linux shell or Windows PowerShell).</li>
        <li>Run <code>trif create my-app --template web</code> to scaffold a project.</li>
        <li>Start developing with <code>trif run src/main.trif</code> or <code>trif compile src/main.trif -t javascript</code>.</li>
      </ol>
      <pre><code>{escape('import std.http as http;\nimport std.io as io;\n\nconst server = http.createServer({ port: 8080 });\n\nserver.get("/", function(ctx) {\n    return ctx.json({ status: "ok", at: http.now() });\n});\n\nexport function main() {\n    io.println("API ready on http://localhost:8080");\n    server.listen();\n}\n')}</code></pre>
    </section>

    <section id=\"language\">
      <h2>Language guide</h2>
      {_render_language_sections()}
    </section>

    <section id=\"cli\">
      <h2>CLI reference</h2>
      <p>The <code>trif</code> executable bundles compilation, project scaffolding, documentation, and an interactive REPL.</p>
      {_render_table(CLI_COMMANDS)}
    </section>

    <section id=\"packages\">
      <h2>Package manager</h2>
      <p>TrifPM mirrors npm conventions while keeping dependencies inside <code>trif_pkg/</code>. Registries can be served
      over HTTP, selected per-project, or used completely offline via the bundled index.</p>
      {_render_table(PACKAGE_COMMANDS)}
      <p>Example workflow:</p>
      <pre><code>{escape('trif package init my-lib\ncd my-lib\ntrif package install hello_console\ntrif package publish\ntrif package serve --port 4873')}</code></pre>
    </section>

    <section id=\"stdlib\">
      <h2>Standard library</h2>
      <p>Every module ships with the toolchain and is available without additional installation. Imports resolve immediately
      after running <code>trif package install</code> for third-party dependencies.</p>
      {_render_stdlib()}
    </section>

    <section id=\"runtime\">
      <h2>Runtime API</h2>
      <p>The Python runtime powers execution across macOS, Linux, and Windows. These helpers are available to advanced users
      embedding Trif into other environments or authoring custom tooling.</p>
      {_render_runtime()}
    </section>

    <section id=\"tooling\">
      <h2>Tooling & workflows</h2>
      <ul>
        <li><strong>Mobile development:</strong> Use <code>std.mobile</code> to design screens and emit <code>bundle.json</code> for PWAs or hybrid shells.</li>
        <li><strong>Web development:</strong> <code>std.http</code> delivers router-style APIs; compile to JavaScript with <code>trif compile -t javascript</code> for front-end builds.</li>
        <li><strong>Memory tooling:</strong> <code>std.memory</code> and <code>std.reverse</code> expose buffer manipulation plus ELF/PE inspection.</li>
        <li><strong>Reverse engineering:</strong> Combine <code>inspectExecutable</code>, <code>hexdump</code>, and the manual managers to orchestrate complex pipelines.</li>
        <li><strong>Interop:</strong> Target native Python by default or emit JavaScript bundles for Node.js and browsers without requiring separate runtimes.</li>
        <li><strong>Examples:</strong> Explore the <code>examples/</code> directory for ready-to-run templates, including the offline-installable <code>hello_console</code> package.</li>
      </ul>
    </section>
  </body>
</html>
"""
    index.write_text(html, encoding="utf-8")
    return index


__all__ = ["build_docs"]

