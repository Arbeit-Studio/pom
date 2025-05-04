from __future__ import annotations

from collections import ChainMap, defaultdict
from collections.abc import Iterable
from functools import partial
from inspect import Parameter, getmembers, isclass, signature
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    NoReturn,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None

TS = TypeVar("TS")
TT = TypeVar("TT")

SourceType = Union[Type[TS], Tuple[Type[TS], ...]]
TargetType = Type[TT]
Source = Union[TS, Tuple[TS]]
MapFunction = Callable[[Any], Any]
MappingDict = Dict[str, Union[str, MapFunction]]
MappingSpec = Union[MappingDict, Set[str]]


class PydanticBaseModelAdapter:
    def __init__(self, BaseModel: Type) -> None:
        self.BaseModel = BaseModel

    def get_public_attrs(self, obj: Any) -> List[Tuple[str, Any]]:
        # Use BaseModel.dict for field extraction
        if isclass(obj) and issubclass(obj, self.BaseModel):
            # When passed a BaseModel class, return its __fields__ names with None as values.
            return [(field, None) for field in obj.__fields__.keys()]
        elif isinstance(obj, self.BaseModel):
            # For BaseModel instances, use dict() to extract field values.
            return list(obj.dict(exclude_unset=True).items())
        raise TypeError(
            f"Expected a BaseModel instance or class, got {type(obj).__name__}"
        )

    def get_init_params(self, obj: Union[Type, Any]) -> Set[Tuple[str, Any]]:
        if isclass(obj):
            return {(name, None) for name in obj.__fields__.keys()}
        return {(name, None) for name in type(obj).__fields__.keys()}

    def get_source_attrs_names(self, source: Any) -> Set[str]:
        # Aggregate attributes using get_public_attrs and get_init_params
        pub = self.get_public_attrs(source)
        init = self.get_init_params(source)
        return {name for name, _ in pub} | {name for name, _ in init}

    def get_source_type(self, source_instance: Any) -> Type:
        return (
            type(source_instance) if not isclass(source_instance) else source_instance
        )

    def filter_empty_params(
        self, init_params: Set[Tuple[str, Parameter]]
    ) -> Set[Tuple[str, Parameter]]:
        return {(name, param) for name, param in init_params if param is None}


class POPOAdapter:
    def get_public_attrs(self, obj: Any) -> List[Tuple[str, Any]]:
        return [attr for attr in getmembers(obj) if not attr[0].startswith("_")]

    def get_init_params(self, obj: Union[Type, Any]) -> Set[Tuple[str, Any]]:
        return {
            (name, param)
            for name, param in signature(obj.__init__).parameters.items()
            if name != "self"
        }

    def get_source_attrs_names(self, source: Any) -> Set[str]:
        if isinstance(source, Iterable) and not isinstance(source, (str, bytes)):
            names = set()
            for s in source:
                pub = self.get_public_attrs(s)
                init = self.get_init_params(s)
                names |= {name for name, _ in pub} | {name for name, _ in init}
            return names
        pub = self.get_public_attrs(source)
        init = self.get_init_params(source)
        return {name for name, _ in pub} | {name for name, _ in init}

    def get_source_type(self, source_instance: Any) -> SourceType:
        return (
            tuple(so if isclass(so) else type(so) for so in source_instance)
            if isinstance(source_instance, Iterable)
            else source_instance if isclass(source_instance) else type(source_instance)
        )

    def filter_empty_params(
        self, init_params: Set[Tuple[str, Parameter]]
    ) -> Set[Tuple[str, Parameter]]:
        return {
            (name, param)
            for name, param in init_params
            if param.default is Parameter.empty
        }


def prop():
    def prop(x):
        return x

    return prop


