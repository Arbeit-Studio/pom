from __future__ import annotations

from collections import ChainMap, defaultdict
from collections.abc import Iterable
from functools import partial
from inspect import getmembers
from typing import Any, Callable, Mapping, NoReturn, Tuple, Type, TypeVar, Union

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

    def map(
        self,
        source: TS,
        target_type: TargetType,
        skip_init: bool = False,
        extra: dict = None,
    ) -> TargetType:
        """Map source object(s) to target type.

        Args:
            source: Single object or iterable of objects to map from
            target_type: Type to map to
            skip_init: Skip __init__ when creating target instance
            extra: Additional attributes to set on target instance
        """
        # Get source properties
        props = self._get_source_props(source)

        # Get mapping rules
        source_type = (
            tuple(type(so) for so in source)
            if isinstance(source, Iterable)
            else type(source)
        )
        maps = self.mappings[source_type][target_type]

        # Apply mappings
        mapped_attrs = dict(self._maps(maps, props))

        # Create target instance
        try:
            if skip_init:
                return self._create_without_init(target_type, mapped_attrs, extra)
            return target_type(**mapped_attrs, **(extra or {}))
        except TypeError as e:
            self._handle_mapping_error(source, target_type, e)

    def _get_source_props(self, source) -> ChainMap:
        """Extract properties from source object(s)."""
        if isinstance(source, Iterable):
            return ChainMap(*[dict(self._get_props(so)) for so in source])
        return ChainMap(dict(self._get_props(source)))

    def _create_without_init(
        self, target_type: type[TT], attrs: dict, extra: dict = None
    ) -> TT:
        """Create instance without calling __init__."""
        instance = object.__new__(target_type)
        for name, value in attrs.items():
            setattr(instance, name, value)
        for name, value in (extra or {}).items():
            setattr(instance, name, value)
        return instance

    def _handle_mapping_error(
        self, source, target_type: Type, error: TypeError
    ) -> NoReturn:
        """Handle mapping errors with descriptive messages."""
        if isinstance(source, Iterable):
            source_types = ", ".join(type(so).__name__ for so in source)
            raise TypeError(
                f"Source objects ({source_types}) are missing required properties "
                f"for target object {target_type.__name__}: {error}"
            )
        raise TypeError(
            f"Source object {type(source).__name__} is missing required properties "
            f"for target object {target_type.__name__}: {error}"
        )

    def _get_props(self, obj) -> list[tuple]:
        return [prop for prop in getmembers(obj) if not prop[0].startswith("_")]

    def _maps(self, maps: dict[str, Callable], props: Mapping) -> list[tuple]:
        result = []
        for prop_name, prop_value in props.items():
            transform = maps[prop_name]
            if callable(transform):
                mapped_value = transform(prop_value)
                result.append((prop_name, mapped_value))
            if isinstance(transform, str):
                result.append((transform, prop_value))
            if isinstance(transform, tuple):
                result.append((transform[0], transform[1](prop_value)))

        return result
