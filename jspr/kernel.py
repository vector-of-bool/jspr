"""
Core special forms for JSPR
"""

from __future__ import annotations

import itertools
import operator
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator
from typing import Mapping as PyMapping
from typing import NamedTuple, NoReturn
from typing import Sequence as PySequence
from typing import cast

from typing_extensions import Literal

from jspr import lang
from jspr.util import not_kwlist, unary, unpack_kwlist

from .mod import Module
from .runtime import (Applicable, Arguments, Closure, Environment, Function, JSPRException, KeywordSequence, Macro, Map,
                      Sequence, SpecialForm, Undefined, Value, eval_kw_pair, is_map, is_sequence, quasiquote)


@SpecialForm
def do_sf(args: Arguments, env: Environment) -> Value:
    items = unary('do', args)
    return lang.eval_do_seq(items, env.new_child())


class _CondBranch(NamedTuple):
    if_: Value
    then: Value


def _make_cond_branchces(pair: Value) -> _CondBranch:
    if not is_sequence(pair) or len(pair) != 2:
        raise JSPRException(['invalid-cond-branch', pair])
    return _CondBranch(pair[0], pair[1])


@SpecialForm
def cond_sf(args: Arguments, env: Environment) -> Value:
    first = unary('cond', args)
    if not is_sequence(first):
        raise JSPRException(['invalid-args', args, '"cond" expects a literal sequence argument'])
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
    pick = lang.eval_expression(if_, subenv)
    if pick is True:
        return lang.eval_expression(then, subenv)
    elif pick is False:
        return lang.eval_expression(else_, subenv)
    else:
        raise JSPRException(['invalid-if-condition', pick])


@SpecialForm
def quote_sf(args: Arguments, _env: Environment) -> Value:
    val = unary('quote', args)
    return val


@SpecialForm
def quasiquote_sf(args: Arguments, env: Environment) -> Value:
    val = unary('quasiquote', args)
    return quasiquote(val, env)


@Function
def let_sf(args: Arguments, env: Environment) -> Value:
    name, value = unpack_kwlist('let', args, ('be', ))
    if not isinstance(name, str):
        raise JSPRException(['invalid-varname', 7])
    if isinstance(value, Closure) and value.name == '':
        value.name = name
    lang.set_env_val(env, name, value)
    return value


@SpecialForm
def ref_sf(args: Arguments, env: Environment) -> Value:
    name = unary('ref', args)
    name = env.eval(name)
    if not isinstance(name, str):
        raise RuntimeError(f'Argument to "ref" must be a string (name={name!r})')
    found = env.lookup(name)
    if found is Undefined:
        raise JSPRException(['env-name-error', name])
    return found


@SpecialForm
def seq_sf(args: Arguments, env: Environment) -> Sequence:
    s = unary('seq', args)
    if not is_sequence(s):
        lang.raise_(['invalid-seq', s])
    return lang.eval_seq(s, env)


@SpecialForm
def map_sf(args: Arguments, env: Environment) -> Map:
    map = unary('map', args)
    if not is_map(map):
        lang.raise_(['invalid-map', map])
    return lang.eval_map(map, env)


def _mk_closure(fn_name: str, env: Environment, args: Arguments) -> Closure:
    arglist, body = unpack_kwlist(fn_name, args, ('is', ))
    if not is_sequence(arglist) or any((not isinstance(s, str)) for s in arglist):
        raise RuntimeError(f'First argument to "{fn_name}" must be a list of strings (arglist={arglist!r})')
    arglist = cast(PySequence[str], arglist)
    return Closure(arglist, body, env.clone())


@SpecialForm
def lambda_sf(args: Arguments, env: Environment) -> Closure:
    return _mk_closure('lambda', env, args)


@SpecialForm
def macro_sf(args: Arguments, env: Environment) -> Macro:
    return Macro(_mk_closure('macro', env, args))


@Function
def eval_fn(args: Arguments, env_: Environment) -> Value:
    expr, env = unpack_kwlist('eval', args, ('with', ))
    if not isinstance(env, Environment):
        raise JSPRException(['invalid-eval-env', env])
    return env.eval(expr)


@Function
def apply_fn(args: Arguments, env: Environment) -> Value:
    func, arglist = unpack_kwlist('apply', args, ('with', ))
    if not callable(func):
        raise JSPRException(['invalid-apply-func', func, arglist])
    if not is_sequence(arglist) and not isinstance(arglist, KeywordSequence):
        raise JSPRException(['invalid-apply-args', func, arglist])
    return func(arglist, env)


