from contextlib import nullcontext as does_not_raise
from dataclasses import dataclass
from typing import ClassVar, List

import pytest

from pom import Mapper


def reversed_string(s: str) -> str:
    return s[::-1]


@pytest.mark.parametrize(
    "skip_init, check_if_raised",
    [(True, does_not_raise()), (False, pytest.raises(TypeError))],
)
def test_skip_init_param_controls_missing_property_behavior(skip_init, check_if_raised):
    """
    Test the skip_init parameter of the map method.

    When skip_init is True, mapping should succeed even with missing required init parameters.
    When skip_init is False, mapping should raise TypeError for missing required init parameters.
    """

    class A:
        def __init__(self, email: str):
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B)
    with check_if_raised:
        b = mapper.map(a, B, skip_init=skip_init)


def test_mapping_to_existing_target_preserves_original_properties():
    """
    Test mapping a source object to an existing target instance when source is missing properties.

    Verifies that:
    1. Mapping succeeds when source object lacks properties present in target
    2. Existing target properties are preserved if not overwritten by source
    3. Properties present in both objects are correctly mapped
    """

    class A:

        def __init__(self, email: str):
            self.email = email

    class B:

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("johnny@mail.com")
    b = B("Johnny", None)

    mapper = Mapper()
    with does_not_raise():
        mapper.add_mapping(source=A, target=B)
        mapper.map(a, b)
        assert b.email == a.email
        assert b.name == "Johnny"


def test_adding_mapping_fails_when_source_missing_mapped_property():
    """
    Test that adding a mapping raises TypeError when the mapping dictionary references
    properties that don't exist in the source class.
    """

    class A:
        def __init__(self, email: str):
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("johnny@mail.com")
    b = B("Johnny", None)

    mapper = Mapper()
    with pytest.raises(TypeError):
        mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})


def test_mapping_from_source_instance():
    """
    Test adding a mapping using a source object instance instead of a class.

    Verifies that the mapper correctly handles instance-based mapping configurations
    and applies transformations specified in the mapping dictionary.
    """

    class A:
        def __init__(self, name: str):
            self.name = name

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny")

    mapper = Mapper()

    mapper.add_mapping(source=a, target=B, mapping={"name": reversed_string})
    b = mapper.map(a, B, skip_init=True)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"


def test_mapping_from_multiple_source_instances():
    """
    Test adding a mapping using a tuple of source object instances.

    Verifies that the mapper can handle multiple source objects and correctly
    applies transformations when mapping from multiple sources.
    """

    class A:
        def __init__(self, name: str):
            self.name = name

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class C:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny")
    a2 = A("Johnny2")
    b = B(None, "johnny@email.com")

    mapper = Mapper()

    mapper.add_mapping(source=(a, b), target=C, mapping={"name": reversed_string})
    c = mapper.map((a2, b), C, skip_init=True)
    assert isinstance(c, C)
    assert c.name == "2ynnhoJ"


def test_error_message_lists_all_missing_attributes():
    """
    Test that the TypeError message includes all missing attributes when adding a mapper
    with explicit attribute names that don't exist in the source class.
    """

    class A:
        def __init__(self, email: str):
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("johnny@mail.com")
    b = B("Johnny", None)

    mapper = Mapper()

    try:
        mapper.add_mapping(
            source=A,
            target=B,
            mapping={"name": reversed_string, "job": "job", "age": "age"},
        )
    except TypeError as e:
        assert str(e) == "Mapping attributes age, job and name not found in source A."


def test_error_message_lists_all_missing_attributes_from_multiple_sources():
    """
    Test that the TypeError message includes all missing attributes when adding a mapper
    with multiple source classes specified as an iterable.
    """

    class A:
        def __init__(self, email: str):
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class C:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    mapper = Mapper()

    try:
        mapper.add_mapping(
            source=(A, B),
            target=C,
            mapping={"name": reversed_string, "job": "job", "age": "age"},
        )
    except TypeError as e:
        assert (
            str(e)
            == "Mapping attributes age, job and name not found in sources A and B."
        )


def test_error_message_for_single_missing_attribute():
    """
    Test the format of TypeError message when only one attribute is missing from a single source.

    Verifies proper singular form usage in the error message.
    """

    class A:
        def __init__(self, email: str):
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    mapper = Mapper()

    try:
        mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})
    except TypeError as e:
        assert str(e) == "Mapping attribute name not found in source A."


