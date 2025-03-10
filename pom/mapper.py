from __future__ import annotations

from collections import ChainMap, defaultdict
from collections.abc import Iterable
from functools import partial
from inspect import getmembers, isclass
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
        self.exclusions = defaultdict(partial(defaultdict, list))

    def add_mapping(
        self,
        *,
        source: Union[SourceType, TS],
        target: TargetType,
        mapping: dict = None,
        exclusions: list = None,
    ):
        if mapping:
            self.guard_all_mappings_in_source(source, mapping)
        source_type = self._get_source_type(source)
        self.mappings[source_type][target].update(mapping or {})
        self.exclusions[source_type][target].extend(exclusions or [])

    def guard_all_mappings_in_source(self, source, mapping):
        mapping_attrs = mapping.keys()
        if isinstance(source, Iterable):
            source_attrs = {m[0] for s in source for m in getmembers(s)}
        else:
            source_attrs = {m[0] for m in getmembers(source)}
        missing_attributes={attr for attr in mapping_attrs if attr not in source_attrs}
        
        if missing_attributes:
            missing_attributes = sorted(mapping_attrs)
            source_name = source.__name__ if isclass(source) else sorted({s.__name__ for s in source})
            if len(source_name) <= 1:
                source_name_string = f"source {source_name}"
            else:
                source_name_string = f"sources {', '.join(source_name[:-1])} and {source_name[-1]}" 
            if len(missing_attributes) <= 1:
                attributes_string = f"attribute {''.join(missing_attributes)}"
            else:
                attributes_string= f"attributes {', '.join(missing_attributes[:-1])} and {missing_attributes[-1]}"
            raise TypeError(
                f"Mapping {attributes_string} not found in {source_name_string}."
            )

    def map(
        self,
        source_instance: TS,
        target: Union[TT, type[TT]],
        skip_init: bool = False,
        extra: dict = None,
    ) -> TT:
        """Map source object(s) to target type.

        Args:
            source: Single object or iterable of objects to map from
            target_type: Type to map to
            skip_init: Skip __init__ when creating target instance
            extra: Additional attributes to set on target instance
        """
        target_is_type = isclass(target)
        skip_init = skip_init or not target_is_type
        target_type: type[TT] = target if target_is_type else type(target)
        # Get source properties
        props = self._get_source_props(
            source_instance, type(source_instance), target_type
        )

        # Get mapping rules
        source_type = self._get_source_type(source_instance)
        maps = self.mappings[source_type][target_type]

        # Apply mappings
        mapped_attrs = dict(self._maps(maps, props))

        # Create target instance
        try:
            if skip_init:
                if not target_is_type:
                    return self._setattr(target, mapped_attrs, extra)
                else:
                    target_instance = object.__new__(target_type)
                    return self._setattr(target_instance, mapped_attrs, extra)
            return target_type(**mapped_attrs, **(extra or {}))
        except TypeError as e:
            self._handle_mapping_error(source_instance, target, e)

    def _get_source_type(self, source_instance):
        source_type = (
            tuple(so if isclass(so) else type(so) for so in source_instance)
            if isinstance(source_instance, Iterable)
            else source_instance if isclass(source_instance) else type(source_instance)
        )
        
        return source_type

    def _get_source_props(
        self, source, source_type: type[TT], target_type: type[TS]
    ) -> ChainMap:
        """Extract properties from source object(s)."""
        if isinstance(source, Iterable):
            return ChainMap(
                *[dict(self._get_props(so, source_type, target_type)) for so in source]
            )
        return ChainMap(dict(self._get_props(source, source_type, target_type)))

    def _setattr(self, instance: TT, attrs: dict, extra: dict = None) -> TT:

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

    def _get_props(
        self, obj, source_type: type[TT], target_type: type[TS]
    ) -> list[tuple]:
        return [
            prop
            for prop in getmembers(obj)
            if not prop[0].startswith("_")
            # TODO: handle the exclusions after getting the prop in another place
            and not prop[0] in self.exclusions[source_type][target_type]
        ]

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