def _assert_kwseq(expr: Sequence, env: Environment) -> None:
    kwlist = lang.load_kwlist(expr)
    kwlist_vals = lang.eval_kwseq(kwlist, env)
    quoted = KeywordSequence((k, ['quote', v]) for k, v in kwlist_vals)
    func = cast(Applicable, lang.ref_str_lookup(env, kwlist.first_key))
    result = lang.do_apply(func, quoted, env)
    if result is True:
        return None
    if result is False:
        kwlist_debug = list(dict((pair, )) for pair in kwlist_vals)
        raise JSPRException(['assertion-failed', expr, kwlist_debug])
    raise JSPRException(['invalid-assert-condition', expr, result])


def _assert_seq(expr: Sequence, env: Environment) -> None:
    seq_vals = lang.eval_seq(expr, env)
    result = lang.eval_expr_seq(expr, env)
    if result is True:
        return None
    if result is False:
        raise JSPRException(['assertion-failed', expr, seq_vals])
    raise JSPRException(['invalid-assert-condition', expr, result])


@SpecialForm
def assert_sf(args: Arguments, env: Environment) -> None:
    val_expr = unary('assert', args)
    debug = None
    if is_sequence(val_expr):
        if lang.detect_kwlist(val_expr):
            return _assert_kwseq(val_expr, env)
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
    def binop_fn(args: Arguments, _env: Environment) -> Value:
        left, right = unpack_kwlist(name, args, [argname])
        return func(left, right)

    return Function(binop_fn)


@Function
def raise_fn(args: Arguments, env: Environment) -> NoReturn:
    value = unary('raise', args)
    raise JSPRException(value)


def _join_two(left: Value, right: Value) -> Value:
    if isinstance(left, str) and isinstance(right, str):
        return left + right
    if is_sequence(left) and is_sequence(right):
        return cast(Sequence, list(left) + list(right))
    raise JSPRException(cast(Sequence, ['invalid-join', left, right]))


@Function
def join_fn(args: Arguments, env: Environment) -> Sequence:
    seq = unary('join', args)
    return list(itertools.chain.from_iterable(seq))


@Function
def str_join_fn(args: Arguments, env: Environment) -> str:
    if isinstance(args, KeywordSequence) and args.try_get('with') is not Undefined:
        seq, joiner = unpack_kwlist('str.join', args, ['with'])
        if not isinstance(joiner, str):
            raise JSPRException(['invalid-str.join-with', joiner])
    else:
        seq = unary('str.join', args)
        joiner = ''
    if not isinstance(seq, Iterable):
        raise JSPRException(['invalid-str.join-seq', seq])
    return joiner.join(seq)


@Function
def elem_fn(args: Arguments, env: Environment) -> Value:
    seq, at = unpack_kwlist('elem', args, ('at', ))
    if not isinstance(seq, (str, PySequence)):
        raise JSPRException(['invalid-elem-seq', seq])
    if not isinstance(at, (int, float)):
        raise JSPRException(['invalid-elem-at', at])
    at = round(at)
    try:
        return seq[at]
    except IndexError:
        raise JSPRException(['invalid-elem-index', seq, at])


@Function
def len_fn(args: Arguments, env: Environment) -> int:
    seq = unary('len', args)
    if isinstance(seq, (str, PySequence, PyMapping, KeywordSequence)):
        return len(seq)
    raise JSPRException(['invalid-len', seq])


@Function
def slice_fn(args: Arguments, env: Environment) -> Value:
    if isinstance(args, KeywordSequence):
        seq = args.first_arg
        if not isinstance(seq, (str, PySequence)):
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
        if not isinstance(seq, (str, PySequence)):
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
def id_fn(args: Arguments, env: Environment) -> Value:
    val = unary('id', args)
    return val


@Function
def iota_fn(args: Arguments, env: Environment) -> PySequence[int]:
    frm = 0
    to = 0
    if len(args) == 0:
        return itertools.count()
    elif len(args) == 1:
        to = unary('iota', args)
    else:
        frm, to = unpack_kwlist('iota', args, ['to'])
    if isinstance(frm, int) and to == 'inf':
        return itertools.count(frm)

    if not isinstance(frm, int) or not isinstance(to, int):
        lang.raise_(['invalid-iota-arg', [frm, to], '`iota` expects integer arguments'])
    return range(frm, to)