def test_basic_mapping_with_identical_classes():
    """
    Test the simplest case of mapping between two classes with identical structure.

    Verifies basic mapping functionality and transformation application.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})
    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"


def test_mapping_classes_without_default_attributes():
    """
    Test mapping between classes that don't have default values for their attributes.

    Verifies that mapping works correctly regardless of attribute default values.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})
    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"


def test_mapping_to_existing_target_instance():
    """
    Test mapping when the target is provided as an instance instead of a class.

    Verifies that the mapper correctly updates existing target instance attributes.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny", "johnny@mail.com")
    b = B(None, None)

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})
    b = mapper.map(a, b)  # There is the instance thing
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == a.email


def test_excluding_properties_when_mapping_to_instance():
    """
    Test mapping with exclusions when passing target as an instance.

    Verifies that excluded attributes are not mapped even when present in both source and target.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny", "johnny@mail.com")
    b = B(None, None)

    mapper = Mapper()
    mapper.add_mapping(
        source=A, target=B, mapping={"name": reversed_string}, exclusions=["email"]
    )
    b = mapper.map(a, b)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == None


def test_excluded_properties_retain_default_values():
    """
    Test the exclusion functionality when mapping between classes.

    Verifies that excluded attributes retain their default or initialized values in the target.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email: str = None):
            self.name = name
            self.email = email or "fixed@email.com"

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(
        source=A, target=B, mapping={"name": reversed_string}, exclusions=["email"]
    )
    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == "fixed@email.com"


def test_mapping_with_extra_properties():
    """
    Test mapping with additional properties provided via the extra parameter.

    Verifies that extra properties are correctly set on the target instance.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email: str, age: int):
            self.name = name
            self.email = email
            self.age = age

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})
    b = mapper.map(a, B, extra={"age": 30})
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.age == 30


def test_mapping_from_multiple_sources():
    """
    Test mapping from multiple source objects to a single target class.

    Verifies that properties from multiple sources are correctly combined in the target.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email
            super().__init__()

    class B:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str, age: int):
            self.name = name
            self.email = email
            self.age = age
            super().__init__()

    class C:
        def __init__(self, name: str, email: str, age: int):
            self.name = name
            self.email = email
            self.age = age
            super().__init__()

    a = A("Johnny", "johnny@mail.com")
    b = B("Jodin", "johnyblaw@blawcloud.com", 30)

    mapper = Mapper()
    mapper.add_mapping(source=(A, B), target=C, mapping={"name": reversed_string})
    c = mapper.map((a, b), C)
    assert isinstance(c, C)
    assert c.name == "ynnhoJ"
    assert c.email == a.email
    assert c.age == b.age


def test_mapping_from_multiple_sources_with_extra_properties():
    """
    Test aggregate mapping with additional properties provided via extra parameter.

    Verifies that both aggregated source properties and extra properties are correctly set.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email
            super().__init__()

    class B:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str, age: int):
            self.name = name
            self.email = email
            self.age = age
            super().__init__()

    class C:
        def __init__(self, name: str, email: str, age: int, nickname: str):
            self.name = name
            self.email = email
            self.age = age
            self.nickname = nickname
            super().__init__()

    a = A("Johnny", "johnny@mail.com")
    b = B("Jodin", "johnyblaw@blawcloud.com", 30)

    mapper = Mapper()
    mapper.add_mapping(source=(A, B), target=C, mapping={"name": reversed_string})
    c = mapper.map((a, b), C, extra={"nickname": "J"})
    assert isinstance(c, C)
    assert c.name == "ynnhoJ"
    assert c.email == a.email
    assert c.age == b.age
    assert c.nickname == "J"


