"""
Types for the JSPR runtime functions and function handling
"""

from __future__ import annotations

import enum
import functools
import inspect
from typing import (Any, Callable, Generic, Iterable, Iterator, Mapping, Optional)
from typing import Sequence as PySequence
from typing import Type, TypeVar, Union, cast

from typing_extensions import Protocol, TypeGuard

#: Unbounded type variable
T = TypeVar('T')

#: Atomic value: strings, integers, floats, bool, and null
Atom = Union[str, int, float, bool, None]

#: A recrusive JSON-like data structure
JSONData = Union[Atom, PySequence['JSONData'], Mapping[str, 'JSONData']]


class UndefinedType(enum.Enum):
    "Type of the 'Undefined' constant"
    Value = 0


#: The instance of 'UndefinedType'
Undefined = UndefinedType.Value

#: An instance of 'T' or 'Undefined'
Maybe = Union[T, UndefinedType]


class Unknown(Protocol):
    """
    Type that has no semantics or properties.
    """


_EnvironmentT = TypeVar('_EnvironmentT', bound='Environment')


class JSPRException(BaseException):
    def __init__(self, value: Value) -> None:
        super().__init__(value)
        self._value = value

    @property
    def value(self):
        """Obtain the value of this exception"""
        return self._value


class Function(Generic[T]):
    def __init__(self, func: Callable[[Arguments], T]) -> None:
        self._func = func

    def __call__(self, args: Arguments, env: Environment) -> T:
        args = eval_args(env.new_child(), args)
        return self._func(args)

    def __repr__(self) -> str:
        return f'<Function {self._func!r}>'

    @property
    def fn(self) -> Callable[[Arguments], T]:
        """The function that is wrapped"""
        return self._func

    @classmethod
    def from_py(cls, name: str, fn: Callable[..., T]) -> Function[T]:
        sig = inspect.signature(fn)
        kw_names = list(sig.parameters.keys())[1:]
        from .util import unpack_kwlist

        @functools.wraps(fn)
        def invoke(args: Arguments) -> T:
            al = unpack_kwlist(name, args, kw_names)
            return fn(*al)

        return cls(invoke)


class SpecialForm:
    def __init__(self, func: Applicable) -> None:
        self._func = func
        self._name = getattr(func, '__name__', '<unnamed>')

    def __repr__(self) -> str:
        return f'<SpecialForm "{self._name}">'

    def __call__(self, args: Arguments, env: Environment) -> Value:
        return self._func(args, env)


def eval_args(env: Environment, args: Arguments) -> Arguments:
    if isinstance(args, KeywordSequence):
        return eval_kwlist(env, args)
    else:
        return eval_arglist(env, args)


def eval_arglist(env: Environment, args: PositionalArgs) -> PositionalArgs:
    return tuple(env.eval(a) for a in args)


def eval_kw_pairs(env: Environment, pairs: Iterable[tuple[str, Value]]) -> Iterable[tuple[str, Value]]:
    return (eval_kw_pair(env, pair) for pair in pairs)


def eval_kwlist(env: Environment, args: KeywordSequence) -> KeywordSequence:
    pairs = eval_kw_pairs(env, args)
    return KeywordSequence(pairs)


def eval_kw_pair(env: Environment, pair: tuple[str, Value]) -> tuple[str, Value]:
    key, given = pair
    if key.endswith('\''):
        return (key[:-1], given)
    if key.endswith('`'):
        return (key[:-1], env.eval(['list', given]))
    return (key, env.eval(given))


def normalize_kw_pair(pair: tuple[str, Value]) -> tuple[str, Value]:
    key, given = pair
    if not key:
        return (key, given)
    last = key[-1]
    rkey = key[:-1]
    if last == "'":
        return rkey, ['quote', given]
    if last == '`':
        return rkey, ['list', given]
    return key, given


