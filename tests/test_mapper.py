import unittest.mock
from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from typing import List, Optional

import pytest
from pydantic import BaseModel, Field, ValidationError, field_validator
from pydantic.fields import FieldInfo

from pom import Mapper
from pom.mapper import PydanticModelAdapter


@pytest.fixture
def reversed_string():
    def _reversed_string(s: str) -> str:
        return s[::-1]

    return _reversed_string


@pytest.fixture
def simple_source_class_A():
    class SourceClassA:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    return SourceClassA


@pytest.fixture
def source_class_A_missing_attr():
    class SourceClassA:
        pass

    return SourceClassA


@pytest.fixture
def simple_source_class_B():
    class SourceClassB:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    return SourceClassB


@pytest.fixture
def simple_target_class():
    class TargetClass:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    return TargetClass


@pytest.fixture(scope="function")
def mapper():
    return Mapper()


class TestBasicMapping:
    """Tests for basic mapping functionality."""

    def test_simple_mapping(self, mapper, simple_source_class_A, simple_target_class):
        """Most basic case: mapping between identical classes."""
        source = simple_source_class_A("Johnny", "johnny@mail.com")

        mapper.add_mapping(source=simple_source_class_A, target=simple_target_class)
        result = mapper.map(source, simple_target_class)

        assert isinstance(result, simple_target_class)
        assert result.name == source.name
        assert result.email == source.email

    @pytest.mark.parametrize("transform_name", [True, False])
    def test_mapping_with_transformation(
        self,
        mapper,
        simple_source_class_A,
        simple_target_class,
        reversed_string,
        transform_name,
    ):
        """Test mapping with optional property transformation."""
        source = simple_source_class_A("Johnny", "johnny@mail.com")

        mapping = {"name": reversed_string} if transform_name else {}
        mapper.add_mapping(
            source=simple_source_class_A, target=simple_target_class, mapping=mapping
        )
        result = mapper.map(source, simple_target_class)

        expected_name = reversed_string(source.name) if transform_name else source.name
        assert result.name == expected_name

    def test_map_popo_to_popo_skip_init(self, mapper):
        """Test mapping to a POPO target with skip_init=True."""

        class Source:
            def __init__(self, value: str):
                self.value = value

        class Target:
            def __init__(self, value: str = "default"):
                self.value = value
                self.initialized = True  # Mark if __init__ was called

            extra_field: str = "not_set"

        source_instance = Source(value="test_value")
        mapper.add_mapping(source=Source, target=Target)

        # Create target instance without calling __init__
        target_instance = mapper.map(source_instance, Target, skip_init=True)

        assert isinstance(target_instance, Target)
        assert target_instance.value == "test_value"
        assert not hasattr(
            target_instance, "initialized"
        )  # __init__ should not have been called

        # Verify it can set attributes not in __init__ if they exist on the class
        # For this to work, Target needs to be prepared to have attributes set directly
        # or the adapter's set_attrs needs to handle it.
        # Let's assume direct attribute setting for now.
        target_instance_with_extra = Target()  # Create a normal instance to compare
        target_instance_with_extra.extra_field = "set_via_map"

        mapper_extra = Mapper()

        class SourceWithExtra:
            def __init__(self, extra_field: str):
                self.extra_field = extra_field

        source_extra_instance = SourceWithExtra(extra_field="set_via_map")
        mapper_extra.add_mapping(source=SourceWithExtra, target=Target)

        # Target class needs 'extra_field' defined if we expect it to be set
        # For simplicity, let's assume Target has it.
        # If Target doesn't have `extra_field` defined, this would typically set it dynamically.
        Target.extra_field = None  # Ensure the attribute exists for setattr

        target_mapped_extra = mapper_extra.map(
            source_extra_instance, Target, skip_init=True
        )
        assert target_mapped_extra.extra_field == "set_via_map"

    def test_map_without_add_mapping_map_equal_attrs(self, mapper):
        """Test that calling map without adding a mapping maps everything that is equal to both source and target."""

        class SourceModel:
            def __init__(self, name: str, age: int) -> None:
                self.name = name
                self.age = age

        class TargetModel:
            def __init__(self, name: str, job: str = None) -> None:
                self.name = name
                self.job = job

        source_instance = SourceModel(name="Test", age=30)

        target = mapper.map(
            source_instance,
            TargetModel,
        )
        assert isinstance(target, TargetModel)
        assert target.name == source_instance.name

    def test_map_without_add_mapping_skip_init(self, mapper):
        """Test mapping without add_mapping and with skip_init=True."""

        class SourceModel:
            def __init__(self, name: str, age: int) -> None:
                self.name = name
                self.age = age
                self.extra_source_field = "source_only"

        class TargetModel:

            def __init__(
                self, name: str, age: int, extra_source_field: str, job: str = None
            ) -> None:
                self.name = name
                self.age = age
                self.extra_source_field = extra_source_field
                self.job = job

        source_instance = SourceModel(name="Test", age=30)
        # Create an empty TargetModel instance, __new__ is used by mapper
        target_instance_shell = object.__new__(TargetModel)
        target = mapper.map(source_instance, target_instance_shell, skip_init=True)

        assert isinstance(target, TargetModel)
        assert target.name == source_instance.name
        assert target.age == source_instance.age  # Copied because skip_init=True
        assert not hasattr(target, "job")  # Not in source, not set because of skip_init
        assert target.extra_source_field == "source_only"

    def test_map_without_add_mapping_multiple_sources(self, mapper):
        """Test mapping from multiple sources without add_mapping."""

        class SourceModelA:
            def __init__(self, name: str, age: int) -> None:
                self.name = name
                self.age = age

        class SourceModelB:
            def __init__(self, job: str, city: str) -> None:
                self.job = job
                self.city = city

        class TargetModel:
            def __init__(
                self,
                name: str,
                job: str = "default_job",
                city: str = "default_city",
                age: int = 0,
            ) -> None:
                self.name = name
                self.job = job
                self.city = city
                self.age = age  # Default value

        source_a = SourceModelA(name="Test", age=30)
        source_b = SourceModelB(job="Engineer", city="SF")

        target = mapper.map((source_a, source_b), TargetModel)

        assert isinstance(target, TargetModel)
        assert target.name == source_a.name
        assert target.job == source_b.job
        assert target.city == source_b.city  # Takes from SourceModelB
        assert target.age == source_a.age  # Takes from SourceModelA

    def test_map_without_add_mapping_multiple_sources_skip_init(self, mapper):
        """Test mapping from multiple sources without add_mapping and with skip_init=True."""

        class SourceModelA:
            def __init__(self, name: str, age: int) -> None:
                self.name = name
                self.age = age
                self.a_specific = "from_a"

        class SourceModelB:
            def __init__(self, job: str, city: str) -> None:
                self.job = job
                self.city = city
                self.b_specific = "from_b"

        class TargetModel:
            name: str
            age: int
            job: str
            city: str
            a_specific: str
            b_specific: str
            # No __init__ for this test to ensure attributes are set directly

        source_a = SourceModelA(name="Test", age=30)
        source_b = SourceModelB(job="Engineer", city="SF")
        target_instance_shell = object.__new__(TargetModel)
        target = mapper.map((source_a, source_b), target_instance_shell, skip_init=True)

        assert isinstance(target, TargetModel)
        assert target.name == source_a.name
        assert target.job == source_b.job
        assert target.age == source_a.age
        assert target.city == source_b.city
        assert target.a_specific == "from_a"
        assert target.b_specific == "from_b"


