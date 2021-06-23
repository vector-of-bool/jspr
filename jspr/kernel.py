"""
Core special forms for JSPR
"""

from jspr import lang
from jspr.lang import normalize_pair
import operator
from functools import reduce, wraps
from typing import (Callable, Iterable, Mapping, NamedTuple, NoReturn, Sequence, cast)

from jspr.util import not_kwlist, unary, unpack_kwlist

from .runtime import (Applicable, Arguments, Closure, Environment, Function, JSPRException, KeywordList, Macro,
                      SpecialForm, Undefined, Value, eval_kw_pair)


class _CondBranch(NamedTuple):
    if_: Value
    then: Value


def _make_cond_branchces(pair: Value) -> _CondBranch:
    if not isinstance(pair, Sequence) or len(pair) != 2:
        raise RuntimeError(f'Each element of the "cond" list argument must be a pair')
    return _CondBranch(pair[0], pair[1])


@SpecialForm
def cond_sf(args: Arguments, env: Environment) -> Value:
    if isinstance(args, KeywordList):
        if len(args.keywords) > 1:
            raise RuntimeError('"cond" expects only a single argument')
        args = [args.first_arg]

    if len(args) > 1:
        raise RuntimeError('"cond" only expects a single argument')

    first = args[0]
    assert isinstance(first, Sequence), args
    pairs = [_make_cond_branchces(p) for p in first]
    for if_, then in pairs:
        branch_env = env.new_child()
        if _hard_bool(branch_env.eval(if_), 'invalid-cond-condition'):
            return branch_env.eval(then)
    raise JSPRException(['cond-no-match'])


@SpecialForm
def if_sf(args: Arguments, env: Environment) -> Value:
    if_, then, else_ = unpack_kwlist('if', args, ('then', 'else'))
    subenv = env.new_child()
    pick = subenv.eval(if_)
    if pick is True:
        return subenv.eval(then)
    elif pick is False:
        return subenv.eval(else_)
    else:
        raise JSPRException(['invalid-if-condition', pick])


@SpecialForm
def quote_sf(args: Arguments, _env: Environment) -> Value:
    val = unary('just', args)
    return val


@SpecialForm
def do_sf(args: Arguments, env: Environment) -> Value:
    items = unary('do', args)
    return env.new_child().eval_seq(items)


def _mk_closure(fn_name: str, env: Environment, args: Arguments) -> Closure:
    arglist, body = unpack_kwlist(fn_name, args, ('is', ))
    if not isinstance(arglist, Sequence) or any((not isinstance(s, str)) for s in arglist):
        raise RuntimeError(f'First argument to "{fn_name}" must be a list of strings ({arglist=!r})')
    arglist = cast(Sequence[str], arglist)
    return Closure(arglist, body, env.clone())


@SpecialForm
def lambda_sf(args: Arguments, env: Environment) -> Closure:
    return _mk_closure('lambda', env, args)


@SpecialForm
def macro_sf(args: Arguments, env: Environment) -> Macro:
    closure = _mk_closure('macro', env, args)
    return Macro(closure)


@SpecialForm
def let_sf(args: Arguments, env: Environment) -> Value:
    name, value = unpack_kwlist('let', args, ('be', ))
    name = env.eval(name)
    value = env.new_child().eval(value)
    if not isinstance(name, str):
        raise TypeError(f'First argument to "let" must be a string ({name=!r})')
    env.define(name, value)
    return value


@SpecialForm
def ref_sf(args: Arguments, env: Environment) -> Value:
    name = unary('ref', args)
    name = env.eval(name)
    if not isinstance(name, str):
        raise RuntimeError(f'Argument to "ref" must be a string ({name=!r})')
    return env[name]


@Function
def eval_fn(args: Arguments) -> Value:
    expr, env = unpack_kwlist('eval', args, ('with', ))
    assert isinstance(env, Environment), ('Expected an environment as the second argument to eval()', repr(args))
    return env.eval(expr)


@SpecialForm
def apply_fn(args: Arguments, env: Environment) -> Value:
    func, arglist = unpack_kwlist('apply', args, ('with', ))
    func = env.eval(func)
    arglist = env.eval(arglist)
    if not callable(func):
        raise JSPRException(['invalid-apply-func', func, arglist])
    if not isinstance(arglist, Sequence) and not isinstance(arglist, KeywordList):
        raise JSPRException(['invalid-apply-args', func, arglist])
    return func(arglist, env)


