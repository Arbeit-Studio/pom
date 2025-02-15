from __future__ import annotations

from collections import ChainMap, defaultdict
from collections.abc import Iterable
from functools import partial
from inspect import getmembers
from typing import Callable, Mapping, Tuple, Type, TypeVar, Union

TS = TypeVar("TS")
TT = TypeVar("TT")

SourceType = Union[Type[TS], Tuple[Type[TS], ...]]
TargetType = Type[TT]
Source = Union[TS, Tuple[TS]]


def prop():
    def prop(x):
        return x

    return prop


class Mapper:
    def __init__(self):
        self.mappings = defaultdict(partial(defaultdict, partial(defaultdict, prop)))

    def add_mapping(self, *, source: SourceType, target: TargetType, mapping=None):
        self.mappings[source][target].update(mapping or {})

    def map(self, source: TS, target_type: TargetType, skip_init=False) -> TargetType:
        if isinstance(source, Iterable):
            props = ChainMap(*[dict(self._get_props(so)) for so in source])
            maps = self.mappings[tuple(type(so) for so in source)][target_type]
        else:
            props = ChainMap(dict(self._get_props(source)))
            maps = self.mappings[type(source)][target_type]
        mapped = self._maps(maps, props)
        try:
            if skip_init:
                instance = object.__new__(target_type)
                for prop in mapped:
                    setattr(instance, prop[0], prop[1])
                return instance
            return target_type(**{k: v for k, v in mapped})
        except TypeError as e:
            if isinstance(source, Iterable):
                raise TypeError(
                    f"Source objects ({', '.join([type(so).__name__ for so in source])}) are missing required properties for target object {target_type.__name__}: {e}"
                )

            raise TypeError(
                f"Source object {type(source).__name__} is missing required properties for target object {target_type.__name__}: {e}"
            )

    def _get_props(self, obj) -> list[tuple]:
        return [prop for prop in getmembers(obj) if not prop[0].startswith("_")]

    def _maps(self, maps: dict[str, Callable], props: Mapping) -> list[tuple]:
        return list(map(lambda p: (p[0], maps[p[0]](p[1])), props.items()))