class TestPropertyExclusion:
    """Tests for property exclusion functionality."""

    @pytest.mark.parametrize(
        "excluded_fields,expected_email",
        [
            ([], "johnny@mail.com"),
        ],
    )
    def test_excluding_properties(
        self,
        mapper,
        simple_source_class_A,
        simple_target_class,
        excluded_fields,
        expected_email,
    ):
        """Test that excluded properties are not mapped."""
        source = simple_source_class_A("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=simple_source_class_A,
            target=simple_target_class,
            exclusions=excluded_fields,
        )
        result = mapper.map(source, simple_target_class)

        assert result.email == expected_email

    @pytest.mark.parametrize(
        "excluded_fields",
        [
            ["email"],
        ],
    )
    def test_excluding_required_properties_raises_proper_error(
        self,
        mapper,
        simple_source_class_A,
        simple_target_class,
        excluded_fields,
    ):
        """Test that excluded properties are not mapped."""
        source = simple_source_class_A("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=simple_source_class_A,
            target=simple_target_class,
            exclusions=excluded_fields,
        )
        with pytest.raises(
            RuntimeError,
            match="TargetClass requires argument email which is excluded from mapping SourceClassA -> TargetClass.",
        ):
            mapper.map(source, simple_target_class)

    @pytest.mark.parametrize(
        "excluded_fields",
        [
            ["email"],
        ],
    )
    def test_excluding_required_properties_raises_proper_error_for_multiple_sources(
        self,
        mapper,
        simple_source_class_A,
        simple_source_class_B,
        simple_target_class,
        excluded_fields,
    ):
        """Test that excluded properties are not mapped."""
        source_a = simple_source_class_A("Johnny", "johnny@mail.com")
        source_b = simple_source_class_B("Johnny Well", "johnnywell@email.com")

        mapper.add_mapping(
            source=(simple_source_class_A, simple_source_class_B),
            target=simple_target_class,
            exclusions=excluded_fields,
        )
        with pytest.raises(
            RuntimeError,
            match="TargetClass requires argument email which is excluded from mapping \\(SourceClassA, SourceClassB\\) -> TargetClass.",
        ):
            mapper.map((source_a, source_b), simple_target_class)


class TestDataclassMapping:
    """Tests for mapping dataclass objects."""

    def test_dataclass_mapping(self, mapper, reversed_string):
        """Test mapping between dataclasses with transformations."""

        @dataclass
        class Source:
            name: str
            email: str

        @dataclass
        class Target:
            name: str
            email: str

        source = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": reversed_string}
        )
        result = mapper.map(source, Target)

        assert isinstance(result, Target)
        assert result.name == "ynnhoJ"
        assert result.email == source.email


class TestErrorHandling:
    """Tests for error handling and validation."""

    @pytest.mark.parametrize(
        "skip_init,should_raise",
        [
            (True, False),
            (False, True),
        ],
    )
    def test_missing_required_properties(self, mapper, skip_init, should_raise):
        """Test handling of missing required properties."""

        class Source:
            def __init__(self, email: str):
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        source = Source("johnny@mail.com")
        mapper.add_mapping(source=Source, target=Target)

        if should_raise:
            with pytest.raises(TypeError):
                mapper.map(source, Target, skip_init=skip_init)
        else:
            result = mapper.map(source, Target, skip_init=skip_init)
            assert result.email == source.email

    def test_add_mapping_source_attr_validation(self, mapper):
        """Test add_mapping raises TypeError if a mapped source attribute does not exist."""

        class SourceWithoutAttr:
            pass

        class Target:
            def __init__(self, name: str):
                self.name = name

        with pytest.raises(
            TypeError,
            match="Mapping attribute non_existent_attr not found in source SourceWithoutAttr.",
        ):
            mapper.add_mapping(
                source=SourceWithoutAttr,
                target=Target,
                mapping={"non_existent_attr": "name"},
            )

    def test_map_from_empty_iterable_source(self, mapper):
        """Test mapping from an empty iterable source."""

        class TargetWithNoArgInit:
            def __init__(self):
                self.value = "default"

        class TargetWithRequiredArg:
            def __init__(self, name: str):
                self.name = name

        mapper.add_mapping(
            source=list, target=TargetWithNoArgInit
        )  # Dummy source type for mapping rule

        # Case 1: Target can be initialized without arguments
        with does_not_raise():
            result1 = mapper.map([], TargetWithNoArgInit)
            assert isinstance(result1, TargetWithNoArgInit)
            assert result1.value == "default"

        # Case 2: Target requires arguments for __init__
        mapper.add_mapping(source=list, target=TargetWithRequiredArg)
        with pytest.raises(
            TypeError,
            match=r"__init__\(\) missing 1 required positional argument: 'name'",
        ):
            mapper.map([], TargetWithRequiredArg)

        # Case 3: skip_init = True
        with does_not_raise():
            result3 = mapper.map([], TargetWithRequiredArg, skip_init=True)
            assert isinstance(result3, TargetWithRequiredArg)
            # Attributes would not be set as there's no source data
            assert not hasattr(
                result3, "name"
            )  # Or it might be None if class defines it

    def test_map_unsupported_transform_type(self, mapper):
        """Test that _map raises ValueError for an unsupported transform type."""

        class Source:
            def __init__(self, data: str):
                self.data = data

        class Target:
            def __init__(self, data: str):
                self.data = data

        source_instance = Source("test")
        mapper.add_mapping(
            source=Source,
            target=Target,
            mapping={"data": 123},  # Invalid transform type (integer)
        )
        with pytest.raises(
            ValueError, match="Unsupported transform type for property 'data'"
        ):
            mapper.map(source_instance, Target)


