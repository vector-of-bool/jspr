"""
General utilities
"""

from typing import Sequence
from .runtime import Arguments, JSPRException, PositionalArgs, Value, KeywordSequence


def not_kwlist(args: Arguments) -> PositionalArgs:
    if isinstance(args, KeywordSequence):
        fn_name = args.first_key
        raise TypeError(f'Function "{fn_name}" does not accept keyword arguments')
    return args


def unary(fn_name: str, args: Arguments) -> Value:
    if isinstance(args, KeywordSequence):
        if len(args.keywords) > 1:
            raise JSPRException(['invalid-args', args, f'"{fn_name}" expects exactly one argument'])
        return args.first_arg
    elif len(args) != 1:
        raise JSPRException(['invalid-args', args, f'"{fn_name}" expects exactly one argument'])
    else:
        return args[0]


def unpack_kwlist(fn_name: str, args: Arguments, keys: Sequence[str]) -> PositionalArgs:
    if not isinstance(args, KeywordSequence):
        if len(args) != len(keys) + 1:
            raise TypeError(f'Function "{fn_name}" expects {len(keys)+1} arguments ({len(args)} given)')
        return args
    return (args.first_arg, ) + tuple(args.get(k) for k in keys)
