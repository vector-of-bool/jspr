from typing import Sequence

import pytest

from . import lang
from .runtime import Environment, JSPRException, Value


@pytest.fixture()
def env() -> Environment:
    return Environment()


def test_atomic_values(env: Environment) -> None:
    values = ['asdf', 1, 3.1, None, True, False]
    for val in values:
        assert lang.eval_expression(val, env) == val


def test_simple_env(env: Environment) -> None:
    env.define('foo', 44)
    result = lang.eval_expression('.foo', env)
    assert result == 44


def test_bad_lookup(env: Environment) -> None:
    try:
        lang.env_lookup(env, 'asdfasdf')
        pytest.fail('Did not throw')
    except JSPRException as e:
        assert e.value == ['env-name-error', 'asdfasdf']

    try:
        lang.eval_expression('.asdf-jkl;', env)
        pytest.fail('Did not throw')
    except JSPRException as e:
        assert e.value == ['env-name-error', 'asdf-jkl;']


def test_array_eval(env: Environment) -> None:
    arr: Sequence[Value] = []
    assert lang.eval_expr_array(arr, env) == []
    arr = ['foo']
    env.define_fn('foo', lambda _env, _args: 6)
    assert lang.eval_expr_array(arr, env) == 6


def test_bad_kwlist_call(env: Environment) -> None:
    try:
        lang.apply_kwlist(['nope'], env)
        pytest.fail('Did not raise')
    except JSPRException as e:
        assert e.value == ['invalid-kw-apply', ['nope']]


def test_bad_call(env: Environment) -> None:
    env.define('foo', 8)
    try:
        lang.eval_expr_array(['foo'], env)
        pytest.fail('Did not raise')
    except JSPRException as e:
        assert e.value == ['invalid-apply', 8, []]


def test_eval_array(env: Environment) -> None:
    env.define('foo', 11)
    env.define('bar', 8)
    result = lang.eval_array(['foo', '.foo', 'bar', '.bar', None, 12], env)
    assert result == ['foo', 11, 'bar', 8, None, 12]


def test_eval_seq(env: Environment) -> None:
    result = lang.eval_expr_seq([1, 2, 1, 8, 'sting', None, 7], env)
    assert result == 7
    result = lang.eval_expr_seq([], env)
    assert result == None