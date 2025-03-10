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
def test_skip_init(skip_init, check_if_raised):
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


def test_raise_type_error_when_add_mapping_source_class_missing_property_provided_in_the_mapping_dictionary():
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


def test_add_mapping_with_source_as_object_instance():
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


def test_add_mapping_with_source_as_tuple_of_object_instance():
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

    mapper.add_mapping(source=(a,b), target=C, mapping={"name": reversed_string})
    c = mapper.map((a2, b), C, skip_init=True)
    assert isinstance(c, C)
    assert c.name == "2ynnhoJ"



def test_type_error_message_contains_all_missing_attributes():
    """
    The TypeError message when adding a mapper with explict attribute names should contain all missing attributes.
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
        mapper.add_mapping(source=A, target=B, mapping={"name": reversed_string, "job": "job", "age": "age"})
    except TypeError as e:
        assert str(e) == "Mapping attributes age, job and name not found in source A."


def test_type_error_message_contains_all_missing_attributes_when_source_is_iterable():
    """
    The TypeError message when adding a mapper with explict attribute names should contain all missing attributes.
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
        mapper.add_mapping(source=(A, B), target=C, mapping={"name": reversed_string, "job": "job", "age": "age"})
    except TypeError as e:
        assert str(e) == "Mapping attributes age, job and name not found in sources A and B."


def test_type_error_message_contains_one_missing_attribute_from_one_source_only():
    """
    This is only to test the version of the message error with only one attribute and only one source, just singular text stuff.
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

def test_simplest_map_case():
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


def test_map_without_default_values_in_class_attributes():
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

def test_map_passing_target_as_instance():
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
    b = mapper.map(a, b) # There is the instance thing
    assert isinstance(b, B)
    assert b.name == "ynnhoJ"
    assert b.email == a.email


def test_map_exclusions_passing_target_as_instance():

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


def test_map_exclude():
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


def test_map_passing_extra_properties():
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


def test_map_aggregate():
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


def test_map_aggregate_passing_extra_properties():
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
    mapper.add_mapping(source=(A, B), target=C)
    with check_if_raised:
        c = mapper.map((a, b), C, skip_init=skip_init)


def test_mapping_with_different_property_names():
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


def test_mapping_with_different_property_names_and_transforming_function():
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


def test_it_works_with_dataclasses():
    
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



def test_it_works_with_dataclasses_instance():
    
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

def test_mapping_as_a_list_of_attribute_names():
        
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
            self.jobp= job
            self.address = address
            self.favorite_food = favorite_food

    class B:
        name: str = None
        favorite_food: List[str] = None
        def __init__(self, name, favorite_food):
            self.name = name
            self.favorite_food = favorite_food
        
    a = A("Johnny", "johnny@email.com", 35, "programmer", "my street nº 777", ["churrasco", "pizza"])
    mapper = Mapper()
    mapper.add_mapping(source=a, target=B, mapping=["name", "favorite_food"])
    b = mapper.map(a, B)
    
    assert isinstance(b, B)
    assert b.name == a.name
    assert b.favorite_food == a.favorite_food


def test_does_not_try_to_copy_from_source_object_attributes_missing_from_the_target_objec_2():
        
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
            self.jobp= job
            self.address = address
            self.favorite_food = favorite_food

    class B:
        name: str = None
        favorite_food: List[str] = None
        def __init__(self, name, favorite_food):
            self.name = name
            self.favorite_food = favorite_food
        
    a = A("Johnny", "johnny@email.com", 35, "programmer", "my street nº 777", ["churrasco", "pizza"])
    mapper = Mapper()
    mapper.add_mapping(source=a, target=B)
    b = mapper.map(a, B)
    
    assert isinstance(b, B)
    assert b.name == a.name
    assert b.favorite_food == a.favorite_food


def test_map_works_without_with_only_instance_attributes():
    raise
