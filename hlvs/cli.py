"""Command line: doctor | validate | run | verify."""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__, schema
from .capabilities import discover, summarise
from .runner import Runner


def cmd_doctor(args) -> int:
    info = discover(probe=not args.no_probe)
    print(summarise(info))
    if args.json:
        print(json.dumps(info, indent=2))
    if args.strict:
        problems = []
        if not info["qwen"].get("reachable"):
            problems.append("qwen not reachable")
        missing = [a for a, e in info["rust_apps"].items() if not e["found"]]
        if missing:
            problems.append("missing apps: %s" % ",".join(missing))
        if problems:
            print("\nSTRICT: " + "; ".join(problems))
            return 2
    return 0


def cmd_validate(args) -> int:
    try:
        project = schema.load(args.project)
    except FileNotFoundError:
        print("no such file: %s" % args.project)
        return 2
    errors = schema.validate(project, base_dir=os.path.dirname(os.path.abspath(args.project)))
    if errors:
        print("INVALID — %d problem(s):" % len(errors))
        for e in errors:
            print("  - %s" % e)
        return 1
    print("VALID — %d scene(s), %d asset(s)" % (len(project["scenes"]), len(project["assets"])))
    return 0


def cmd_run(args) -> int:
    project = schema.load(args.project)
    workdir = args.workdir or os.path.join(os.path.dirname(os.path.abspath(args.project)), "build")
    runner = Runner(project, args.project, workdir)
    report = runner.run(dry_run=args.dry_run, resume=not args.no_resume)
    path = runner.manifest.save()
    print("\nmanifest: %s" % path)
    summary = report.get("summary", {})
    print("summary : %s" % json.dumps(summary))
    return 0 if summary.get("failed", 0) == 0 else 1


def cmd_verify(args) -> int:
    from .adapters import media
    info = media.probe(args.output)
    if not info.get("exists"):
        print("missing: %s" % args.output)
        return 2
    print(json.dumps({k: v for k, v in info.items() if k != "video" and k != "audio"}, indent=2))
    ok, err = media.decodes_cleanly(args.output)
    print("clean decode: %s" % ok)
    if not ok:
        print(err)
        return 1
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="hlvs", description="hermes-local-video-studio")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="discover the environment")
    d.add_argument("--json", action="store_true")
    d.add_argument("--no-probe", action="store_true", help="do not run binaries, only locate them")
    d.add_argument("--strict", action="store_true")
    d.set_defaults(func=cmd_doctor)

    v = sub.add_parser("validate", help="validate a project specification")
    v.add_argument("project")
    v.set_defaults(func=cmd_validate)

    r = sub.add_parser("run", help="execute a project")
    r.add_argument("project")
    r.add_argument("--workdir")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--no-resume", action="store_true")
    r.set_defaults(func=cmd_run)

    o = sub.add_parser("verify", help="inspect a rendered file")
    o.add_argument("output")
    o.set_defaults(func=cmd_verify)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
