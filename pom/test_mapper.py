from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from typing import List

import pytest

from pom import Mapper


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
            match="Mapping attributes age, job and name not found in source \\(SourceClassA, SourceClassB\\).",
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
            name: str = None
            email: str = None

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
        mapper.add_mapping(source=a, target=Target, mapping=["name", "favorite_food"])
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
