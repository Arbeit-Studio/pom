from __future__ import annotations
from collections import defaultdict, ChainMap
from collections.abc import Iterable
from inspect import getmembers
from functools import partial
from typing import TypeVar, Type, Union, Tuple

TS = TypeVar("TS")
TT = TypeVar("TT")

SourceType = Union[Type[TS], Tuple[Type[TS]]]
TargetType = Type[TT]
Source = Union[TS, Tuple[TS]]

def prop():
    def prop(x):
        return x
    return prop


class Mapper:
    def __init__(self):
        self.mappings = defaultdict(
            partial(defaultdict, partial(defaultdict, prop))
        )

    def add_mapping(self, *, source: SourceType, target: TargetType, mapping=None):
        self.mappings[source][target].update(mapping or {})

    def map(self, source: TS, target_type: TargetType, skip_init=True) -> TT:
        if isinstance(source, Iterable):
            props = ChainMap(*[dict(self._get_props(so)) for so in source])
            maps = self.mappings[tuple(type(so) for so in source)][target_type]
        else:
            props = ChainMap(dict(self._get_props(source)))
            maps = self.mappings[source][target_type]
        mapped = self._maps(maps, props)
        if skip_init:
            instance = target_type.__new__(target_type)
            for prop in mapped:
                setattr(instance, prop[0], prop[1])
        return instance
        return target_type(**{k: v for k, v in mapped})

    def _get_props(self, obj) -> list[tuple]:
        return [prop for prop in getmembers(obj) if not prop[0].startswith("_")]

    def _maps(self, maps: dict[callable], props: dict) -> list[tuple]:
        return list(map(lambda p: (p[0], maps[p[0]](p[1])), props.items()))