class TestAdvancedMapping:
    """Tests for advanced mapping scenarios."""

    def test_mapping_to_existing_target_preserves_original_properties(self, mapper):
        """
        Test mapping a source object to an existing target instance when source is missing properties.

        Verifies that:
        1. Mapping succeeds when source object lacks properties present in target
        2. Existing target properties are preserved if not overwritten by source
        3. Properties present in both objects are correctly mapped
        """

        class Source:
            def __init__(self, email: str):
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("johnny@mail.com")
        b = Target("Johnny", None)

        with does_not_raise():
            mapper.add_mapping(source=Source, target=Target)
            mapper.map(a, b)
            assert b.email == a.email
            assert b.name == "Johnny"

    def test_adding_mapping_fails_when_source_missing_mapped_property(
        self, mapper, reversed_string
    ):
        """
        Test that adding a mapping raises TypeError when the mapping dictionary references
        properties that don't exist in the source class.
        """

        class Source:
            def __init__(self, email: str):
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("johnny@mail.com")
        b = Target("Johnny", None)

        with pytest.raises(TypeError):
            mapper.add_mapping(
                source=Source, target=Target, mapping={"name": reversed_string}
            )

    def test_mapping_from_source_instance(self, mapper, reversed_string):
        """
        Test adding a mapping using a source object instance instead of a class.

        Verifies that the mapper correctly handles instance-based mapping configurations
        and applies transformations specified in the mapping dictionary.
        """

        class Source:
            def __init__(self, name: str):
                self.name = name

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("Johnny")

        mapper.add_mapping(source=a, target=Target, mapping={"name": reversed_string})
        b = mapper.map(a, Target, skip_init=True)
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"

    def test_mapping_from_multiple_source_instances(self, mapper, reversed_string):
        """
        Test adding a mapping using a tuple of source object instances.

        Verifies that the mapper can handle multiple source objects and correctly
        applies transformations when mapping from multiple sources.
        """

        class SourceA:
            def __init__(self, name: str):
                self.name = name

        class SourceB:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = SourceA("Johnny")
        a2 = SourceA("Johnny2")
        b = SourceB(None, "johnny@email.com")

        mapper.add_mapping(
            source=(a, b), target=Target, mapping={"name": reversed_string}
        )
        c = mapper.map((a2, b), Target, skip_init=True)
        assert isinstance(c, Target)
        assert c.name == "2ynnhoJ"

    def test_error_message_lists_all_missing_attributes(self, mapper, reversed_string):
        """
        Test that the TypeError message includes all missing attributes when adding a mapper
        with explicit attribute names that don't exist in the source class.
        """

        class Source:
            def __init__(self, email: str):
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("johnny@mail.com")
        b = Target("Johnny", None)

        try:
            mapper.add_mapping(
                source=Source,
                target=Target,
                mapping={"name": reversed_string, "job": "job", "age": "age"},
            )
        except TypeError as e:
            assert (
                str(e)
                == "Mapping attributes age, job and name not found in source Source."
            )

    def test_error_message_lists_all_missing_attributes_from_multiple_sources(
        self, mapper, reversed_string
    ):
        """
        Test that the TypeError message includes all missing attributes when adding a mapper
        with multiple source classes specified as an iterable.
        """

        class SourceClassA:
            def __init__(self, email: str):
                self.email = email

        class SourceClassB:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        with pytest.raises(
            TypeError,
            match="Mapping attributes age and job not found in source \\(SourceClassA, SourceClassB\\).",
        ):
            mapper.add_mapping(
                source=(SourceClassA, SourceClassB),
                target=Target,
                mapping={"name": reversed_string, "job": "job", "age": "age"},
            )

    def test_error_message_for_single_missing_attribute(self, mapper, reversed_string):
        """
        Test the format of TypeError message when only one attribute is missing from a single source.

        Verifies proper singular form usage in the error message.
        """

        class Source:
            def __init__(self, email: str):
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        try:
            mapper.add_mapping(
                source=Source, target=Target, mapping={"name": reversed_string}
            )
        except TypeError as e:
            assert str(e) == "Mapping attribute name not found in source Source."

    def test_basic_mapping_with_identical_classes(self, mapper, reversed_string):
        """
        Test the simplest case of mapping between two classes with identical structure.

        Verifies basic mapping functionality and transformation application.
        """

        class Source:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": reversed_string}
        )
        b = mapper.map(a, Target)
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"

    def test_mapping_classes_without_default_attributes(self, mapper, reversed_string):
        """
        Test mapping between classes that don't have default values for their attributes.

        Verifies that mapping works correctly regardless of attribute default values.
        """

        class Source:

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": reversed_string}
        )
        b = mapper.map(a, Target)
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"

    def test_mapping_to_existing_target_instance(self, mapper, reversed_string):
        """
        Test mapping when the target is provided as an instance instead of a class.

        Verifies that the mapper correctly updates existing target instance attributes.
        """

        class Source:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("Johnny", "johnny@mail.com")
        b = Target(None, None)

        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": reversed_string}
        )
        b = mapper.map(a, b)  # There is the instance thing
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"
        assert b.email == a.email

    def test_excluding_properties_when_mapping_to_instance(
        self, mapper, reversed_string
    ):
        """
        Test mapping with exclusions when passing target as an instance.

        Verifies that excluded attributes are not mapped even when present in both source and target.
        """

        class Source:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("Johnny", "johnny@mail.com")
        b = Target(None, None)

        mapper.add_mapping(
            source=Source,
            target=Target,
            mapping={"name": reversed_string},
            exclusions=["email"],
        )
        b = mapper.map(a, b)
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"
        assert b.email == None

    def test_excluded_properties_retain_default_values(self, mapper, reversed_string):
        """
        Test the exclusion functionality when mapping between classes.

        Verifies that excluded attributes retain their default or initialized values in the target.
        """

        class Source:

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str = None):
                self.name = name
                self.email = email or "fixed@email.com"

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source,
            target=Target,
            mapping={"name": reversed_string},
            exclusions=["email"],
        )
        b = mapper.map(a, Target)
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"
        assert b.email == "fixed@email.com"

    def test_mapping_with_extra_properties(self, mapper, reversed_string):
        """
        Test mapping with additional properties provided via the extra parameter.

        Verifies that extra properties are correctly set on the target instance.
        """

        class Source:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str, age: int):
                self.name = name
                self.email = email
                self.age = age

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": reversed_string}
        )
        b = mapper.map(a, Target, extra={"age": 30})
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"
        assert b.age == 30

    def test_mapping_from_multiple_sources(self, mapper, reversed_string):
        """
        Test mapping from multiple source objects to a single target class.

        Verifies that properties from multiple sources are correctly combined in the target.
        """

        class SourceA:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email
                super().__init__()

        class SourceB:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str, age: int):
                self.name = name
                self.email = email
                self.age = age
                super().__init__()

        class Target:
            def __init__(self, name: str, email: str, age: int):
                self.name = name
                self.email = email
                self.age = age
                super().__init__()

        a = SourceA("Johnny", "johnny@mail.com")
        b = SourceB("Jodin", "johnyblaw@blawcloud.com", 30)

        mapper.add_mapping(
            source=(SourceA, SourceB), target=Target, mapping={"name": reversed_string}
        )
        c = mapper.map((a, b), Target)
        assert isinstance(c, Target)
        assert c.name == "ynnhoJ"
        assert c.email == a.email
        assert c.age == b.age

    def test_mapping_from_multiple_sources_with_extra_properties(
        self, mapper, reversed_string
    ):
        """
        Test aggregate mapping with additional properties provided via extra parameter.

        Verifies that both aggregated source properties and extra properties are correctly set.
        """

        class SourceA:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email
                super().__init__()

        class SourceB:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str, age: int):
                self.name = name
                self.email = email
                self.age = age
                super().__init__()

        class Target:
            def __init__(self, name: str, email: str, age: int, nickname: str):
                self.name = name
                self.email = email
                self.age = age
                self.nickname = nickname
                super().__init__()

        a = SourceA("Johnny", "johnny@mail.com")
        b = SourceB("Jodin", "johnyblaw@blawcloud.com", 30)

        mapper.add_mapping(
            source=(SourceA, SourceB), target=Target, mapping={"name": reversed_string}
        )
        c = mapper.map((a, b), Target, extra={"nickname": "J"})
        assert isinstance(c, Target)
        assert c.name == "ynnhoJ"
        assert c.email == a.email
        assert c.age == b.age
        assert c.nickname == "J"

    @pytest.mark.parametrize(
        "skip_init, check_if_raised",
        [(True, does_not_raise()), (False, pytest.raises(TypeError))],
    )
    def test_mapping_from_multiple_sources_with_missing_property(
        self, mapper, skip_init, check_if_raised
    ):
        """
        Test aggregate mapping behavior when required properties are missing from all sources.

        Verifies proper handling of missing properties based on skip_init parameter.
        """

        class SourceA:
            def __init__(self, email: str):
                self.email = email
                super().__init__()

        class SourceB:
            def __init__(self, email: str, age: int):
                self.email = email
                self.age = age
                super().__init__()

        class Target:
            def __init__(self, name: str, email: str, age: int):
                self.name = name
                self.email = email
                self.age = age
                super().__init__()

        a = SourceA("johnny@mail.com")
        b = SourceB("johnyblaw@blawcloud.com", 30)

        mapper.add_mapping(source=(SourceA, SourceB), target=Target)
        with check_if_raised:
            c = mapper.map((a, b), Target, skip_init=skip_init)

    def test_mapping_properties_with_different_names(self, mapper):
        """
        Test mapping between properties with different names in source and target.

        Verifies that the mapping dictionary correctly handles property name translations.
        """

        class Source:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email_address: str):
                self.name = name
                self.email_address = email_address

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source,
            target=Target,
            mapping={"email": "email_address"},
        )

        b = mapper.map(a, Target)
        assert isinstance(b, Target)
        assert b.name == a.name
        assert b.email_address == a.email

    def test_mapping_properties_with_different_names_and_transformation(
        self, mapper, reversed_string
    ):
        """
        Test mapping between differently named properties with transformation functions.

        Verifies that both name translation and value transformation work together.
        """

        class Source:
            name: str = None
            email: str = None

            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, reverse_name: str, email_address: str):
                self.reverse_name = reverse_name
                self.email_address = email_address

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source,
            target=Target,
            mapping={
                "name": ("reverse_name", reversed_string),
                "email": "email_address",
            },
        )

        b = mapper.map(a, Target)
        assert isinstance(b, Target)
        assert b.reverse_name == "ynnhoJ"
        assert b.email_address == a.email

    def test_mapping_dataclass_to_dataclass(self, mapper):
        """
        Test mapping functionality with Python dataclasses.

        Verifies that the mapper works correctly with dataclass-decorated classes.
        """

        @dataclass
        class DataclassSource:
            name: str
            email: str

        @dataclass
        class DataclassTarget:
            name: str
            email: str

        mapper.add_mapping(source=DataclassSource, target=DataclassTarget)

        a = DataclassSource("Johnny", "johnny@email.com")

        b = mapper.map(a, DataclassTarget)
        assert isinstance(b, DataclassTarget)
        assert b.name == a.name
        assert b.email == a.email

    def test_mapping_from_dataclass_instance_with_transformation(
        self, mapper, reversed_string
    ):
        """
        Test mapping from a dataclass instance with transformations.

        Verifies that the mapper correctly handles dataclass instances and applies transformations.
        """

        @dataclass
        class DataclassSource:
            name: str
            email: str

        @dataclass
        class DataclassTarget:
            name: str
            email: str

        a = DataclassSource("Johnny", "johnny@email.com")
        mapper.add_mapping(
            source=a, target=DataclassTarget, mapping={"name": reversed_string}
        )

        b = mapper.map(a, DataclassTarget)
        assert isinstance(b, DataclassTarget)
        assert b.name == reversed_string(a.name)
        assert b.email == a.email

    def test_mapping_using_attribute_name_list(self, mapper):
        """
        Test mapping using a list of attribute names instead of a mapping dictionary.

        Verifies that the mapper can handle simple attribute lists for direct mappings.
        """

        class Source:
            name: str = None
            email: str = None
            age: int = None
            job: str = None
            address: str = None
            favorite_food: List[str] = None

            def __init__(self, name, email, age, job, address, favorite_food):
                self.name = name
                self.email = email
                self.age = age
                self.jobp = job
                self.address = address
                self.favorite_food = favorite_food

        class Target:
            name: str = None
            favorite_food: List[str] = None

            def __init__(self, name, favorite_food):
                self.name = name
                self.favorite_food = favorite_food

        a = Source(
            "Johnny",
            "johnny@email.com",
            35,
            "programmer",
            "my street nº 777",
            ["churrasco", "pizza"],
        )
        mapper.add_mapping(source=a, target=Target, mapping={"name", "favorite_food"})
        b = mapper.map(a, Target)

        assert isinstance(b, Target)
        assert b.name == a.name
        assert b.favorite_food == a.favorite_food

    def test_mapping_ignores_nonexistent_target_attributes(self, mapper):
        """
        Test that the mapper only copies attributes that exist in the target object.

        Verifies that attempting to map non-existent target attributes doesn't raise errors.
        """

        class Source:
            name: str = None
            email: str = None
            age: int = None
            job: str = None
            address: str = None
            favorite_food: List[str] = None

            def __init__(self, name, email, age, job, address, favorite_food):
                self.name = name
                self.email = email
                self.age = age
                self.jobp = job
                self.address = address
                self.favorite_food = favorite_food

        class Target:
            name: str = None
            favorite_food: List[str] = None

            def __init__(self, name, favorite_food):
                self.name = name
                self.favorite_food = favorite_food

        a = Source(
            "Johnny",
            "johnny@email.com",
            35,
            "programmer",
            "my street nº 777",
            ["churrasco", "pizza"],
        )
        mapper.add_mapping(source=a, target=Target)
        b = mapper.map(a, Target)

        assert isinstance(b, Target)
        assert b.name == a.name
        assert b.favorite_food == a.favorite_food

    def test_mapping_classes_with_only_instance_attributes(
        self, mapper, reversed_string
    ):
        """
        Test mapping between classes that only define attributes in __init__.

        Verifies that the mapper works correctly with dynamically created instance attributes.
        """

        class Source:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        a = Source("Johnny", "johnny@mail.com")

        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": reversed_string}
        )
        b = mapper.map(a, Target)
        assert isinstance(b, Target)
        assert b.name == "ynnhoJ"

    def test_invalid_transformation_function_raises_error(self, mapper):
        """Test that invalid transformation functions raise appropriate errors."""

        class Source:
            def __init__(self, name: str):
                self.name = name

        class Target:
            def __init__(self, name: str):
                self.name = name

        def bad_transform(x):
            raise ValueError("Bad transform")

        source = Source("Johnny")
        mapper.add_mapping(
            source=Source, target=Target, mapping={"name": bad_transform}
        )

        with pytest.raises(ValueError, match="Bad transform"):
            mapper.map(source, Target)

    def test_none_value_in_mapping_preserves_none(self, mapper):
        """Test that None values in source are preserved in mapping."""

        class Source:
            def __init__(self, name: str = None):
                self.name = name

        class Target:
            def __init__(self, name: str = None):
                self.name = name

        source = Source(None)
        mapper.add_mapping(source=Source, target=Target)
        result = mapper.map(source, Target)

        assert result.name is None

    def test_mapping_with_inheritance(self, mapper):
        """Test mapping works correctly with inherited attributes."""

        class BaseSource:
            def __init__(self, base_attr: str):
                self.base_attr = base_attr

        class Source(BaseSource):
            def __init__(self, base_attr: str, name: str):
                super().__init__(base_attr)
                self.name = name

        class Target:
            def __init__(self, base_attr: str, name: str):
                self.base_attr = base_attr
                self.name = name

        source = Source("base", "Johnny")
        mapper.add_mapping(source=Source, target=Target)
        result = mapper.map(source, Target)

        assert result.base_attr == "base"
        assert result.name == "Johnny"

    def test_mapping_with_property_decorators(self, mapper):
        """Test mapping handles @property decorators correctly."""

        class Source:
            def __init__(self, name: str):
                self._name = name

            @property
            def name(self):
                return self._name

        class Target:
            def __init__(self, name: str):
                self.name = name

        source = Source("Johnny")
        mapper.add_mapping(source=Source, target=Target)
        result = mapper.map(source, Target)

        assert result.name == "Johnny"

    @pytest.mark.performance
    def test_mapping_large_object_performance(self, mapper):
        """Test mapping performance with large objects."""

        class LargeSource:
            def __init__(self):
                for i in range(1000):
                    setattr(self, f"attr_{i}", i)

        class LargeTarget:
            pass

        source = LargeSource()
        mapper.add_mapping(source=source, target=LargeTarget)

        import time

        start = time.time()
        result = mapper.map(source, LargeTarget, skip_init=True)
        duration = time.time() - start

        assert duration < 1.0  # Should complete in under 1 second
        assert all(getattr(result, f"attr_{i}") == i for i in range(1000))

    def test_mapping_with_none_extra(self, mapper):
        """Test that mapping works correctly when extra parameter is None."""

        class Source:
            def __init__(self, name: str):
                self.name = name

        class Target:
            def __init__(self, name: str):
                self.name = name

        source = Source("Johnny")
        mapper.add_mapping(source=Source, target=Target)

        result = mapper.map(source, Target, extra=None)
        assert isinstance(result, Target)
        assert result.name == "Johnny"

    def test_extra_parameter_overrides_source_attribute(self, mapper):
        """Test that extra parameters take precedence over source attributes."""

        class Source:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        class Target:
            def __init__(self, name: str, email: str):
                self.name = name
                self.email = email

        source = Source("Johnny", "johnny@mail.com")
        mapper.add_mapping(source=Source, target=Target)

        # Extra parameter overrides source's email
        result = mapper.map(source, Target, extra={"email": "override@email.com"})

        assert isinstance(result, Target)
        assert result.name == source.name  # Not overridden
        assert result.email == "override@email.com"  # Overridden by extra

    @pytest.mark.parametrize(
        "sources,expected_age",
        [
            (lambda a, b: (b, a), lambda b, _: b.age),  # (source_b, source_a)
            (lambda a, b: (a, b), lambda _, a: a.age),  # (source_a, source_b)
        ],
    )
    def test_mapping_from_multiple_sources_to_source_type(
        self, mapper, sources, expected_age
    ):
        """
        Test mapping from multiple sources where target type matches one of the sources.

        Verifies that mapping works correctly when target class is same as one of source classes.
        """

        class SourceA:
            def __init__(self, name: str, age: int = None):
                self.name = name
                self.age = age

        class SourceB:
            def __init__(self, age: int):
                self.age = age

        source_a = SourceA("Johnny", 25)
        source_b = SourceB(30)

        mapper.add_mapping(source=(SourceB, SourceA), target=SourceA)
        result = mapper.map(sources(source_a, source_b), SourceA)

        assert result.age == expected_age(source_b, source_a)

    def test_mapping_with_target_name_and_transform_tuple(
        self, mapper, reversed_string
    ):
        """Test mapping using (target_name, transform_function) tuple."""

        class Source:
            def __init__(self, original_name: str):
                self.original_name = original_name

        class Target:
            def __init__(self, new_name: str):
                self.new_name = new_name

        source_instance = Source("TestName")
        mapper.add_mapping(
            source=Source,
            target=Target,
            mapping={"original_name": ("new_name", reversed_string)},
        )
        result = mapper.map(source_instance, Target)
        assert isinstance(result, Target)
        assert result.new_name == "emaNtseT"


