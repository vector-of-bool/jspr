import pytest

from .runtime import Environment
from . import kernel


@pytest.fixture()
def env() -> Environment:
    e = Environment()
    kernel.load_kernel(e)
    return e


def test_load_kernel(env: Environment) -> None:
    "Load the kernel into an environment"
    # Done by the test fixture


def test_simple_add(env: Environment) -> None:
    assert env.eval(['+', 3, 4]) == 7


def test_simple_cond(env: Environment) -> None:
    expr = ['cond', [[False, 7], [True, 91]]]
    assert (env.eval(expr)) == 91
    expr = [{'cond': [[False, 7], [True, 91]]}]
    assert (env.eval(expr)) == 91


def test_key_quoting(env: Environment) -> None:
    let_expr = [{'let': 'a'}, {'be\'': [{'foo': 'bar'}]}]
    expr = {'a=': [{'do': [let_expr, '.a']}]}
    env.eval(expr)
    assert env['a'] == [{'foo': 'bar'}]


def test_simple_lambda(env: Environment) -> None:
    expr = [
        'do',
        [
            {
                'fun=': ['lambda', ['a'], '.a']
            },
            ['fun', 9],
        ],
    ]
    assert env.eval(expr) == 9


def test_auto_array(env: Environment) -> None:
    expr = {'-do': [1, 2, 9]}
    assert env.eval(expr) == 9


def test_simple_macro(env: Environment) -> None:
    expr = [
        'do',
        [
            {
                'm=': ['macro', [], ['quote', '.value']]
            },
            {
                'value=': 8
            },
            ['m'],
        ],
    ]
    assert env.eval(expr) == 8
