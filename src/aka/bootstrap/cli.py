"""Generic launch command; business arguments follow an explicit boundary."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aka.contracts.startup import Invocation
from .host import run_profile


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    boundary = argv.index("--") if "--" in argv else len(argv)
    parser = argparse.ArgumentParser(prog="aka run")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--patch", type=Path, action="append", default=[])
    parser.add_argument("--var", action="append", default=[], metavar="NAME=VALUE")
    args = parser.parse_args(argv[:boundary])
    if boundary == len(argv):
        parser.error("separate startup arguments with --")
    variables = {}
    for item in args.var:
        if "=" not in item:
            parser.error("--var requires NAME=VALUE")
        name, value = item.split("=", 1)
        if name in variables:
            parser.error(f"duplicate variable: {name}")
        variables[name] = value
    return run_profile(args.profile, Invocation(argv[boundary + 1:]),
                       patch_files=args.patch, variables=variables)