class TestPydanticMapping:

    def test_mapping_with_pydantic_models(self, mapper, reversed_string):
        """Test mapping between Pydantic models with validation."""

        class SourceModel(BaseModel):
            name: str
            email: str
            age: Optional[int] = None

        class TargetModel(BaseModel):
            name: str
            email: str
            age: Optional[int] = None

        source = SourceModel(name="Johnny", email="johnny@mail.com", age=30)

        mapper.add_mapping(
            source=SourceModel, target=TargetModel, mapping={"name": reversed_string}
        )
        result = mapper.map(source, TargetModel)

        assert isinstance(result, TargetModel)
        assert result.name == "ynnhoJ"
        assert result.email == source.email
        assert result.age == source.age

    def test_mapping_with_multiple_pydantic_models(self, mapper):
        """Test mapping between multiple Pydantic models."""

        class SourceModelA(BaseModel):
            name: str
            email: str

        class SourceModelB(BaseModel):
            age: int
            address: str

        class TargetModel(BaseModel):
            name: str
            email: str
            age: int
            address: str

        source_a = SourceModelA(name="Johnny", email="johnny@email.com")
        source_b = SourceModelB(age=30, address="123 Main St")
        mapper.add_mapping(source=(SourceModelA, SourceModelB), target=TargetModel)
        result = mapper.map((source_a, source_b), TargetModel)
        assert isinstance(result, TargetModel)
        assert result.name == source_a.name
        assert result.email == source_a.email
        assert result.age == source_b.age
        assert result.address == source_b.address

    # In TestPydanticMapping
    def test_map_popo_to_pydantic_with_validation(self, mapper):
        class PopoSource:
            def __init__(self, name: str, age: int):
                self.name = name
                self.age = age

        class PydanticTarget(BaseModel):
            name: str
            age: int

            @field_validator("age")
            def age_must_be_positive(cls, v):
                if v < 0:
                    raise ValueError("age must be positive")
                return v

        mapper.add_mapping(source=PopoSource, target=PydanticTarget)

        # Valid case
        source_valid = PopoSource(name="Valid", age=10)
        target_valid = mapper.map(source_valid, PydanticTarget)
        assert target_valid.age == 10

        # Invalid case for Pydantic validation
        source_invalid = PopoSource(name="Invalid", age=-5)
        with pytest.raises(ValidationError):  # Pydantic's own error
            mapper.map(source_invalid, PydanticTarget)

    def test_map_pydantic_to_popo(self, mapper):
        class PydanticSource(BaseModel):
            name: str
            value: int

        class PopoTarget:
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

        source = PydanticSource(name="Test", value=123)
        mapper.add_mapping(source=PydanticSource, target=PopoTarget)
        target_instance = mapper.map(source, PopoTarget)

        assert isinstance(target_instance, PopoTarget)
        assert target_instance.name == "Test"
        assert target_instance.value == 123

    def test_pydantic_target_excluded_required_field_detection(self, mapper):
        class PydanticTargetWithRequired(BaseModel):
            name: str  # Required
            age: Optional[int] = None  # Optional
            city: str = "NY"  # Has default

        class SourceSimple:
            def __init__(self, name: str, age: int, city: str):
                self.name = name
                self.age = age
                self.city = city

        source = SourceSimple("Test", 30, "LA")

        mapper.add_mapping(
            source=SourceSimple,
            target=PydanticTargetWithRequired,
            exclusions={"name"},  # Excluding a Pydantic-required field
        )

        # Expected: RuntimeError because 'name' is required by PydanticTargetWithRequired and is excluded.
        with pytest.raises(
            RuntimeError,
            match="PydanticTargetWithRequired requires argument name which is excluded",
        ):
            mapper.map(source, PydanticTargetWithRequired)

        # Control: excluding an optional field should work
        mapper_optional = Mapper()
        mapper_optional.add_mapping(
            source=SourceSimple,
            target=PydanticTargetWithRequired,
            exclusions={"age"},  # Excluding an optional field
        )
        with does_not_raise():
            result = mapper_optional.map(source, PydanticTargetWithRequired)
            assert result.name == "Test"
            assert result.age is None  # As it was excluded

    def test_map_to_pydantic_skip_init(self, mapper):
        class PydanticTarget(BaseModel):
            name: str
            value: int

        class PopoSource:
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

        source = PopoSource(name="Test", value=10)
        mapper.add_mapping(source=PopoSource, target=PydanticTarget)

        target_instance = mapper.map(source, PydanticTarget, skip_init=True)
        assert isinstance(target_instance, PydanticTarget)
        assert target_instance.name == "Test"
        assert target_instance.value == 10
        # Ensure model is valid after attrs are set
        assert PydanticTarget.model_validate(target_instance.model_dump())

    def test_pydantic_mapping_with_field_aliases(self, mapper):
        class Source(BaseModel):
            user_name: str

        class TargetWithAlias(BaseModel):
            name: str = Field(alias="user_name_alias")

        source_instance = Source(user_name="john_doe")

        mapper.add_mapping(
            source=Source,
            target=TargetWithAlias,
            mapping={"user_name": "user_name_alias"},
        )
        result1 = mapper.map(source_instance, TargetWithAlias)
        assert result1.name == "john_doe"
        assert result1.model_dump(by_alias=True) == {"user_name_alias": "john_doe"}

    def test_pydantic_mapping_wrongly_with_field_name_instead_of_aliases(self, mapper):
        class Source(BaseModel):
            user_name: str

        class TargetWithAlias(BaseModel):
            name: str = Field(alias="user_name_alias")

        source_instance = Source(user_name="john_doe")

        mapper.add_mapping(
            source=Source,
            target=TargetWithAlias,
            mapping={"user_name": "name"},
        )
        with pytest.raises(ValidationError, match="user_name_alias"):
            mapper.map(source_instance, TargetWithAlias)

    def test_map_pydantic_without_add_mapping(self, mapper):
        """Test mapping Pydantic models without add_mapping."""

        class SourcePydantic(BaseModel):
            name: str
            age: int
            extra_source_field: str = "source_only_pydantic"

        class TargetPydantic(BaseModel):
            name: str
            job: Optional[str] = None
            age: int

        source_instance = SourcePydantic(name="TestPydantic", age=31)
        target = mapper.map(source_instance, TargetPydantic)

        assert isinstance(target, TargetPydantic)
        assert target.name == source_instance.name
        assert target.age == source_instance.age
        assert target.job is None
        assert not hasattr(target, "extra_source_field")

    def test_map_pydantic_without_add_mapping_skip_init(self, mapper):
        """Test mapping Pydantic models without add_mapping and skip_init=True."""

        class SourcePydantic(BaseModel):
            name: str
            age: int
            extra_source_field: str = "source_only_pydantic"

        class TargetPydantic(BaseModel):
            name: str
            job: Optional[str] = None
            age: Optional[int] = None
            extra_source_field: Optional[str] = None

        source_instance = SourcePydantic(name="TestPydantic", age=32)
        # For Pydantic, skip_init=True implies using .construct() or similar,
        # then setting attributes.
        # The mapper's PydanticModelAdapter uses cls.construct() then set_attrs.
        target = mapper.map(source_instance, TargetPydantic, skip_init=True)

        assert isinstance(target, TargetPydantic)
        assert target.name == source_instance.name
        assert target.age == source_instance.age
        assert (
            target.job is None
        )  # Not in source, Pydantic default if not set by construct
        assert target.extra_source_field == "source_only_pydantic"

    def test_map_multiple_pydantic_sources_without_add_mapping(self, mapper):
        """Test mapping from multiple Pydantic sources without add_mapping."""

        class SourcePydanticA(BaseModel):
            name: str
            age: int
            a_specific: str = "from_a_pydantic"

        class SourcePydanticB(BaseModel):
            job: str
            city: str
            b_specific: str = "from_b_pydantic"

        class TargetPydantic(BaseModel):
            name: str
            job: str
            age: int
            city: Optional[str] = "default_city_pydantic"

        source_a = SourcePydanticA(name="TestPydanticMulti", age=33)
        source_b = SourcePydanticB(job="Developer", city="NY")

        target = mapper.map((source_a, source_b), TargetPydantic)

        assert isinstance(target, TargetPydantic)
        assert target.name == source_a.name
        assert target.age == source_a.age
        assert target.job == source_b.job
        assert target.city == source_b.city
        assert not hasattr(target, "a_specific")
        assert not hasattr(target, "b_specific")

    def test_map_multiple_pydantic_sources_without_add_mapping_skip_init(self, mapper):
        """Test mapping from multiple Pydantic sources without add_mapping and skip_init=True."""

        class SourcePydanticA(BaseModel):
            name: str
            age: int
            a_specific: str = "from_a_pydantic_skip"

        class SourcePydanticB(BaseModel):
            job: str
            city: str
            b_specific: str = "from_b_pydantic_skip"

        class TargetPydantic(BaseModel):
            name: str
            age: Optional[int] = None
            job: Optional[str] = None
            city: Optional[str] = None
            a_specific: Optional[str] = None
            b_specific: Optional[str] = None

        source_a = SourcePydanticA(name="TestPydanticMultiSkip", age=34)
        source_b = SourcePydanticB(job="Architect", city="LA")

        target = mapper.map((source_a, source_b), TargetPydantic, skip_init=True)

        assert isinstance(target, TargetPydantic)
        assert target.name == source_a.name
        assert target.age == source_a.age
        assert target.job == source_b.job
        assert target.city == source_b.city
        assert target.a_specific == source_a.a_specific
        assert target.b_specific == source_b.b_specific


