from pathlib import Path
import itertools
from typing import Any, Mapping, Optional, Union, cast
from typing_extensions import TypedDict

import yaml
import pytest

from jspr.runtime import Environment, Function, JSPRException, JSONData, Value
from jspr.kernel import load_kernel
from jspr.mod import Module

THIS_DIR = Path(__file__).absolute().parent
TEST_FILES = list(THIS_DIR.glob('test_*.yml'))

RescueCase = TypedDict('RescudeCase', {'code': JSONData, 'rescue': Any})
ResultCase = TypedDict('Case', {'code': JSONData, 'expect': Any})
Case = Union[RescueCase, ResultCase]
_TestFileContent = TypedDict('_TestFileContent', {'cases': 'dict[str, Case]'})

texts = ((f, f.read_text()) for f in TEST_FILES)
yaml_docs = ((fpath, yaml.safe_load(t)) for fpath, t in texts)
cases_by_file = ((fpath, cast(_TestFileContent, doc)['cases']) for fpath, doc in yaml_docs)

cases = itertools.chain.from_iterable(
    ((fpath, casename, casedata) for casename, casedata in cases.items()) for fpath, cases in cases_by_file)

cases, cases_1 = itertools.tee(cases, 2)
case_ids = [f'{fpath.name}/{casename}' for fpath, casename, _ in cases_1]


def add(a: Value, b: Value) -> Value:
    return a + b


def manip_str(given: str, prepend: Optional[str] = None, append: Optional[str] = None) -> str:
    if prepend is not None:
        given = prepend + given
    if append is not None:
        given = given + append
    return given


_TEST_MODULE = Module('testmod', {
    'add': Function.from_py(add),
    'manip-str': Function.from_py(manip_str),
})


@pytest.mark.parametrize('filepath,casename,case', cases, ids=case_ids)
def test_evaluate(filepath: Path, casename: str, case: Case) -> None:
    env = Environment()
    load_kernel(env)
    # Load in the initial environment
    predef: Mapping[str, Value] = case.get('env', {})
    for pair in predef.items():
        env.define(pair[0], pair[1])

    env.define('testmod', _TEST_MODULE)

    code = case['code']
    if 'expect' in case:
        result = env.eval_do_seq(code)
        expected = case['expect']
        assert result == expected
    elif 'rescue' in case:
        try:
            result = env.eval_do_seq(code)
            pytest.fail('Expected a failure, but none occurred')
        except JSPRException as e:
            assert e.value == case['rescue']
    else:
        pytest.fail('Invalid test case: Expect a "rescue" or "expect" key')
