# Trif Language

Trif is a beginner-friendly yet powerful programming language that sits between the worlds of Python and Node.js. It compiles to Python or JavaScript, features a batteries-included standard library, and ships with a local package manager, documentation generator, and REPL.

## Features

- **Simple syntax** inspired by modern scripting languages with explicit function blocks and familiar control-flow.
- **Multiple backends**: transpile to Python for desktop, data, and IPC workloads or to JavaScript for browser and serverless deployments.
- **Standard library** for I/O, networking, threading, and data processing implemented purely with the Python standard library.
- **Concurrency** via the `spawn` statement and thread pool utilities.
- **Package manager** with offline registry and encryption support for shipping desktop builds.
- **Documentation tooling** producing a static site in `docs/build`.
- **Examples** covering desktop, CLI, networking, and web targets.
- **VS Code extension** delivering syntax highlighting and IntelliSense-like completions.

## Getting started

Run the CLI with Python (no external dependencies required):

```bash
python -m trif_lang run examples/hello.trif
```

Enter the REPL:

```bash
python -m trif_lang repl
```

Compile to Python:

```bash
python -m trif_lang compile examples/hello.trif -o build/hello.py
```

Compile to JavaScript (the generated file expects `js_runtime/trif_runtime.mjs` next to it):

```bash
python -m trif_lang compile examples/web/frontend.trif -t javascript -o build/frontend.mjs
```

Encrypt a Python build using a passphrase:

```bash
python -m trif_lang compile examples/chat/server.trif -o build/server.py --encrypt supersecret
```

## Package manager

Initialise a package and publish it to the local registry:

```bash
python -m trif_lang package init my_package
python -m trif_lang package publish my_package
```

Install from the registry:

```bash
python -m trif_lang package install my_package
```

Packages live under `~/.trif/registry` and are installed into `~/.trif/packages`.

## Documentation

Generate the static docs:

```bash
python -m trif_lang docs
```

The output `docs/build/index.html` contains an overview of the language and tooling.

## Examples

- `examples/hello.trif` – basic CLI program.
- `examples/chat/server.trif` & `examples/chat/client.trif` – socket based multi-client chat.
- `examples/web/backend.trif` – desktop-friendly HTTP file server.
- `examples/web/frontend.trif` – frontend code compiled to JavaScript manipulating the DOM.

## VS Code extension

The `vscode-extension` folder contains a simple Visual Studio Code extension that provides syntax highlighting, snippets, and hover tips for Trif files. See the README inside that folder for installation instructions.

## Interoperability

Because Trif compiles to Python or JavaScript, you can call into native modules from either ecosystem. Use the generated Python code to embed Trif logic inside existing Python applications, or the JavaScript output to integrate with Node.js toolchains.

## License

This project is provided for demonstration and educational purposes.
