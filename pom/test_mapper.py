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


def test_map_aggregate():
    class A:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email
            super().__init__()

    class B:
        def __init__(self, name: str, email: str, age: str):
            self.name = name
            self.email = email
            self.age = age
            super().__init__()

    class C:
        def __init__(self, name: str, email: str, age: str):
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