@Function
def reduce_fn(args: Arguments, env: Environment) -> Value:
    seq, val, by = unpack_kwlist('reduce', args, ['from', 'by'])
    if not isinstance(seq, Iterable):
        lang.raise_(['invalid-reduce-args', [seq, val, by], 'The first argument must be iterable'])
    if not callable(by):
        lang.raise_(['invalid-reduce-args', [seq, val, by], 'The "by" argument of reduce must be a callable object'])
    for x in seq:
        val = by([val, x], env.new_child())
    return val


@Function
def iter_map_fn(args: Arguments, env: Environment) -> Value:
    iterable, project = unpack_kwlist('iter.map', args, ['by'])
    return (project([it], env) for it in iterable)


@Function
def iter_take_fn(args: Arguments, env: Environment) -> Iterable[Value]:
    n, its = unpack_kwlist('iter.take', args, ['from'])
    return (it for it, _ in zip(its, range(n)))


def _lazy_eval_args(env: Environment, args: Arguments) -> Iterable[Value]:
    if isinstance(args, PySequence):
        return (env.eval(v) for v in args)
    else:
        return (eval_kw_pair(env, p)[1] for p in args)


def _hard_bool(arg: Value, err: str) -> bool:
    if not isinstance(arg, bool):
        raise JSPRException([err, arg])
    return arg


CompareResult = Literal['lt', 'gt', 'eq']


def _compare_seq(left: Sequence, right: Sequence, env: Environment) -> CompareResult:
    pairs = zip(left, right)
    for lval, rval in pairs:
        r = compare_fn.fn([lval, rval], env)
        if r != 'eq':
            return cast(CompareResult, r)
    if len(left) < len(right):
        return 'lt'
    if len(left) > len(right):
        return 'gt'
    return 'eq'


def _compare_mapping(left: PyMapping[str, Value], right: PyMapping[str, Value], env: Environment) -> CompareResult:
    lkeys = list(left.keys())
    rkeys = list(right.keys())
    lkeys.sort()
    rkeys.sort()
    key_comp = _compare_seq(lkeys, rkeys, env)
    if key_comp != 'eq':
        return key_comp
    for k in lkeys:
        lval = left[k]
        rval = right[k]
        comp = compare_fn.fn([lval, rval], env)
        if comp != 'eq':
            return comp
    return 'eq'


_CompType = Function
if TYPE_CHECKING:
    # Python 3.9 has a bug parsing this as a direct decoration:
    _CompType = Function[CompareResult]


@_CompType
def compare_fn(args: Arguments, env: Environment) -> CompareResult:
    left, right = unpack_kwlist('compare', args, ['with'])
    if is_sequence(left) and is_sequence(right):
        return _compare_seq(left, right, env)
    if is_map(left) and is_map(right):
        return _compare_mapping(left, right, env)
    left: Any
    right: Any
    try:
        if left < right:
            return 'lt'
        elif left > right:
            return 'gt'
        else:
            assert left == right, ('Impossible comparison', left, right)
            return 'eq'
    except TypeError:
        raise JSPRException(['invalid-compare', left, right])


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


def _do_is(args: KeywordSequence, arg_it: Iterator[tuple[str, Value]], lhs: Value, env: Environment) -> bool:
    pair = next(arg_it, Undefined)
    if pair is Undefined:
        if lhs is True:
            return lhs
        elif lhs is False:
            return lhs
        else:
            lang.raise_(['invalid-test-value', lhs, args])
    # Find the result
    oper, rhs_expr = pair
    if oper == 'and':
        if not _hard_bool(lhs, 'invalid-test-and-condition'):
            return False
        rhs = env.eval(rhs_expr)
        return _do_is(args, arg_it, rhs, env)

    if oper == 'or':
        if _hard_bool(lhs, 'invalid-test-or-condition'):
            return True
        rhs = env.eval(rhs_expr)
        return _do_is(args, arg_it, rhs, env)

    rhs = env.eval(rhs_expr)
    new_val: Value

    if oper in ('eq', 'equal-to'):
        new_val = lhs == rhs
        return _do_is(args, arg_it, new_val, env)
    elif oper in ('neq', 'not-equal-to'):
        new_val = lhs != rhs
    elif oper in ('gt', 'greater-than', 'lt', 'less-than', 'gte', 'lte', 'greater-or-equal-to', 'at-least',
                  'less-or-equal-to', 'at-most'):
        comp = compare_fn.fn([lhs, rhs], env)
        oper = {
            'greater-than': 'gt',
            'less-than': 'lt',
            'greater-or-equal-to': 'gte',
            'less-or-equal-to': 'lte',
            'at-least': 'gte',
            'at-most': 'lte',
        }.get(oper, oper)
        new_val = comp in {
            'gt': ('gt', ),
            'lt': ('lt', ),
            'gte': ('gt', 'eq'),
            'lte': ('lt', 'eq'),
        }[oper]
    elif oper == 'in':
        if not hasattr(rhs, '__contains__'):
            lang.raise_(['invalid-test-in', lhs, rhs])
        new_val = lhs in cast(Iterable[Value], rhs)
    elif oper == 'not-in':
        if not hasattr(rhs, '__contains__'):
            lang.raise_(['invalid-test-not-in', lhs, rhs])
        new_val = lhs not in cast(Iterable[Value], rhs)
    else:
        lang.raise_(['invalid-test-oper', oper, lhs, rhs])

    return _do_is(args, arg_it, new_val, env)


