"""Command line interface for the Trif language toolchain."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .compiler import Compiler
from .package_manager import PackageManager
from .runtime import Runtime
from .docs import build_docs


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


def package_command(args: argparse.Namespace) -> None:
    manager = PackageManager()
    if args.action == "init":
        manager.init(Path(args.path))
    elif args.action == "install":
        manager.install(args.package)
    elif args.action == "publish":
        manager.publish(Path(args.path))
    elif args.action == "list":
        packages = manager.list_installed()
        print(json.dumps(packages, indent=2))
    else:
        raise SystemExit(f"Unknown package action {args.action}")


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

    pkg_p = sub.add_parser("package", help="Manage Trif packages")
    pkg_sub = pkg_p.add_subparsers(dest="action", required=True)
    init_p = pkg_sub.add_parser("init", help="Initialise a package in the given directory")
    init_p.add_argument("path", nargs="?", default=os.getcwd())
    init_p.set_defaults(func=package_command)

    install_p = pkg_sub.add_parser("install", help="Install a package by name")
    install_p.add_argument("package")
    install_p.set_defaults(func=package_command)

    publish_p = pkg_sub.add_parser("publish", help="Publish the package in the given directory to the local registry")
    publish_p.add_argument("path", nargs="?", default=os.getcwd())
    publish_p.set_defaults(func=package_command)

    list_p = pkg_sub.add_parser("list", help="List installed packages")
    list_p.set_defaults(func=package_command)

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
