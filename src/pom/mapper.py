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

from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

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


class PopoAdapter:

    def __init__(self, exclusions) -> None:
        self.exclusions = exclusions

    def get_init_params(self, obj: Union[Type, Any]) -> Set[Tuple[str, Any]]:
        return {
            (name, param)
            for name, param in signature(obj.__init__).parameters.items()
            if name not in ["self", "args", "kwargs"]
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
            if self.is_collection(source_instance)
            else source_instance if isclass(source_instance) else type(source_instance)
        )

    def is_collection(
        self,
        obj: Any,
    ) -> bool:
        # Default: treat any iterable (except strings/bytes) as multiple sources
        if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
            return True
        # Single source
        return False

    def select_attrs(
        self,
        source: TS,
        source_type: Union[Type[TS], Tuple[Type[TS], ...]],
        target_type: Type[TT],
    ) -> Dict[str, Any]:
        return dict(
            self._filter_out_excluded_attrs(
                self.get_public_attrs(source), source_type, target_type
            )
        )

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

    def get_public_attrs(self, obj: Any) -> List[Tuple[str, Any]]:
        return [attr for attr in getmembers(obj) if not attr[0].startswith("_")]

    def get_attrs_names(self, attrs: Iterable[Tuple[str, Any]]) -> Set[str]:
        return {name for name, _ in attrs}

    def filter_empty_params(
        self, init_params: Set[Tuple[str, Parameter]]
    ) -> Set[Tuple[str, Parameter]]:
        return {
            (name, param)
            for name, param in init_params
            if param.default is Parameter.empty
        }

    def set_attrs(self, instance: TT, attrs: Mapping[str, Any]) -> TT:
        for name, value in attrs.items():
            setattr(instance, name, value)
        return instance

    def create_instance(self, cls: Type[TT]) -> TT:
        return object.__new__(cls)


class PydanticModelAdapter(PopoAdapter):
    def __init__(self, exclusions: Any, BaseModel: Type) -> None:
        super().__init__(exclusions)
        self.BaseModel = BaseModel

    def get_public_attrs(self, obj: Any) -> List[Tuple[str, Any]]:
        # Use BaseModel.dict for field extraction
        if isclass(obj) and issubclass(obj, self.BaseModel):
            # When passed a BaseModel class, return its __fields__ names with None as values.
            return [
                (name, field)
                for name, field in obj.__fields__.items()
                if self._field_has_default(field)
            ]
        elif isinstance(obj, self.BaseModel):
            # For BaseModel instances, use dict() to extract field values.
            return list(obj.dict().items())
        raise TypeError(
            f"Expected a BaseModel instance or class, got {type(obj).__name__}"
        )

    def get_init_params(self, obj: Union[Type, Any]) -> Set[Tuple[str, Any]]:
        if isclass(obj):
            return self._get_obj_fields(obj)
        return self._get_obj_fields(type(obj))

    def get_source_attrs_names(self, source: Any) -> Set[str]:
        # Aggregate attributes using get_public_attrs and get_init_params
        pub = self.get_public_attrs(source)
        init = self.get_init_params(source)
        return {name for name, _ in pub} | {name for name, _ in init}

    def filter_empty_params(
        self, init_params: Set[Tuple[str, "FieldInfo"]]
    ) -> Set[Tuple[str, "FieldInfo"]]:
        return {
            (name, field)
            for name, field in init_params
            if not self._field_has_default(field)
        }

    def is_collection(
        self,
        obj: Any,
    ) -> bool:
        # BaseModel instances/classes should always be treated as single sources
        if (
            isclass(obj)
            and issubclass(obj, self.BaseModel)
            or isinstance(obj, self.BaseModel)
        ):
            return False
        elif isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
            return True
        raise TypeError(
            f"Expected a BaseModel instance, class or a collection of them, got {type(obj).__name__}"
        )

    def create_instance(self, cls: type[TT]) -> TT:
        if not isclass(cls) and issubclass(cls, BaseModel):
            raise TypeError("Expected a Pydantic BaseModel class")
        return cls.construct()

    @staticmethod
    def _get_obj_fields(obj):
        return {(field.alias or name, field) for name, field in obj.__fields__.items()}

    @staticmethod
    def _field_has_default(field_info: "FieldInfo") -> bool:
        return (
            field_info.default is not PydanticUndefined
            or field_info.default_factory is not None
        )