@SpecialForm
def test_sf(args: Arguments, env: Environment) -> bool:
    if not isinstance(args, KeywordSequence):
        lang.raise_(['invalid-test-args', args])
    arg_it = iter(args)
    first_val = env.eval(next(arg_it)[1])
    return _do_is(args, arg_it, first_val, env)


@SpecialForm
def get_current_env_fn(args: Arguments, env: Environment) -> Value:
    args = not_kwlist(args)
    if args != []:
        raise JSPRException(['invalid-args', '__env__', args])
    return env


@SpecialForm
def dunder_eval(args: Arguments, env: Environment) -> Value:
    from . import lang
    expr = unary('__eval__', args)
    return lang.eval_expression(expr, env)


@SpecialForm
def dunder_eval_do_seq(args: Arguments, env: Environment) -> Value:
    from . import lang
    seq = unary('__eval_do_seq__', args)
    return lang.eval_do_seq(seq, env)


class _Sequence(Module):
    _FUNCS = {
        'len': len_fn,
        'elem': elem_fn,
        'slice': slice_fn,
        'join': join_fn,
        'head': Function.from_py(lambda v: next(iter(v))),
        'tail': Function.from_py(lambda s: s[1:]),
        'seq': Function.from_py(lambda s: list(s)),
    }

    def __init__(self) -> None:
        super().__init__('seq', _Sequence._FUNCS)

    def __call__(self, args: Arguments, env: Environment) -> Value:
        return seq_sf(args, env)


def load_kernel(env: Environment) -> None:
    # Special forms
    env.define_fn('__env__', get_current_env_fn)
    env.define_fn('__eval__', dunder_eval)
    env.define_fn('__eval_do_seq__', dunder_eval_do_seq)
    env.define_fn('if', if_sf)
    env.define_fn('cond', cond_sf)
    env.define_fn('lambda', lambda_sf)
    env.define_fn('macro', macro_sf)
    env.define_fn('quote', quote_sf)
    env.define_fn('quasiquote', quasiquote_sf)
    env.define_fn('do', do_sf)
    env.define_fn('let', let_sf)
    env.define_fn('ref', ref_sf)
    env.define_fn('seq', _Sequence())
    env.define('iter', Module('iter', {
        'reduce': reduce_fn,
        'map': iter_map_fn,
        'take': iter_take_fn,
        'iota': iota_fn,
    }))
    env.define(
        'str',
        Module('str', {
            'join': str_join_fn,
            'str': Function.from_py(lambda s: str(s)),
            'repr': Function.from_py(lambda s: repr(s)),
        }))
    env.define_fn('map', map_sf)
    env.define_fn('or', or_sf)
    env.define_fn('and', and_sf)
    env.define_fn('xor', xor_sf)
    env.define_fn('assert', assert_sf)
    env.define_fn('test', test_sf)
    # Regular predefined functions
    env.define_fn('raise', raise_fn)
    env.define_fn('apply', apply_fn)
    env.define_fn('eval', eval_fn)
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
    env.define_fn('compare', compare_fn)
    env.define_fn('lt', _make_binop('lt', 'than', lambda l, r: compare_fn.fn([l, r], Environment()) == 'lt'))
    env.define_fn('gt', _make_binop('gt', 'than', lambda l, r: compare_fn.fn([l, r], Environment()) == 'gt'))
    env.define_fn('gte', _make_binop('gte', 'than', lambda l, r: compare_fn.fn([l, r], Environment()) != 'lt'))
    env.define_fn('lte', _make_binop('lte', 'than', lambda l, r: compare_fn.fn([l, r], Environment()) != 'gt'))
    env.define_fn('same', _make_binop('same', 'as', lambda l, r: l is r))