class TestPydanticModelAdapter:
    def test_pydantic_adapter_get_public_attrs_from_class(self, mapper):
        class MyPydanticModel(BaseModel):
            name: str
            age: int

        adapter = mapper.get_adapter(MyPydanticModel)  # Gets PydanticModelAdapter
        attrs = adapter.get_public_attrs(MyPydanticModel)
        assert isinstance(adapter, PydanticModelAdapter)
        assert set(attrs) == set()

    def test_pydantic_adapter_get_public_attrs_from_instance_exclude_unset(
        self, mapper
    ):
        class MyPydanticModel(BaseModel):
            name: str
            age: Optional[int] = None
            city: str = "DefaultCity"

        source_instance = MyPydanticModel(
            name="Test"
        )  # age is not set, city uses default
        adapter = mapper.get_adapter(source_instance)
        attrs = adapter.get_public_attrs(source_instance)

        # Pydantic's .dict(exclude_unset=True) includes fields explicitly set or with defaults
        # If 'age' was not set and had no default, it wouldn't be in .dict(exclude_unset=True)
        # If 'age' is Optional[int] = None, it will be included with value None if set to None or not provided.
        # If 'city' has a default, it's always "set".
        attr_dict = dict(attrs)
        assert attr_dict["name"] == "Test"
        assert attr_dict["city"] == "DefaultCity"
        assert "age" in attr_dict  # Will be None if not provided
        assert attr_dict.get("age") is None

    def test_pydantic_adapter_get_init_params(self, mapper):
        class MyPydanticModel(BaseModel):
            name: str
            value: int

        adapter = mapper.get_adapter(MyPydanticModel)  # Gets PydanticModelAdapter

        class_params = adapter.get_init_params(MyPydanticModel)
        class_params_dict = dict(class_params)

        assert len(class_params_dict) == 2
        assert "name" in class_params_dict
        assert class_params_dict["name"].annotation == str
        assert class_params_dict["name"].is_required()

        assert "value" in class_params_dict
        assert class_params_dict["value"].annotation == int
        assert class_params_dict["value"].is_required()

        instance = MyPydanticModel(name="Test", value=1)
        instance_params = adapter.get_init_params(instance)
        instance_params_dict = dict(instance_params)

        assert len(instance_params_dict) == 2
        assert "name" in instance_params_dict
        assert instance_params_dict["name"].annotation == str
        assert instance_params_dict["name"].is_required()

        assert "value" in instance_params_dict
        assert instance_params_dict["value"].annotation == int
        assert instance_params_dict["value"].is_required()

    def test_pydantic_adapter_get_public_attrs_from_class_with_defaults(self, mapper):
        class MyPydanticModelWithDefaults(BaseModel):
            name: str
            age: int = 30
            city: Optional[str] = Field(default="NY")
            country: str  # No default

        adapter = mapper.get_adapter(MyPydanticModelWithDefaults)
        attrs_gen = adapter.get_public_attrs(MyPydanticModelWithDefaults)
        attrs = dict(attrs_gen)

        assert isinstance(adapter, PydanticModelAdapter)

        # Fields with defaults should be included
        assert "age" in attrs
        assert isinstance(attrs["age"], FieldInfo)
        assert attrs["age"].default == 30

        assert "city" in attrs
        assert isinstance(attrs["city"], FieldInfo)
        assert attrs["city"].default == "NY"

        # Fields without defaults should NOT be included by get_public_attrs for a class
        # because it checks _field_has_default or if it's an alias for a field with default.
        # The current PydanticModelAdapter.get_public_attrs for a class only returns fields with defaults.
        # If the intention is to get all fields, the adapter logic would need to change.
        # Based on current adapter logic:
        assert "name" not in attrs  # No default
        assert "country" not in attrs  # No default

    def test_pydantic_adapter_get_public_attrs_from_class_no_defaults(self, mapper):
        # This is essentially what the original test_pydantic_adapter_get_public_attrs_from_class did
        class MyPydanticModelNoDefaults(BaseModel):
            name: str
            age: int

        adapter = mapper.get_adapter(MyPydanticModelNoDefaults)
        attrs = adapter.get_public_attrs(MyPydanticModelNoDefaults)
        assert isinstance(adapter, PydanticModelAdapter)
        assert set(attrs) == set()  # No fields with defaults


