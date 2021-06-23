import itertools
from typing import Mapping, NoReturn, Sequence, cast

from jspr.runtime import (Applicable, Arguments, Environment, JSPRException, KeywordList, Value, Undefined)


def eval_expression(val: Value, env: Environment) -> Value:
    if isinstance(val, str):
        return eval_expr_string(val, env)
    if isinstance(val, Sequence):
        return eval_expr_array(val, env)
    if isinstance(val, Mapping):
        val = cast(Mapping[str, Value], val)
        return eval_expr_map(val, env)
    if isinstance(val, (bool, int, float)) or val is None:
        return val
    raise RuntimeError(f'Unhandled value: {val=!r}')


def eval_expr_string(string: str, env: Environment) -> Value:
    if string.startswith('.'):
        varname = string[1:]
        return env_lookup(env, varname)
    return string


def env_lookup(env: Environment, key: str) -> Value:
    value = env.lookup(key)
    if value is Undefined:
        raise_(['env-name-error', key])
    return value


def eval_expr_array(arr: Sequence[Value], env: Environment) -> Value:
    if len(arr) == 0:
        return arr
    head = arr[0]
    tail = arr[1:]
    if isinstance(head, str):
        func = env_lookup(env, head)
        func = cast(Applicable, func)
        return apply_array(func, tail, env)
    if isinstance(head, Mapping) and len(head) == 1:
        if any(not isinstance(el, Mapping) for el in tail):
            raise_(['invalid-kw-apply', arr])
        arr = cast(Sequence[Mapping[str, Value]], arr)
        return apply_kwlist(arr, env)
    func = eval_expression(head, env)
    func = cast(Applicable, func)
    return apply_array(func, tail, env)


def eval_expr_map(m: Mapping[str, Value], env: Environment) -> Value:
    if len(m) != 1:
        raise_(['invalid-bare-map', m])
    key, expr = next(iter(m.items()))
    nkey, nval = normalize_pair(key, expr)
    if nkey.startswith('-'):
        new_m = {nkey[1:]: nval}
        return eval_expr_array([new_m], env)
    if not nkey.endswith('='):
        raise_(['invalid-bare-map', m])
    varname = nkey[:-1]
    varvalue = eval_expression(nval, env)
    env.define(varname, varvalue)
    return varvalue


def eval_expr_seq(seq: Value, env: Environment) -> Value:
    if not isinstance(seq, Sequence) or isinstance(seq, str):
        raise_(['invalid-do', seq])
    ret = None
    for expr in seq:
        ret = eval_expression(expr, env)
    return ret


def raise_(value: Value) -> NoReturn:
    raise JSPRException(value)


def apply_array(func: Applicable, args: Sequence[Value], env: Environment) -> Value:
    return do_apply(func, args, env)


def detect_kwlist(args: Value) -> bool:
    return (isinstance(args, Sequence)  #
            and isinstance(args[0], Mapping)  #
            and len(args[0]) == 1  #
            and all(isinstance(el, Mapping) for el in args))


def load_kwlist(args: Sequence[Value]) -> KeywordList:
    if not detect_kwlist(args):
        raise_(['invalid-kw-apply', args])
    args = cast(Sequence[Mapping[str, Value]], args)
    each_items = (m.items() for m in args)
    pair_iter = itertools.chain.from_iterable(each_items)
    norm_pairs = (normalize_pair(key, expr) for key, expr in pair_iter)
    return KeywordList(norm_pairs)


def apply_kwlist(args: Sequence[Value], env: Environment) -> Value:
    norm_kws = load_kwlist(args)
    fn_key = norm_kws.first_key
    func = cast(Applicable, env_lookup(env, fn_key))
    return do_apply(func, norm_kws, env)


def normalize_pair(key: str, value: Value) -> tuple[str, Value]:
    if key.endswith("'"):
        key = key[:-1]
        return (key, ['quote', value])
    if key.endswith('`'):
        if not isinstance(value, Sequence) or isinstance(value, str):
            raise_(['invalid-array-quote', key, value])
        key = key[:-1]
        return (key, ['array', value])
    if key.endswith('-'):
        if not isinstance(value, Sequence) or isinstance(value, str):
            raise_(['invalid-do-quote', key, value])
        key = key[:-1]
        return (key, ['do', value])
    if key.endswith(':'):
        if not isinstance(value, Mapping):
            raise_(['invalid-map-quote', key, value])
        return (key[:-1], ['map', value])
    if not key:
        return (key, value)
    if key.endswith('='):
        return (key, value)
    if not key[-1].isalnum():
        raise_(['invalid-key-suffix', key, value])
    return (key, value)


def do_apply(func: Applicable, args: Arguments, env: Environment) -> Value:
    if not callable(func):
        raise_(['invalid-apply', func, args])
    return func(args, env)


def eval_array(arr: Sequence[Value], env: Environment) -> Sequence[Value]:
    new_env = env.new_child()
    return [eval_expression(el, new_env) for el in arr]


def eval_map(m: Mapping[str, Value], env: Environment) -> Mapping[str, Value]:
    new_env = env.new_child()
    pairs = m.items()
    norm_pairs = (normalize_pair(k, v) for k, v in pairs)
    val_pairs = ((k, eval_expression(v, new_env)) for k, v in norm_pairs)
    return dict(val_pairs)


def eval_args(args: Arguments, env: Environment) -> Arguments:
    new_env = env.new_child()
    if isinstance(args, KeywordList):
        return eval_kwlist(args, new_env)
    return eval_array(args, new_env)


def eval_kwlist(kwlist: KeywordList, env: Environment) -> KeywordList:
    val_pairs = ((key, eval_expression(expr, env)) for key, expr in kwlist)
    return KeywordList(val_pairs)
