from __future__ import annotations

import itertools
import re
from typing import Any
from typing import Mapping as PyMapping
from typing import NoReturn
from typing import Sequence as PySequence
from typing import cast

from typing_extensions import TypeGuard

from jspr.runtime import (Applicable, Arguments, Environment, JSPRException, KeywordSequence, Map, Sequence, Undefined,
                          Value, is_map, is_sequence)

VALID_IDENT_RE = re.compile(r'[a-zA-Z_](?:[\w_\d-]*[\w_\d])?')
UNESCAPED_INTERP_SPLIT = re.compile(r'(.*?[^`](?:``)*)#\{(.*)')


def eval_expression(val: Value, env: Environment) -> Value:
    if isinstance(val, str):
        return eval_expr_string(val, env)
    if isinstance(val, PySequence):
        return eval_expr_seq(val, env)
    if isinstance(val, PyMapping):
        val = cast(Map, val)
        return eval_expr_map(val, env)
    if isinstance(val, (bool, int, float)) or val is None:
        return val
    raise RuntimeError(f'Unhandled value: {val!r}')


def eval_expr_string(string: str, env: Environment) -> Value:
    if string.startswith('.'):
        varname = string[1:]
        return ref_str_lookup(env, varname)
    return interpolate_string(string, env)


def interpolate_string(string: str, env: Environment) -> str:
    if string.find('#{') < 0:
        # Optimize: Most strings won't have interpolations, so don't scan them
        return string
    # Find the next un-escaped part
    mat = UNESCAPED_INTERP_SPLIT.match(string)
    if mat is None:
        # No unescaped matches. Replace any that _were_ escaped:
        return string.replace('`#', '#')
    until, tail = mat.groups()
    until = until.replace('`#', '#')
    brace_pos = tail.find('}')
    if brace_pos < 0:
        raise_(['unterminated-string-interp', tail])
    ref = tail[:brace_pos]
    val = ref_str_lookup(env, ref)
    part = until + _to_str(val)
    tail = interpolate_string(tail[brace_pos + 1:], env)
    return part + tail


def _to_str(v: Any) -> str:
    if v is None:
        return 'null'
    return str(v)


def ref_str_lookup(env: Environment, key: str) -> Value:
    path = key.split('.')
    value = env
    while path:
        attr = path[0]
        value = attribute_lookup(value, attr)
        path.pop(0)
    return value


def attribute_lookup(map: Any, key: str) -> Value:
    fail = lambda: raise_(['no-such-attr', map, key])
    if hasattr(map, '__jspr_getattr__'):
        return map.__jspr_getattr__(key)
    try:
        if hasattr(map, '__getitem__'):
            return map[key]
        fail()
    except AttributeError as e:
        if e.args[0] is key:
            fail()
        raise
    except KeyError as e:
        if e.args[0] is key:
            fail()
        raise


def eval_expr_seq(arr: Sequence, env: Environment) -> Value:
    if len(arr) == 0:
        return arr
    head = arr[0]
    tail = arr[1:]
    if isinstance(head, str):
        func = ref_str_lookup(env, head)
        func = cast(Applicable, func)
        return apply_seq(func, tail, env)
    if is_map(head) and len(head) == 1:
        if not detect_kwlist(arr):
            raise_(['invalid-kw-apply', arr])
        return apply_kwlist(arr, env)
    func = eval_expression(head, env)
    func = cast(Applicable, func)
    return apply_seq(func, tail, env)


def eval_expr_map(m: Map, env: Environment) -> Value:
    if len(m) != 1:
        raise_(['invalid-bare-map', m])
    key, expr = next(iter(m.items()))
    nkey, nval = normalize_pair(key, expr)
    if nkey.startswith('-'):
        new_m = {nkey[1:]: nval}
        return eval_expr_seq([new_m], env)
    if not nkey.endswith('='):
        raise_(['invalid-bare-map', m])
    varname = nkey[:-1]
    varvalue = eval_expression(nval, env)
    env.define(varname, varvalue)
    return varvalue


def eval_do_seq(seq: Value, env: Environment) -> Value:
    if not is_sequence(seq):
        raise_(['invalid-do', seq])
    ret = None
    for expr in seq:
        ret = eval_expression(expr, env)
    return ret


def raise_(value: Value) -> NoReturn:
    raise JSPRException(value)


def apply_seq(func: Applicable, args: Sequence, env: Environment) -> Value:
    return do_apply(func, args, env)


def detect_kwlist(args: Value) -> TypeGuard[PySequence[Map]]:
    return (is_sequence(args)  #
            and is_map(args[0])  #
            and len(args[0]) == 1  #
            and all(is_map(el) for el in args))


def load_kwlist(args: Sequence) -> KeywordSequence:
    if not detect_kwlist(args):
        raise_(['invalid-kw-apply', args])
    each_items = (m.items() for m in args)
    pair_iter = itertools.chain.from_iterable(each_items)
    norm_pairs = (normalize_pair(key, expr) for key, expr in pair_iter)
    return KeywordSequence(norm_pairs)


def apply_kwlist(args: Sequence, env: Environment) -> Value:
    norm_kws = load_kwlist(args)
    fn_key = norm_kws.first_key
    func = cast(Applicable, ref_str_lookup(env, fn_key))
    return do_apply(func, norm_kws, env)


def normalize_pair(key: str, value: Value) -> tuple[str, Value]:
    if ':' in key:
        idx = key.index(':')
        nkey = key[:idx]
        ntail = key[idx + 1:]
        nvalue = normalize_pair(ntail, value)
        if len(nkey) and not nkey[-1].isalnum() and nkey[-1] != '=':
            raise_(['invalid-key-suffix', nkey, nvalue])
        return (nkey, nvalue)
    if key.endswith("'"):
        key = key[:-1]
        return (key, ['quote', value])
    if len(key) and not key[-1].isalnum() and key[-1] != '=':
        raise_(['invalid-key-suffix', key, value])
    return (key, value)


def do_apply(func: Applicable, args: Arguments, env: Environment) -> Value:
    if not callable(func):
        raise_(['invalid-apply', func, args])
    return func(args, env)


def eval_seq(arr: Sequence, env: Environment) -> Sequence:
    new_env = env.new_child()
    return [eval_expression(el, new_env) for el in arr]


def eval_map(m: Map, env: Environment) -> Map:
    if not is_map(m):
        raise JSPRException(['invalid-map', m])
    new_env = env.new_child()
    pairs = m.items()
    norm_pairs = (normalize_pair(k, v) for k, v in pairs)
    val_pairs = ((k, eval_expression(v, new_env)) for k, v in norm_pairs)
    return dict(val_pairs)


def eval_args(args: Arguments, env: Environment) -> Arguments:
    new_env = env.new_child()
    if isinstance(args, KeywordSequence):
        return eval_kwseq(args, new_env)
    return eval_seq(args, new_env)


def eval_kwseq(kwlist: KeywordSequence, env: Environment) -> KeywordSequence:
    val_pairs = ((key, eval_expression(expr, env)) for key, expr in kwlist)
    return KeywordSequence(val_pairs)