class TestPopoAdapter:
    def test_popo_adapter_get_init_params_variations(self, mapper):
        class NoInit:
            pass

        class ArgsKwargsInit:
            def __init__(self, *args, **kwargs):
                pass

        class OnlySelfInit:
            def __init__(self):
                pass

        adapter = mapper.get_adapter(NoInit)  # Gets PopoAdapter
        assert adapter.get_init_params(NoInit) == set()  # object.__init__

        adapter_ak = mapper.get_adapter(ArgsKwargsInit)
        # inspect.signature will show 'args' and 'kwargs'
        assert adapter_ak.get_init_params(ArgsKwargsInit) == set()

        adapter_os = mapper.get_adapter(OnlySelfInit)
        assert adapter_os.get_init_params(OnlySelfInit) == set()

    def test_popo_adapter_get_public_attrs_with_properties_methods(self, mapper):
        class PopoWithProperty:
            def __init__(self):
                self._name = "test"

            @property
            def name(self):
                return self._name

            def get_value(self):
                return 42

            _internal_val = "secret"

        instance = PopoWithProperty()
        adapter = mapper.get_adapter(instance)
        attrs = dict(adapter.get_public_attrs(instance))

        assert "name" in attrs
        assert attrs["name"] == "test"
        assert "get_value" in attrs  # Methods are included
        assert "_internal_val" not in attrs