class Environment:
    """
    The environment in which a JSPR program is executing. Used for name lookup.
    """
    def __init__(self, parent: Optional[Environment] = None):
        self._names: dict[str, Value] = {}
        self._parent = parent

    @classmethod
    def root_jspr_context(cls: Type[_EnvironmentT]) -> _EnvironmentT:
        me = cls()
        return me

    def define(self, name: str, item: Value) -> None:
        self._names[name] = item

    def define_fn(self, name: str, fn: Applicable) -> None:
        self.define(name, fn)

    def __repr__(self) -> str:
        return f'<jspr.runtime.Environment object>'

    @property
    def parent(self) -> Optional[Environment]:
        """The parent context"""
        return self._parent

    def lookup(self, name: str) -> Maybe[Value]:
        """Look up the definition of the given name"""
        if name in self._names:
            return self._names[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return Undefined

    def __getitem__(self, key: str) -> Value:
        found = self.lookup(key)
        if found is Undefined:
            raise JSPRException(['env-name-error', key])
        return found

    def __jspr_getattr__(self, key: str) -> Value:
        found = self.lookup(key)
        if found is Undefined:
            raise JSPRException(['env-name-error', key])
        return found

    def __contains__(self, key: str) -> bool:
        return self.lookup(key) is not Undefined

    def eval(self, expr: Value) -> Value:
        eval = self.lookup('__eval__')
        if eval is Undefined:
            raise RuntimeError(f'No "__eval__" is defined in the environment')
        if not callable(eval):
            raise RuntimeError(f'The "__eval__" is this environment is not callable')
        eval = cast(Applicable, eval)
        return eval([expr], self)

    def eval_do_seq(self, expr: Value) -> Value:
        eval_seq = self.lookup('__eval_do_seq__')
        if eval_seq is Undefined:
            raise RuntimeError(f'No "__eval_do_seq__" is defined in the environment')
        if not callable(eval_seq):
            raise RuntimeError(f'The "__eval_do_seq__" is this environment is not callable')
        eval_seq = cast(Applicable, eval_seq)
        return eval_seq([expr], self)

    def apply(self, func: Value, args: Arguments) -> Value:
        apply = self.lookup('apply')
        if apply is Undefined:
            raise RuntimeError('No "apply" is defined in the environment')
        if not callable(apply):
            raise RuntimeError('The "apply" in this environment is not callable')
        apply = cast(Applicable, apply)
        return apply([func, args], self)

    def new_child(self) -> Environment:
        """
        Create a new environment with this one as its parent
        """
        return Environment(parent=self)

    def clone(self) -> Environment:
        """
        Create a clone of the environment at its current state.
        """
        new_env = Environment(self.parent)
        new_env._names = dict(self._names)
        return new_env


#: An iterable that can be used to construct a keyword list
KeywordPairIterable = Iterable["tuple[str, Value]"]


class KeywordSequence:
    def __init__(self, keywords: KeywordPairIterable) -> None:
        self.keywords = tuple(keywords)
        self._to_inspect = list(key for key, _ in self.keywords[1:])

    @property
    def first_arg(self) -> Value:
        """Get the first argument in the keyword list"""
        return self.keywords[0][1]

    @property
    def first_key(self) -> str:
        """Return the first key in the list (the function name)"""
        return self.keywords[0][0]

    def __len__(self) -> int:
        return len(self.keywords)

    def try_get(self, key: str, *, ignore_first: bool = False) -> Maybe[Value]:
        kws = self.keywords
        if ignore_first and kws:
            kws = kws[1:]
        for k, value in kws:
            if k == key:
                return value
        return Undefined

    def get(self, key: str, *, ignore_first: bool = False) -> Value:
        found = self.try_get(key, ignore_first=ignore_first)
        if found is Undefined:
            raise ValueError(f'Missing keyword argument "{key}"')
        return found

    def __iter__(self) -> Iterator[tuple[str, Value]]:
        return iter(self.keywords)

    def __repr__(self) -> str:
        pairs = (f'{k!r}={val!r}' for k, val in self)
        return f'<KeywordSequence [{", ".join(pairs)}]>'

    def keys(self) -> Iterator[str]:
        return (k for k, _ in self.keywords[1:])

    def raise_for_unused(self) -> None:
        if not self._to_inspect:
            return
        unused_str = ', '.join(f'"{s}"' for s in self._to_inspect)
        raise TypeError(f'Unexpected arguments: {unused_str}')

    def match(self, pairs: Mapping[str, T]) -> Optional[T]:
        given_keys = set(self.keys())
        for keylist, func in pairs.items():
            keyset = set(keylist.split(','))
            if keyset == given_keys:
                return func
        return None


class MacroClosure:
    def __init__(self, arglist: PySequence[str], body: Value, env: Environment) -> None:
        self.name = '<closure>'
        self.arglist = arglist
        self.body = body
        self.env = env

    def __call__(self, args: Arguments, caller_env: Environment) -> Value:
        inner_env = Environment(parent=self.env)
        inner_env.define('__recurse__', self)
        if isinstance(args, KeywordSequence):
            from .util import unpack_kwlist
            args = unpack_kwlist(self.name, args, self.arglist[1:])
        for key, arg in zip(self.arglist, args):
            inner_env.define(key, arg)
        return inner_env.eval(self.body)


class Closure(MacroClosure):
    def __call__(self, args: Arguments, caller_env: Environment) -> Value:
        args = eval_args(caller_env, args)
        return super().__call__(args, caller_env)


class Macro:
    def __init__(self, func: Applicable) -> None:
        self._func = func

    def __call__(self, args: Arguments, caller_env: Environment) -> Value:
        new_code = self._func(args, caller_env)
        return caller_env.eval(new_code)


def quasiquote(val: Value, env: Environment) -> Value:
    if isinstance(val, (str, int, float, bool)):
        return val
    if is_sequence(val):
        if len(val) == 2 and val[0] == 'unquote':
            return env.eval(val[1])
        if len(val) == 1 and is_map(val[0]) and next(iter(val[0].keys())) == 'unquote':
            return env.eval(next(iter(val[0].values())))
        return [quasiquote(v, env) for v in val]
    if is_map(val):
        return {quasiquote(k, env): quasiquote(v, env) for k, v in val.items()}
    return val


"""
A value that is present in the JSPR runtime. Can be anything, but can be narrowed down with some checks.
"""
Value = Union[Atom, JSONData, 'Applicable', Any, 'Map', 'Sequence']
Map = Mapping[str, Value]
Sequence = PySequence[Value]
PositionalArgs = PySequence[Value]
Arguments = Union[PositionalArgs, KeywordSequence]

PositionalFunction = Callable[[PositionalArgs], Value]
KeywordFunction = Callable[[KeywordSequence], Value]


def is_map(m: Value) -> TypeGuard[Map]:
    return isinstance(m, Mapping)


def is_sequence(m: Value) -> TypeGuard[Sequence]:
    return isinstance(m, PySequence) and not isinstance(m, str)


class Applicable(Protocol):
    def __call__(self, args: Arguments, env: Environment) -> Value:
        ...
