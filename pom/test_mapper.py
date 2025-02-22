from contextlib import nullcontext as does_not_raise

import pytest

from pom import Mapper


@pytest.mark.parametrize(
    "skip_init, check_if_raised",
    [(True, does_not_raise()), (False, pytest.raises(TypeError))],
)
def test_map_source_object_missing_property(skip_init, check_if_raised):
    class A:
        def __init__(self, email: str):
            self.email = email

    class B:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    a = A("johnny@mail.com")

    mapper = Mapper()
    mapper.add_mapping(source=A, target=B, mapping={"name": lambda n: n[::-1]})
    with check_if_raised:
        b = mapper.map(a, B, skip_init=skip_init)


def test_map_source_object_missing_property_to_instance_target_objet():
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


def test_add_mapping_source_object_missing_property_provided_in_the_mapping_dictionary():
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
        mapper.add_mapping(source=A, target=B, mapping={"name": lambda n: n[::-1]})


def test_map():
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
    mapper.add_mapping(source=A, target=B, mapping={"name": lambda n: n[::-1]})
    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"


def test_map_passing_target_as_instance():
    class A:
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
    mapper.add_mapping(source=A, target=B, mapping={"name": lambda n: n[::-1]})
    b = mapper.map(a, b)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == a.email


def test_map_exclusions_passing_target_as_instance():
    class A:
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
        source=A, target=B, mapping={"name": lambda n: n[::-1]}, exclusions=["email"]
    )
    b = mapper.map(a, b)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == None


def test_map_exclude():
    class A:
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
        source=A, target=B, mapping={"name": lambda n: n[::-1]}, exclusions=["email"]
    )
    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == "fixed@email.com"


def test_map_passing_extra_properties():
    class A:
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
    mapper.add_mapping(source=A, target=B, mapping={"name": lambda n: n[::-1]})
    b = mapper.map(a, B, extra={"age": 30})
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.age == 30


def test_map_aggregate():
    class A:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email
            super().__init__()

    class B:
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
    mapper.add_mapping(source=(A, B), target=C, mapping={"name": lambda n: n[::-1]})
    c = mapper.map((a, b), C)
    assert isinstance(c, C)
    assert c.name == "ynnhoJ"
    assert c.email == a.email
    assert c.age == b.age


def test_map_aggregate_passing_extra_properties():
    class A:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email
            super().__init__()

    class B:
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
    mapper.add_mapping(source=(A, B), target=C, mapping={"name": lambda n: n[::-1]})
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
def test_map_aggregate_missing_property(skip_init, check_if_raised):
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
    mapper.add_mapping(source=(A, B), target=C, mapping={"name": lambda n: n[::-1]})
    with check_if_raised:
        c = mapper.map((a, b), C, skip_init=skip_init)


def test_mapping_with_different_property_names():
    class A:
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


def test_mapping_with_different_property_names_and_transforming_function():
    class A:
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
            "name": ("reverse_name", lambda n: n[::-1]),
            "email": "email_address",
        },
    )

    b = mapper.map(a, B)
    assert isinstance(b, B)
    assert b.reverse_name == "ynnhoJ"
    assert b.email_address == a.email
