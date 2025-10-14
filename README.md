# Trif (Teriffic) Language

Trif is a batteries-included programming language that feels like modern JavaScript while executing natively across macOS, Linux, and Windows. The toolchain compiles Trif source to Python or JavaScript, bundles an npm-inspired package manager, exposes an ergonomic CLI, and ships with extensive standard libraries for web, mobile, data, memory tooling, and reverse engineering.

## Installation

### Native C++ toolchain

The new `trifc` compiler is implemented entirely in C++ and no longer depends on
the Python runtime for core compilation. Build it directly with the lightweight
`native/build.sh` script:

```bash
cd native
./build.sh
./build/trifc path/to/file.trif --target cpp
```

This pipeline performs a single optimized compilation step with minimal
overhead, providing noticeably faster iteration than traditional CMake-based
setups. Pass `--target python` or `--target javascript` to emit the legacy
transpilation targets without invoking any Python infrastructure.

### macOS and Linux

```bash
curl -L https://example.com/trif.tar.gz | tar -xz
cd trif-lang
./scripts/install.sh
export PATH="$HOME/.trif/bin:$PATH"
```

The installer copies the toolchain to `~/.trif/toolchain` and creates a `trif` wrapper that launches `python -m trif_lang`. No additional dependencies are required beyond the system Python that ships with macOS and most Linux distributions.

### Windows PowerShell

```powershell
cd trif-lang
.\scripts\install.ps1
$env:PATH = "{0};{1}" -f "$env:USERPROFILE/.trif/bin", $env:PATH
```

Invoke the CLI with `trif.ps1` from any PowerShell session.

## Quick start

```bash
trif create my-app --template web
cd my-app
trif run src/main.trif
```

Install the bundled example package (no network required):

```bash
trif package install hello_console
```

The package manager drops dependencies into `trif_pkg/` so you can immediately import them:

```trif
import hello_console;

export function main() {
    hello_console.main();
}
```

## CLI overview

| Command | Purpose |
| --- | --- |
| `trif compile <file>` | Compile to Python, JavaScript, or bytecode with optional encryption. |
| `trif run <file>` | Compile and execute a program instantly. |
| `trif create <name>` | Scaffold projects for `web`, `mobile`, `memory`, `reverse`, or `lib`. |
| `trif package <...>` | npm-like package manager (init, install, publish, serve, use, list). |
| `trif docs` | Open the handbook located at `docs/index.html`. |
| `trif repl` | Interactive shell for experimentation. |

## Package manager

TrifPM works just like npm, complete with an offline registry and HTTP-compatible server.

```bash
trif package init my-library
trif package install hello_console
trif package publish   # publishes to ~/.trif/registry
trif package serve --port 4873
```

- Packages install into the project-local `trif_pkg/` directory.
- Imports automatically resolve compiled Python modules so `import my-library` works out of the box.
- `trif package use <url>` switches to custom registries, while `trif package offline` prints the bundled registry path for air-gapped environments.

## Standard library highlights

- `std.io` &mdash; Console helpers, JSON utilities, and filesystem access.
- `std.http` &mdash; Express-style router with `createServer`, JSON/HTML helpers, and hot reload friendly design.
- `std.mobile` &mdash; Blueprint mobile experiences and emit PWA-ready bundles.
- `std.memory` &mdash; Manipulate raw buffers for instrumentation or binary patching.
- `std.reverse` &mdash; Inspect ELF and PE binaries, gather section metadata, and generate hexdumps.
- `std.managers` &mdash; Manual managers for tasks, state, resources, events, lifecycles, pipelines, and layered configuration.
- `std.net`, `std.threading`, and `std.data` for networking, concurrency, and structured data.

## Advanced tooling

Trif is equally at home building web APIs, mobile shells, and systems tooling:

```trif
import std.io as io;
import std.memory as memory;
import std.reverse as reverse;

const region = memory.openBuffer(64);
region.write32(0, 0xDEADBEEF);

const binary = reverse.inspectExecutable("./program");
io.println("Format: " + binary.format);
io.println("Sections: " + binary.sections.length);
```

The language runtime hot-loads dependencies from `trif_pkg/`, compiles missing `.trif` files on the fly, and exposes helpers like `runtime.extract_export` for ergonomic module interop.

## Documentation

Generate the full handbook:

```bash
trif docs
```

Open `docs/index.html` to read through the language tour, CLI reference, package manager guide, and standard library documentation. The `trif docs` command will launch it in your default browser when available.

## Examples

- `examples/hello.trif` – zero dependency console application.
- `examples/chat/` – TCP-based chat server and client using `std.net`.
- `examples/web/backend.trif` – HTTP server powered by the new `std.http` module.
- `examples/packages/hello_console/` – offline-installable package demonstrating TrifPM.
- `examples/web/frontend.trif` – JavaScript output targeting modern browsers.

## VS Code extension

The `vscode-extension/` folder provides syntax highlighting, snippets, and inline documentation. See the extension README for installation instructions.

## Interoperability

The native compiler can still emit Python and JavaScript modules when needed.
Use `--target python` for embedding inside existing CPython workflows or
`--target javascript` to generate Node.js-compatible bundles, all powered by the
new C++ backend.

## License

This project is provided for demonstration and educational purposes.