@pytest.mark.parametrize(
    "skip_init, check_if_raised",
    [(True, does_not_raise()), (False, pytest.raises(TypeError))],
)
def test_mapping_from_multiple_sources_with_missing_property(
    skip_init, check_if_raised
):
    """
    Test aggregate mapping behavior when required properties are missing from all sources.

    Verifies proper handling of missing properties based on skip_init parameter.
    """

    class A:
        def __init__(self, email: str):
            self.email = email
            super().__init__()

    class B:
        def __init__(self, email: str, age: int):
            self.email = email
            self.age = age
            super().__init__()

    class C:
        def __init__(self, name: str, email: str, age: int):
            self.name = name
            self.email = email
            self.age = age
            super().__init__()

    a = A("johnny@mail.com")
    b = B("johnyblaw@blawcloud.com", 30)

    mapper = Mapper()
    mapper.add_mapping(source=(A, B), target=C)
    with check_if_raised:
        c = mapper.map((a, b), C, skip_init=skip_init)


def test_mapping_properties_with_different_names():
    """
    Test mapping between properties with different names in source and target.

    Verifies that the mapping dictionary correctly handles property name translations.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email_address: str):
            self.name = name
            self.email_address = email_address

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(
        source=A,
        target=B,
        mapping={"email": "email_address"},
    )

    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == a.name
    assert b.email_address == a.email


def test_mapping_properties_with_different_names_and_transformation():
    """
    Test mapping between differently named properties with transformation functions.

    Verifies that both name translation and value transformation work together.
    """

    class A:
        name: str = None
        email: str = None

        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, reverse_name: str, email_address: str):
            self.reverse_name = reverse_name
            self.email_address = email_address

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(
        source=A,
        target=B,
        mapping={
            "name": ("reverse_name", reversed_string),
            "email": "email_address",
        },
    )

    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.reverse_name == "ynnhoJ"
    assert b.email_address == a.email


def test_mapping_dataclass_to_dataclass():
    """
    Test mapping functionality with Python dataclasses.

    Verifies that the mapper works correctly with dataclass-decorated classes.
    """

    @dataclass
    class A:
        name: str
        email: str

    @dataclass
    class B:
        name: str
        email: str

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B)

    a = A("Johnny", "johnny@email.com")

    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == a.name
    assert b.email == a.email


def test_mapping_from_dataclass_instance_with_transformation():
    """
    Test mapping from a dataclass instance with transformations.

    Verifies that the mapper correctly handles dataclass instances and applies transformations.
    """

    @dataclass
    class A:
        name: str
        email: str

    @dataclass
    class B:
        name: str
        email: str

    a = A("Johnny", "johnny@email.com")
    mapper = Mapper()
    mapper.add_mapping(source=a, target=B, mapping={"name": reversed_string})

    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == reversed_string(a.name)
    assert b.email == a.email


def test_mapping_using_attribute_name_list():
    """
    Test mapping using a list of attribute names instead of a mapping dictionary.

    Verifies that the mapper can handle simple attribute lists for direct mappings.
    """

    class A:
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

    class B:
        name: str = None
        favorite_food: List[str] = None

        def __init__(self, name, favorite_food):
            self.name = name
            self.favorite_food = favorite_food

    a = A(
        "Johnny",
        "johnny@email.com",
        35,
        "programmer",
        "my street nº 777",
        ["churrasco", "pizza"],
    )
    mapper = Mapper()
    mapper.add_mapping(source=a, target=B, mapping=["name", "favorite_food"])
    b = mapper.map(a, B)

    assert isinstance(b, B)
    assert b.name == a.name
    assert b.favorite_food == a.favorite_food


def test_mapping_ignores_nonexistent_target_attributes():
    """
    Test that the mapper only copies attributes that exist in the target object.

    Verifies that attempting to map non-existent target attributes doesn't raise errors.
    """

    class A:
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

    class B:
        name: str = None
        favorite_food: List[str] = None

        def __init__(self, name, favorite_food):
            self.name = name
            self.favorite_food = favorite_food

    a = A(
        "Johnny",
        "johnny@email.com",
        35,
        "programmer",
        "my street nº 777",
        ["churrasco", "pizza"],
    )
    mapper = Mapper()
    mapper.add_mapping(source=a, target=B)
    b = mapper.map(a, B)

    assert isinstance(b, B)
    assert b.name == a.name
    assert b.favorite_food == a.favorite_food


def test_mapping_classes_with_only_instance_attributes():
    """
    Test mapping between classes that only define attributes in __init__.

    Verifies that the mapper works correctly with dynamically created instance attributes.
    """

    class A:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("Johnny", "johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string})
    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