def prop():
    def prop(x):
        return x

    return prop


class Mapper:
    def __init__(self) -> None:
        self.mappings = defaultdict(partial(defaultdict, partial(defaultdict, prop)))
        self.exclusions = defaultdict(partial(defaultdict, list))

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
        adapter = self.get_adapter(source)
        source_type = adapter.get_source_type(source)
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
        adapter = self.get_adapter(source)
        source_type = adapter.get_source_type(source)

        self._guard_no_required_attrs_excluded(
            source, target_type, source_type, extra, target
        )

        # Get source properties
        source_attrs = self._create_source_attrs_chain_map(
            source, source_type, target_type
        )

        # Get mapping rules
        mapping = self.mappings[source_type][target_type]

        # Apply mappings
        mapped_attrs = self._map(mapping, source_attrs, extra)

        return self._build_target(
            skip_init,
            target,
            mapped_attrs,
            target_type,
            source,
        )

    def get_adapter(self, obj: Any):
        if (
            BaseModel is not None
            and (
                isinstance(obj, BaseModel)
                or (isclass(obj) and issubclass(obj, BaseModel))
            )
            or (
                isinstance(obj, Iterable)
                and all(isinstance(item, BaseModel) for item in obj)
            )
        ):
            return PydanticModelAdapter(self.exclusions, BaseModel)
        return PopoAdapter(self.exclusions)

    # region Private methods
    # These methods are not intended to be used outside of this class.

    def _map(
        self, mappings: MappingDict, attrs: Mapping[str, Any], extra: Dict[str, Any]
    ) -> Mapping[str, Any]:
        result = []
        for prop_name, prop_value in attrs.items():
            transform = mappings[prop_name]
            if callable(transform):
                mapped_value = transform(prop_value)
                result.append((prop_name, mapped_value))
            elif isinstance(transform, str):
                result.append((transform, prop_value))
            elif isinstance(transform, tuple):
                result.append((transform[0], transform[1](prop_value)))
            else:
                raise ValueError(
                    f"Unsupported transform type for property '{prop_name}'."
                )

        return ChainMap(extra, dict(result))

    def _create_source_attrs_chain_map(
        self,
        source: Any,
        source_type: Any,
        target_type: Any,
    ) -> ChainMap:
        adapter = self.get_adapter(source)

        if adapter.is_collection(source):
            return ChainMap(
                *[adapter.select_attrs(so, source_type, target_type) for so in source]
            )
        # Single source
        return ChainMap(adapter.select_attrs(source, source_type, target_type))

    def _build_target(
        self,
        skip_init: bool,
        target: Union[TT, Type[TT]],
        mapped_attrs: Mapping[str, Any],
        target_type: Type[TT],
        source_instance: Union[TS, Tuple[TS, ...]],
    ) -> TT:
        # Create target instance
        adapter = self.get_adapter(target)
        try:
            if skip_init:
                if not isclass(target):
                    return adapter.set_attrs(target, mapped_attrs)
                else:
                    target_instance = adapter.create_instance(target_type)
                    return adapter.set_attrs(target_instance, mapped_attrs)
            return self._initialize_target(mapped_attrs, target_type)
        except TypeError as e:
            self._handle_mapping_error(source_instance, target_type, e)
        except AttributeError as e:
            raise

    def _initialize_target(
        self,
        mapped_attrs: Mapping[str, Any],
        target_type: Type[TT],
    ) -> TT:
        adapter = self.get_adapter(target_type)
        return target_type(
            **{
                k: v
                for k, v in mapped_attrs.items()
                if k
                in set(adapter.get_attrs_names(adapter.get_init_params(target_type)))
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

    def _get_target_required_init_params_names(
        self, target: Union[TT, Type[TT]]
    ) -> Set[str]:
        adapter = self.get_adapter(target)
        t_props_names = adapter.get_attrs_names(
            adapter.filter_empty_params(adapter.get_init_params(target))
        ) - adapter.get_attrs_names(adapter.get_public_attrs(target))

        return t_props_names

    def _guard_source_has_all_attrs_specified_in_mapping(
        self, source: Union[SourceType, TS], mapping: Optional[MappingSpec]
    ) -> None:
        if not mapping:
            return

        mapping_attrs_names = self._get_mapping_attrs_names(mapping)
        adapter = self.get_adapter(source)
        source_attrs_names = adapter.get_source_attrs_names(source)
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

    # endregion