class TestAdapterSelection:
    def test_get_adapter_for_mixed_iterable(self, mapper):
        class PydanticModel(BaseModel):
            field: str

        class PopoModel:
            pass

        mixed_iterable = [PydanticModel(field="test"), PopoModel()]
        adapter = mapper.get_adapter(mixed_iterable)
        # Expect PopoAdapter because not all items are Pydantic models
        assert not isinstance(adapter, PydanticModelAdapter)
        assert isinstance(
            adapter, mapper.get_adapter(PopoModel()).__class__
        )  # Check it's PopoAdapter

    @unittest.mock.patch("pom.mapper.BaseModel", None)
    def test_get_adapter_when_pydantic_not_available(self, mapper):
        class SomeClass:
            pass

        # Test with a class
        adapter_class = mapper.get_adapter(SomeClass)
        assert not isinstance(adapter_class, PydanticModelAdapter)
        assert isinstance(
            adapter_class, mapper.get_adapter(SomeClass()).__class__
        )  # Check it's PopoAdapter

        # Test with an instance
        instance = SomeClass()
        adapter_instance = mapper.get_adapter(instance)
        assert not isinstance(adapter_instance, PydanticModelAdapter)
        assert isinstance(adapter_instance, mapper.get_adapter(SomeClass()).__class__)

        # Test with an iterable of non-Pydantic (since BaseModel is None)
        iterable = [SomeClass(), SomeClass()]
        adapter_iterable = mapper.get_adapter(iterable)
        assert not isinstance(adapter_iterable, PydanticModelAdapter)
        assert isinstance(adapter_iterable, mapper.get_adapter(SomeClass()).__class__)