def _assert_kwlist(expr: Sequence[Value], env: Environment) -> None:
    kwlist = lang.load_kwlist(expr)
    kwlist_vals = lang.eval_kwlist(kwlist, env)
    quoted = KeywordList((k, ['quote', v]) for k, v in kwlist_vals)
    func = cast(Applicable, lang.env_lookup(env, kwlist.first_key))
    result = lang.do_apply(func, quoted, env)
    if result is True:
        return None
    if result is False:
        kwlist_debug = list(dict((pair, )) for pair in kwlist_vals)
        raise JSPRException(['assertion-failed', expr, kwlist_debug])
    raise JSPRException(['invalid-assert-condition', expr, result])


def _assert_seq(expr: Sequence[Value], env: Environment) -> None:
    seq_vals = lang.eval_array(expr, env)
    result = lang.eval_expr_array(expr, env)
    if result is True:
        return None
    if result is False:
        raise JSPRException(['assertion-failed', expr, seq_vals])
    raise JSPRException(['invalid-assert-condition', expr, result])


@SpecialForm
def assert_sf(args: Arguments, env: Environment) -> None:
    val_expr = unary('assert', args)
    debug = None
    if isinstance(val_expr, Sequence):
        if lang.detect_kwlist(val_expr):
            return _assert_kwlist(val_expr, env)
        else:
            return _assert_seq(val_expr, env)
    val = env.eval(val_expr)
    if val is True:
        return None
    if val is False:
        raise JSPRException(['assertion-failed', val_expr, debug])
    raise JSPRException(['invalid-assert-condition', val_expr, val])


def _make_binop(name: str, argname: str, func: Callable[[Value, Value], Value]) -> Applicable:
    @wraps(func)
    def binop_fn(args: Arguments, /) -> Value:
        left, right = unpack_kwlist(name, args, [argname])
        return func(left, right)

    return Function(binop_fn)


@Function
def raise_fn(args: Arguments) -> NoReturn:
    value = unary('raise', args)
    raise JSPRException(value)


def _join_two(left: Value, right: Value) -> Value:
    if isinstance(left, str) and isinstance(right, str):
        return left + right
    if isinstance(left, list) and isinstance(right, list):
        return cast(Sequence[Value], left + right)
    raise JSPRException(cast(Sequence[Value], ['invalid-join', left, right]))


@Function
def join_fn(args: Arguments) -> Sequence[Value]:
    if len(args) < 1:
        raise JSPRException(['no-args-join'])
    items: Iterable[Value]
    if isinstance(args, KeywordList):
        items = (p[1] for p in args)
    else:
        items = args
    return reduce(_join_two, cast(Iterable[Value], items))


@Function
def elem_fn(args: Arguments) -> Value:
    seq, at = unpack_kwlist('elem', args, ('at', ))
    if not isinstance(seq, (str, Sequence)):
        raise JSPRException(['invalid-elem-seq', seq])
    if not isinstance(at, (int, float)):
        raise JSPRException(['invalid-elem-at', at])
    at = round(at)
    try:
        return seq[at]
    except IndexError:
        return ['invalid-elem-index', seq, at]


@Function
def len_fn(args: Arguments) -> int:
    seq = unary('len', args)
    if isinstance(seq, (str, Sequence, Mapping, KeywordList)):
        return len(seq)
    raise JSPRException(['invalid-len', seq])


@Function
def slice_fn(args: Arguments) -> Value:
    if isinstance(args, KeywordList):
        seq = args.first_arg
        if not isinstance(seq, (str, Sequence)):
            raise JSPRException(['invalid-slice-seq', seq])
        from_ = args.try_get('from')
        to = args.try_get('to')
        if from_ is Undefined:
            from_ = 0
        if to is Undefined:
            to = len(seq)
    else:
        if not args:
            raise JSPRException(['invalid-slice-args', args])
        seq = args[0]
        if not isinstance(seq, (str, Sequence)):
            raise JSPRException(['invalid-slice-seq', seq])
        if len(args) >= 2:
            from_ = args[1]
        else:
            from_ = 0
        if len(args) >= 3:
            to = args[2]
        else:
            to = len(seq)

    if not isinstance(from_, (int, float)):
        raise JSPRException(['invalid-slice-from', from_])
    if not isinstance(to, (int, float)):
        raise JSPRException(['invalid-slice-to', to])

    from_ = round(from_)
    to = round(to)

    if abs(to) < abs(from_):
        raise JSPRException(['invalid-slice-range', seq, from_, to])

    try:
        return seq[from_:to]
    except IndexError:
        raise JSPRException(['invalid-slice-range', seq, from_, to])


@Function
def id_fn(args: Arguments) -> Value:
    val = unary('id', args)
    return val


