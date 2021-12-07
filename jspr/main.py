import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn, Sequence, cast

from typing_extensions import Protocol

import jspr


def make_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='The JSPR file to execute', type=Path)
    return parser


class ParsedArgv(Protocol):
    file: Path


def parse_argv(argv: Sequence[str]) -> ParsedArgv:
    parser = make_arg_parser()
    return cast(ParsedArgv, parser.parse_args(argv))


def _load_json(doc: bytes) -> jspr.runtime.JSONData:
    return json.loads(doc)


def _load_doc(doc: bytes) -> Any:
    try:
        import yaml
    except ModuleNotFoundError:
        return _load_json(doc)
    else:
        return yaml.safe_load(doc)


def main(argv: Sequence[str]) -> int:
    args = parse_argv(argv)
    if str(args.file) == '-':
        doc = _load_doc(sys.stdin.buffer.read())
    else:
        doc = _load_doc(args.file.read_bytes())
    ctx = jspr.runtime.Environment.root_jspr_context()
    jspr.kernel.load_kernel(ctx)
    ctx.define_fn('print', jspr.runtime.Function.from_py('print', lambda msg: print(msg)))
    value = ctx.eval(doc)
    print(repr(value))
    return 0


def start() -> NoReturn:
    sys.exit(main(sys.argv[1:]))
