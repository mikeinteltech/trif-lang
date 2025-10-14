"""Command line interface for the Trif language toolchain."""
from __future__ import annotations

import argparse
import http.server
import json
import os
import socketserver
import sys
import textwrap
from functools import partial
from pathlib import Path

from .compiler import Compiler
from .package_manager import OFFLINE_REGISTRY, LOCAL_REGISTRY, PackageManager
from .runtime import Runtime
from .docs import build_docs


TEMPLATE_SNIPPETS = {
    "lib": textwrap.dedent(
        """
        import std.io as io;

        export function main() {
            io.println("Hello from Trif library template!");
        }
        """
    ).strip(),
    "web": textwrap.dedent(
        """
        import std.http as http;
        import std.io as io;

        const server = http.createServer({ port: 5173 });

        server.get("/", function(ctx) {
            return ctx.html("<h1>Welcome to Trif Web</h1>");
        });

        server.get("/api/time", function(ctx) {
            return ctx.json({ now: http.now() });
        });

        export function main() {
            io.println("Starting Trif web dev server at http://localhost:5173");
            server.listen();
        }
        """
    ).strip(),
    "mobile": textwrap.dedent(
        """
        import std.mobile as mobile;
        import std.io as io;

        const app = mobile.createApp({ title: "Trif Mobile" });

        app.screen("home", function(screen) {
            screen.header("Trif Mobile Starter");
            screen.text("Edit src/main.trif to build rich native apps.");
            screen.button("Tap me", function() {
                io.println("Button tapped!");
            });
        });

        export function main() {
            mobile.build(app, { platform: "pwa", outDir: "build/mobile" });
        }
        """
    ).strip(),
    "memory": textwrap.dedent(
        """
        import std.memory as memory;
        import std.io as io;

        export function main() {
            const region = memory.openBuffer(64);
            region.write32(0, 0xDEADBEEF);
            const value = region.read32(0);
            io.println("Read value: " + memory.formatHex(value));
        }
        """
    ).strip(),
    "reverse": textwrap.dedent(
        """
        import std.reverse as reverse;
        import std.io as io;

        export function main() {
            const info = reverse.inspectExecutable("./a.out");
            io.println("Target format: " + info.format);
            io.println("Sections detected: " + info.sections.length);
        }
        """
    ).strip(),
}


def _default_output_name(source: Path, target: str) -> Path:
    if target == "python":
        return source.with_suffix(".py")
    if target == "javascript":
        return source.with_suffix(".js")
    if target == "bytecode":
        return source.with_suffix(".trifc")
    raise ValueError(f"Unknown target {target}")


def compile_command(args: argparse.Namespace) -> None:
    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"Source file {source} does not exist")

    compiler = Compiler()
    output_path = Path(args.output) if args.output else _default_output_name(source, args.target)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = compiler.compile_file(source, target=args.target, optimize=not args.no_opt)

    if args.target == "bytecode":
        output_path.write_bytes(result)
    else:
        text = result
        if args.encrypt:
            text = compiler.encrypt_output(text, args.encrypt)
        output_path.write_text(text, encoding="utf-8")

    print(f"Compiled {source} -> {output_path}")


def run_command(args: argparse.Namespace) -> None:
    source = Path(args.source)
    compiler = Compiler()
    runtime = Runtime()
    result = compiler.compile_file(source, target="python", optimize=not args.no_opt)
    runtime.execute_python(result, argv=args.args)


def create_command(args: argparse.Namespace) -> None:
    project = Path(args.name)
    manager = PackageManager(project_root=project)
    manager.init(project)
    snippet = TEMPLATE_SNIPPETS[args.template]
    main_path = project / "src" / "main.trif"
    main_path.write_text(snippet + "\n", encoding="utf-8")

    if args.template == "web":
        public = project / "public"
        public.mkdir(exist_ok=True)
        html = textwrap.dedent(
            """
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="utf-8" />
                <title>Trif Web Starter</title>
              </head>
              <body>
                <h1>Trif Web Starter</h1>
                <p>Your server code lives in <code>src/main.trif</code>.</p>
              </body>
            </html>
            """
        ).strip()
        (public / "index.html").write_text(html + "\n", encoding="utf-8")
    elif args.template == "mobile":
        assets = project / "mobile"
        assets.mkdir(exist_ok=True)
        manifest = {
            "name": project.name,
            "platform": "pwa",
            "description": "Generated by trif create"
        }
        (assets / "app.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Created {args.template} project at {project}")