@SpecialForm
def array_sf(args: Arguments, env: Environment) -> Sequence[Value]:
    seq = unary('array', args)
    if not isinstance(seq, Sequence) or isinstance(seq, str):
        raise JSPRException(['invalid-array', seq])
    return lang.eval_array(seq, env)


@SpecialForm
def map_sf(args: Arguments, env: Environment) -> Sequence[Value]:
    map = unary('map', args)
    if not isinstance(map, Mapping):
        raise JSPRException(['invalid-map', seq])
    return lang.eval_map(map, env)


def _lazy_eval_args(env: Environment, args: Arguments) -> Iterable[Value]:
    if isinstance(args, Sequence):
        return (env.eval(v) for v in args)
    else:
        return (eval_kw_pair(env, p)[1] for p in args)


def _hard_bool(arg: Value, err: str) -> bool:
    if not isinstance(arg, bool):
        raise JSPRException([err, arg])
    return arg


@SpecialForm
def or_sf(args: Arguments, env: Environment) -> bool:
    return any(_hard_bool(b, 'invalid-or-condition') for b in _lazy_eval_args(env, args))


@SpecialForm
def and_sf(args: Arguments, env: Environment) -> bool:
    return all(_hard_bool(b, 'invalid-and-condition') for b in _lazy_eval_args(env, args))


@SpecialForm
def xor_sf(args: Arguments, env: Environment) -> bool:
    found = False
    values = _lazy_eval_args(env, args)
    for v in values:
        if _hard_bool(v, 'invalid-xor-condition'):
            if found:
                return False
            found = True
    return found


@SpecialForm
def get_current_env_fn(args: Arguments, env: Environment) -> Value:
    args = not_kwlist(args)
    if args != []:
        raise RuntimeError(f'__env__ does not expect arguments (Got {args=!r})')
    return env


@SpecialForm
def dunder_eval(args: Arguments, env: Environment) -> Value:
    from . import lang
    expr = unary('__eval__', args)
    return lang.eval_expression(expr, env)


@SpecialForm
def dunder_eval_seq(args: Arguments, env: Environment) -> Value:
    from . import lang
    seq = unary('__eval_seq__', args)
    return lang.eval_expr_seq(seq, env)


def load_kernel(env: Environment) -> None:
    # Special forms
    env.define_fn('__env__', get_current_env_fn)
    env.define_fn('__eval__', dunder_eval)
    env.define_fn('__eval_seq__', dunder_eval_seq)
    env.define_fn('if', if_sf)
    env.define_fn('cond', cond_sf)
    env.define_fn('lambda', lambda_sf)
    env.define_fn('macro', macro_sf)
    env.define_fn('quote', quote_sf)
    env.define_fn('do', do_sf)
    env.define_fn('let', let_sf)
    env.define_fn('ref', ref_sf)
    env.define_fn('array', array_sf)
    env.define_fn('map', map_sf)
    env.define_fn('or', or_sf)
    env.define_fn('and', and_sf)
    env.define_fn('xor', xor_sf)
    env.define_fn('assert', assert_sf)
    # Regular predefined functions
    env.define_fn('raise', raise_fn)
    env.define_fn('apply', apply_fn)
    env.define_fn('eval', eval_fn)
    env.define_fn('len', len_fn)
    env.define_fn('elem', elem_fn)
    env.define_fn('slice', slice_fn)
    env.define_fn('id', id_fn)
    env.define_fn('+', _make_binop('add', 'and', operator.add))
    env.define_fn('add', _make_binop('add', 'and', operator.add))
    env.define_fn('-', _make_binop('sub', 'minus', operator.sub))
    env.define_fn('sub', _make_binop('sub', 'minus', operator.sub))
    env.define_fn('*', _make_binop('mul', 'by', operator.mul))
    env.define_fn('mul', _make_binop('mul', 'by', operator.mul))
    env.define_fn('//', _make_binop('floordiv', 'by', operator.floordiv))
    env.define_fn('floordiv', _make_binop('floordiv', 'by', operator.floordiv))
    env.define_fn('/', _make_binop('truediv', 'by', operator.truediv))
    env.define_fn('div', _make_binop('truediv', 'by', operator.truediv))
    env.define_fn('=', _make_binop('eq', 'and', operator.eq))
    env.define_fn('eq', _make_binop('eq', 'and', operator.eq))
    env.define_fn('neq', _make_binop('ne', 'and', operator.ne))
    env.define_fn('!=', _make_binop('ne', 'and', operator.ne))
    env.define_fn('=!', _make_binop('ne', 'and', operator.ne))
    env.define_fn('<>', _make_binop('ne', 'and', operator.ne))
    env.define_fn('join', join_fn)
