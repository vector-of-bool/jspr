from typing import ClassVar, Iterable, Mapping

from jspr.lang import raise_

from .runtime import Value


def _auto_name(py_name: str) -> str:
    return py_name.replace('_', '-').strip('-')


class Module:
    def __init__(self, name: str, items: Mapping[str, Value]) -> None:
        self._name = name
        self._items = dict(items)

    @property
    def name(self) -> str:
        """The name of the module"""
        return self._name

    def keys(self) -> Iterable[str]:
        """Get the names that are available in this module"""
        return self._items.keys()

    def __contains__(self, key: str) -> bool:
        return key in self._items

    def __jspr_getattr__(self, key: str) -> Value:
        try:
            return self._items[key]
        except KeyError:
            raise_(['mod-name-error', self.name, key])

    def __repr__(self) -> str:
        return f'<jspr.Module name="{self.name}">'


class AutoModule(Module):
    jspr_mod_name: ClassVar[str]
    jspr_mod_fns: ClassVar[Iterable[str]]

    def __init__(self) -> None:
        super().__init__(self.jspr_mod_name, {_auto_name(k): getattr(self, k) for k in self.jspr_mod_fns})
