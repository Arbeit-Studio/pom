from __future__ import annotations

from collections import ChainMap, defaultdict
from collections.abc import Iterable
from dataclasses import fields, is_dataclass
from functools import partial
from inspect import Parameter, getmembers, isclass, signature
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    NoReturn,
    Tuple,
    Type,
    TypeVar,
    Union,
)

TS = TypeVar("TS")
TT = TypeVar("TT")

SourceType = Union[Type[TS], Tuple[Type[TS], ...]]
TargetType = Type[TT]
Source = Union[TS, Tuple[TS], SourceType]
MapFunction = Callable[[Any], Any]
MappingDict = Dict[str, Union[str, MapFunction]]
MappingSpec = Union[MappingDict, List[str]]


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
        mapping: MappingSpec = None,
        exclusions: list = None,
    ):
        self._guard_all_mappings_in_source(source, mapping)
        if isinstance(mapping, List):
            mapping = {name: name for name in mapping}
        source_type = self._get_source_type(source)
        self.mappings[source_type][target].update(mapping or {})
        self.exclusions[source_type][target].extend(exclusions or [])

    def _guard_all_mappings_in_source(self, source, mapping: MappingSpec):
        if not mapping:
            return
        if isinstance(mapping, Mapping):
            mapping_attrs = mapping.keys()
        if isinstance(mapping, List):
            mapping_attrs = mapping
        if isinstance(source, Iterable):
            source_attrs = {m[0] for s in source for m in getmembers(s)} | {
                m[0]
                for s in source
                for m in list(signature(s.__init__).parameters.keys())[1:]
            }
        else:
            source_attrs = {m[0] for m in getmembers(source)} | set(
                list(signature(source.__init__).parameters.keys())[1:]
            )
        missing_attributes = {
            attr for attr in mapping_attrs if attr not in source_attrs
        }

        if missing_attributes:
            source_name_string, attributes_string = (
                self._format_missing_attrs_error_message(source, mapping_attrs)
            )
            raise TypeError(
                f"Mapping {attributes_string} not found in {source_name_string}."
            )

    def _format_missing_attrs_error_message(self, source, mapping_attrs):
        missing_attributes = sorted(mapping_attrs)
        source_name = self._get_source_name(source)
        if isinstance(source_name, str):
            source_name_string = f"source {source_name}"
        elif isinstance(source_name, Iterable):
            source_name_string = (
                f"sources {', '.join(source_name[:-1])} and {source_name[-1]}"
            )
        else:
            raise RuntimeError("Can't define source class name")
        if len(missing_attributes) <= 1:
            attributes_string = f"attribute {''.join(missing_attributes)}"
        else:
            attributes_string = f"attributes {', '.join(missing_attributes[:-1])} and {missing_attributes[-1]}"
        return source_name_string, attributes_string

    def _get_source_name(self, source: Source):
        if isinstance(source, Iterable):
            return sorted({s.__name__ for s in source})
        if isclass(source):
            return source.__name__
        if isinstance(source, type) is False:
            return type(source).__name__
        raise RuntimeError("Can't define source class name")

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
        extra = extra or {}
        target_is_type = isclass(target)
        target_type: type[TT] = target if target_is_type else type(target)
        skip_init = skip_init or not target_is_type
        source_type = self._get_source_type(source_instance)

        # Get source properties
        props = self._get_source_props(
            source_instance, type(source_instance), target_type
        )

        self._guard_no_missing_attrs(
            source_instance, target_type, source_type, extra, target
        )

        # Get mapping rules
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
            return target_type(
                **{
                    k: v
                    for k, v in mapped_attrs.items()
                    if k
                    in set(list(signature(target_type.__init__).parameters.keys())[1:])
                },
                **(extra or {}),
            )
        except TypeError as e:
            self._handle_mapping_error(source_instance, target, e)

    def _guard_no_missing_attrs(
        self, source_instance, target_type, source_type, extra, target
    ):
        missing_prop = set(self.exclusions[source_type][target_type]) - set(
            extra.keys()
        )

        target_attrs = self._get_target_attrs_without_default_values(
            target_type, target
        )

        trouble_props = missing_prop & target_attrs
        if not trouble_props:
            return
        source_name = self._get_source_name(source_instance)
        if len(trouble_props) == 1:
            raise RuntimeError(
                f"{target_type.__name__} requires argument {trouble_props.pop()} which is excluded from mapping {source_name} -> {target_type.__name__}"
            )
        if len(trouble_props) > 1:
            sorted_trouble_props_names = sorted(trouble_props)
            trouble_pros_names = f"{', '.join(sorted_trouble_props_names[:-1])} and {sorted_trouble_props_names[-1]}"
            raise RuntimeError(
                f"{target_type.__name__} requires arguments {trouble_pros_names} which are excluded from mapping {source_name}  -> {target_type.__name__}"
            )

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
        self, source_object, source_type: type[TT], target_type: type[TS]
    ) -> list[tuple]:
        return [
            s_prop
            for s_prop in getmembers(source_object)
            if not s_prop[0].startswith("_")
            # TODO: handle the exclusions after getting the prop in another place
            and not s_prop[0] in self.exclusions[source_type][target_type]
            # does not copy if prop not in target object
            # and s_prop[0] in t_props_names
        ]

    def _get_target_attrs_without_default_values(self, target_type, target):
        if is_dataclass(target_type):
            t_props_names = {field.name for field in fields(target_type)}
        else:
            t_props_names = set(
                list(
                    name
                    for name, param in signature(
                        target_type.__init__
                    ).parameters.items()
                    # get only parameter without default value
                    if param.default is Parameter.empty
                )[1:]
                # minus the parameters already in the target, like class attributes and already instantiated objects
            ) - {t_prop[0] for t_prop in getmembers(target)}
        return t_props_names

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
