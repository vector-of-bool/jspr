import argparse
from jspr.runtime import Environment
from pathlib import Path
import json
import sys
from typing import NoReturn, Protocol, Sequence, cast


def make_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='The JSPR file to execute', type=Path)
    return parser


class ParsedArgv(Protocol):
    file: Path


def parse_argv(argv: Sequence[str]) -> ParsedArgv:
    parser = make_arg_parser()
    return cast(ParsedArgv, parser.parse_args(argv))


def main(argv: Sequence[str]) -> int:
    args = parse_argv(argv)
    print(repr(args))
    if str(args.file) == '-':
        doc = json.load(sys.stdin)
    else:
        doc = json.loads(args.file.read_text())
    ctx = Environment.root_jspr_context()
    value = ctx.eval(doc)
    print(repr(value))
    return 0


def start() -> NoReturn:
    sys.exit(main(sys.argv[1:]))