class Mapper:
    def __init__(self) -> None:
        self.mappings = defaultdict(partial(defaultdict, partial(defaultdict, prop)))
        self.exclusions = defaultdict(partial(defaultdict, list))

    @staticmethod
    def _get_adapter(obj: Any):
        if BaseModel is not None and (
            isinstance(obj, BaseModel) or (isclass(obj) and issubclass(obj, BaseModel))
        ):
            return PydanticBaseModelAdapter(BaseModel)
        return POPOAdapter()

    def add_mapping(
        self,
        *,
        source: Union[SourceType, TS],
        target: TargetType,
        mapping: Optional[MappingSpec] = None,
        exclusions: Optional[Set[str]] = None,
    ) -> None:
        mapping = mapping or {}
        self._guard_source_has_all_attrs_specified_in_mapping(source, mapping)
        if isinstance(mapping, Set):
            mapping = {name: name for name in mapping}
        source_type = self._get_source_type(source)
        self.mappings[source_type][target].update(mapping or {})
        self.exclusions[source_type][target].extend(exclusions or set())

    def map(
        self,
        source: Source,
        target: Union[TT, type[TT]],
        skip_init: bool = False,
        extra: Optional[dict] = None,
    ) -> TT:
        """Map source object(s) to target type.

        Args:
            source: Single object or iterable of objects to map from
            target: Type to map to
            skip_init: Skip __init__ when creating target instance
            extra: Additional attributes to set on target instance
        """
        extra = extra or {}
        target_is_type = isclass(target)
        target_type: type[TT] = target if target_is_type else type(target)
        skip_init = skip_init or not target_is_type
        source_type = self._get_source_type(source)

        self._guard_no_required_attrs_excluded(
            source, target_type, source_type, extra, target
        )

        # Get source properties
        source_attrs = self._build_source_attrs_chain_map(
            source, source_type, target_type
        )

        # Get mapping rules
        mapping = self.mappings[source_type][target_type]

        # Apply mappings
        mapped_attrs = self._map(mapping, source_attrs)

        resulting_attrs = ChainMap(extra, mapped_attrs)

        return self._build_target(
            skip_init,
            target,
            resulting_attrs,
            target_type,
            source,
        )

    def _guard_source_has_all_attrs_specified_in_mapping(
        self, source: Union[SourceType, TS], mapping: Optional[MappingSpec]
    ) -> None:
        if not mapping:
            return

        mapping_attrs_names = self._get_mapping_attrs_names(mapping)
        source_attrs_names = self._get_source_attrs_names(source)
        missing_attributes = {
            attr for attr in mapping_attrs_names if attr not in source_attrs_names
        }

        if missing_attributes:
            self._raise_missing_attrs_error(source, missing_attributes)

    def _get_mapping_attrs_names(self, mapping: MappingSpec) -> Set[str]:
        if isinstance(mapping, Mapping):
            return set(mapping.keys())
        if isinstance(mapping, Iterable):
            return set(mapping)
        raise RuntimeError(
            "Can't get mapping attributes names. Mapping expected to be a Dict or List like object"
        )

    def _get_source_attrs_names(self, source: Any) -> Set[str]:
        adapter = self._get_adapter(source)
        return adapter.get_source_attrs_names(source)

    def _get_attrs_names(self, attrs: Iterable[Tuple[str, Any]]) -> Set[str]:
        return {name for name, _ in attrs}

    def _get_init_params(self, obj: Union[Type, Any]) -> Set[Tuple[str, Any]]:
        adapter = self._get_adapter(obj)
        return adapter.get_init_params(obj)

    def _raise_missing_attrs_error(
        self, source: Union[SourceType, TS], missing_attributes: Set[str]
    ) -> NoReturn:
        sorted_missing_attributes = sorted(missing_attributes)
        source_name = self._get_source_class_name(source)
        if isinstance(source_name, str):
            source_name_string = f"source {source_name}"
        elif isinstance(source_name, Iterable):
            source_name_string = (
                f"sources {', '.join(source_name[:-1])} and {source_name[-1]}"
            )
        else:
            raise RuntimeError("Can't define source class name")
        if len(sorted_missing_attributes) <= 1:
            attributes_string = f"attribute {''.join(sorted_missing_attributes)}"
        else:
            attributes_string = f"attributes {', '.join(sorted_missing_attributes[:-1])} and {sorted_missing_attributes[-1]}"
        raise TypeError(
            f"Mapping {attributes_string} not found in {source_name_string}."
        )

    def _get_source_class_name(self, source: Union[SourceType, TS]) -> str:
        if isinstance(source, Iterable):
            names = sorted(
                [s.__name__ if isclass(s) else type(s).__name__ for s in source]
            )
            return f"({', '.join(names)})"
        if isclass(source):
            return source.__name__
        if isinstance(source, type) is False:
            return type(source).__name__
        raise RuntimeError("Can't define source class name")

    def _build_target(
        self,
        skip_init: bool,
        target: Union[TT, Type[TT]],
        mapped_attrs: Mapping[str, Any],
        target_type: Type[TT],
        source_instance: Union[TS, Tuple[TS, ...]],
    ) -> TT:
        # Create target instance
        try:
            if skip_init:
                if not isclass(target):
                    return self._set_attrs(target, mapped_attrs)
                else:
                    target_instance = object.__new__(target_type)
                    return self._set_attrs(target_instance, mapped_attrs)
            return self._initialize_target(mapped_attrs, target_type)
        except TypeError as e:
            self._handle_mapping_error(source_instance, target_type, e)

    def _initialize_target(
        self,
        mapped_attrs: Mapping[str, Any],
        target_type: Type[TT],
    ) -> TT:
        return target_type(
            **{
                k: v
                for k, v in mapped_attrs.items()
                if k in set(self._get_attrs_names(self._get_init_params(target_type)))
            },
        )

    def _guard_no_required_attrs_excluded(
        self,
        source_instance: Union[TS, Tuple[TS, ...]],
        target_type: Type[TT],
        source_type: Union[Type[TS], Tuple[Type[TS], ...]],
        extra: Dict[str, Any],
        target: Union[TT, Type[TT]],
    ) -> None:
        missing_attrs_candidates = set(self.exclusions[source_type][target_type]) - set(
            extra.keys()
        )

        target_required_attrs = self._get_target_required_init_params_names(target)

        missing_attrs = missing_attrs_candidates & target_required_attrs
        if missing_attrs:
            self._raise_required_attrs_excluded_error(
                source_instance, target_type, missing_attrs
            )

    def _raise_required_attrs_excluded_error(
        self,
        source_instance: Union[TS, Tuple[TS, ...]],
        target_type: Type[TT],
        missing_attrs: Set[str],
    ) -> NoReturn:
        source_name = self._get_source_class_name(source_instance)
        if len(missing_attrs) == 1:
            raise RuntimeError(
                f"{target_type.__name__} requires argument {missing_attrs.pop()} which is excluded from mapping {source_name} -> {target_type.__name__}."
            )
        else:
            sorted_trouble_props_names = sorted(missing_attrs)
            trouble_pros_names = f"{', '.join(sorted_trouble_props_names[:-1])} and {sorted_trouble_props_names[-1]}"
            raise RuntimeError(
                f"{target_type.__name__} requires arguments {trouble_pros_names} which are excluded from mapping {source_name} -> {target_type.__name__}."
            )

    def _get_source_type(self, source_instance: Any) -> SourceType:
        adapter = self._get_adapter(source_instance)
        return adapter.get_source_type(source_instance)

    def _build_source_attrs_chain_map(
        self,
        source: Union[TS, Tuple[TS, ...]],
        source_type: Union[Type[TS], Tuple[Type[TS], ...]],
        target_type: Type[TT],
    ) -> ChainMap:
        """Extract properties from source object(s)."""

        # This is necessary because BaseModel instances are iterables, but we want to treat them as single objects.
        if BaseModel is not None:
            if isinstance(source, BaseModel) or (
                isclass(source) and issubclass(source, BaseModel)
            ):
                return ChainMap(self._select_attrs(source, source_type, target_type))

        if isinstance(source, Iterable):
            return ChainMap(
                *[self._select_attrs(so, source_type, target_type) for so in source]
            )
        return ChainMap(self._select_attrs(source, source_type, target_type))

    def _select_attrs(
        self,
        source: TS,
        source_type: Union[Type[TS], Tuple[Type[TS], ...]],
        target_type: Type[TT],
    ) -> Dict[str, Any]:
        return dict(
            self._filter_out_excluded_attrs(
                self._get_public_attrs(source), source_type, target_type
            )
        )

    def _set_attrs(self, instance: TT, attrs: Mapping[str, Any]) -> TT:
        for name, value in attrs.items():
            setattr(instance, name, value)
        return instance

    def _handle_mapping_error(
        self,
        source: Union[TS, Tuple[TS, ...]],
        target_type: Type[TT],
        error: TypeError,
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

    def _get_public_attrs(self, obj: Any) -> List[Tuple[str, Any]]:
        adapter = self._get_adapter(obj)
        return adapter.get_public_attrs(obj)

    def _filter_out_excluded_attrs(
        self,
        attrs: List[Tuple[str, Any]],
        source_type: Union[Type[TS], Tuple[Type[TS], ...]],
        target_type: Type[TT],
    ) -> List[Tuple[str, Any]]:
        return [
            attr
            for attr in attrs
            if attr[0] not in self.exclusions[source_type][target_type]
        ]

    def _get_target_required_init_params_names(
        self, target: Union[TT, Type[TT]]
    ) -> Set[str]:
        t_props_names = self._get_attrs_names(
            self._filter_empty_params(self._get_init_params(target))
        ) - self._get_attrs_names(self._get_public_attrs(target))

        return t_props_names

    def _filter_empty_params(
        self, init_params: Set[Tuple[str, Parameter]]
    ) -> Set[Tuple[str, Parameter]]:
        return {
            (name, param)
            for name, param in init_params
            # 'None' is used as a placeholder for Pydantic models in init_params to indicate
            # that a parameter is missing or uninitialized. This allows us to filter out
            # such parameters by checking 'param is None'.
            if param is None or param.default is Parameter.empty
        }

    def _map(
        self, maps: Dict[str, Callable], props: Mapping[str, Any]
    ) -> Dict[str, Any]:
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

        return dict(result)