def package_command(args: argparse.Namespace) -> None:
    project_root = Path(getattr(args, "project", os.getcwd()))
    manager = PackageManager(project_root=project_root)
    action = args.action
    if action == "init":
        manager.init(Path(args.path))
    elif action == "install":
        manager.install(args.package)
    elif action == "install-local":
        manager.install(f"file:{args.path}")
    elif action == "publish":
        manager.publish(Path(args.path))
    elif action == "list":
        packages = manager.list_installed()
        print(json.dumps(packages, indent=2))
    elif action == "use":
        manager.use_registry(args.url)
    elif action == "serve":
        serve_registry(args.port, Path(args.directory) if args.directory else LOCAL_REGISTRY)
    elif action == "offline":
        print(OFFLINE_REGISTRY.as_posix())
    else:
        raise SystemExit(f"Unknown package action {action}")


def serve_registry(port: int, directory: Path) -> None:
    directory = directory.resolve()
    if not directory.exists():
        raise SystemExit(f"Registry directory {directory} does not exist")
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))

    class RegistryServer(socketserver.TCPServer):
        allow_reuse_address = True

    with RegistryServer(("", port), handler) as httpd:
        print(f"Serving registry from {directory} at http://localhost:{port}/ (Ctrl+C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("Stopping registry server")


def docs_command(_: argparse.Namespace) -> None:
    docs_root = build_docs()
    print(f"Documentation generated at {docs_root}")


def repl_command(_: argparse.Namespace) -> None:
    runtime = Runtime()
    compiler = Compiler()
    print("Trif interactive shell. Type :quit to exit.")
    buffer: list[str] = []
    while True:
        try:
            prompt = "... " if buffer else ">>> "
            line = input(prompt)
        except EOFError:
            break
        if line.strip() == ":quit":
            break
        buffer.append(line)
        if line.strip().endswith("{") or line.strip() == "":
            continue
        source = "\n".join(buffer)
        try:
            py_code = compiler.compile_source(source, target="python")
            runtime.execute_python(py_code)
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
        buffer.clear()


def configure_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="trif", description="Trif language toolchain")
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile", help="Compile a Trif source file")
    compile_p.add_argument("source")
    compile_p.add_argument("-o", "--output")
    compile_p.add_argument("-t", "--target", choices=["python", "javascript", "bytecode"], default="python")
    compile_p.add_argument("--no-opt", action="store_true", help="Disable optimizations")
    compile_p.add_argument("--encrypt", help="Encrypt output using the given passphrase")
    compile_p.set_defaults(func=compile_command)

    run_p = sub.add_parser("run", help="Compile and run a Trif source file")
    run_p.add_argument("source")
    run_p.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to the program")
    run_p.add_argument("--no-opt", action="store_true", help="Disable optimizations")
    run_p.set_defaults(func=run_command)

    create_p = sub.add_parser("create", help="Scaffold a new Trif project")
    create_p.add_argument("name")
    create_p.add_argument(
        "--template",
        choices=sorted(TEMPLATE_SNIPPETS.keys()),
        default="lib",
        help="Project template",
    )
    create_p.set_defaults(func=create_command)

    pkg_p = sub.add_parser("package", help="Manage Trif packages")
    pkg_p.add_argument(
        "--project",
        default=os.getcwd(),
        help="Project root that will receive installed packages",
    )
    pkg_sub = pkg_p.add_subparsers(dest="action", required=True)
    init_p = pkg_sub.add_parser("init", help="Initialise a package in the given directory")
    init_p.add_argument("path", nargs="?", default=os.getcwd())
    init_p.set_defaults(func=package_command)

    install_p = pkg_sub.add_parser("install", help="Install a package by name")
    install_p.add_argument("package")
    install_p.set_defaults(func=package_command)

    install_local_p = pkg_sub.add_parser("install-local", help="Install a package from a local path")
    install_local_p.add_argument("path")
    install_local_p.set_defaults(func=package_command)

    publish_p = pkg_sub.add_parser("publish", help="Publish the package in the given directory to the local registry")
    publish_p.add_argument("path", nargs="?", default=os.getcwd())
    publish_p.set_defaults(func=package_command)

    list_p = pkg_sub.add_parser("list", help="List installed packages")
    list_p.set_defaults(func=package_command)

    use_p = pkg_sub.add_parser("use", help="Switch registry endpoint")
    use_p.add_argument("url")
    use_p.set_defaults(func=package_command)

    serve_p = pkg_sub.add_parser("serve", help="Serve a registry over HTTP")
    serve_p.add_argument("--port", type=int, default=4873)
    serve_p.add_argument("--directory", help="Directory to serve", default=None)
    serve_p.set_defaults(func=package_command)

    offline_p = pkg_sub.add_parser("offline", help="Print the path to the bundled offline registry")
    offline_p.set_defaults(func=package_command)

    docs_p = sub.add_parser("docs", help="Generate static documentation site")
    docs_p.set_defaults(func=docs_command)

    repl_p = sub.add_parser("repl", help="Interactive Trif shell")
    repl_p.set_defaults(func=repl_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = configure_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
