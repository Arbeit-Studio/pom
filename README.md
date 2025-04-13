# Python Object Mapper

## ⚠️ Alpha Release

This library is currently in alpha. While the core API is mostly stable and unlikely to change significantly before the final release, the project is still under development and has limited real-world usage. Bugs, crashes, or unexpected behavior may occur.

## Quick Start

Sample classes.

```python
class A:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

class B:
    def __init__(self, name: str, email:str, age: int):
        self.name = name
        self.email = email
        self.age = age

class C:
    def __init__(self, name: str, email: str, age: int):
        self.name = name
        self.email  = email
        self.age = age
```

### Mapping only one object

1. Define the mapping.

```python
from pom import Mapper

mapper = Mapper()

mapper.add_mapping(
    source=A,
    target=B,
    mapping={'name': lambda n: n[::-1]}
)

```

2. Map the object

```python
a = A('Johnny', 'johnny@mail.com')
b = mapper.map(a, B, extra={"age": 35})
```

3. The result

```python
>>> print(vars(b))
{'name': 'ynnhoJ', 'email': 'johnny@mail.com', 'age': 35}
```

### Using multiple object

1. Define the mapping as a tuple of two classes as source `(A, B)`.

```python
mapper = Mapper()

mapper.add_mapping(
    source=(A,B),
    target=C,
    mapping={'name': lambda n: n[::-1]}
)
```

2. Map the objects as usual.

```python
a = A('Johnny', 'johnny@mail.com')
b = B('Jodin', 'johnyblaw@blawcloud.com', 30)
c = mapper.map((a,b), C)
```

**Objects in the left of the source tuple have precedence in the attribute discovery from the map method.**

3. The result.

```python
>>> print(vars(c))
{'name': 'ynnhoJ', 'email': 'johnny@mail.com', 'age': 30}
```

## Mapper API Reference

The Mapper class provides flexible object-to-object mapping with support for transformations, exclusions, and multiple source objects.

### Basic Usage

#### Simple Mapping

Map properties between objects with identical attribute names:

```python
from pom import Mapper

class Source:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

class Target:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

mapper = Mapper()
mapper.add_mapping(source=Source, target=Target)

source = Source("John", "john@example.com")
result: Target = mapper.map(source, Target)
```

#### Property Transformations

Apply transformations to properties during mapping:

```python
def reverse_string(s: str) -> str:
    return s[::-1]

mapper.add_mapping(
    source=Source,
    target=Target,
    mapping={"name": reverse_string}
)
```

#### Property Name Translations

Map properties with different names:

```python
class Target:
    def __init__(self, full_name: str, email_address: str):
        self.full_name = full_name
        self.email_address = email_address

mapper.add_mapping(
    source=Source,
    target=Target,
    mapping={
        "name": "full_name",
        "email": "email_address"
    }
)
```

#### Combined Transformations and Translations

Apply both transformations and name translations:

```python
mapper.add_mapping(
    source=Source,
    target=Target,
    mapping={
        "name": ("full_name", reverse_string),
        "email": "email_address"
    }
)
```

### Advanced Features

#### Multiple Source Objects

Map from multiple source objects to a single target:

```python
class SourceA:
    def __init__(self, name: str):
        self.name = name

class SourceB:
    def __init__(self, email: str, age: int):
        self.email = email
        self.age = age

class Target:
    def __init__(self, name: str, email: str, age: int):
        self.name = name
        self.email = email
        self.age = age

mapper.add_mapping(
    source=(SourceA, SourceB),
    target=Target
)

a = SourceA("John")
b = SourceB("john@example.com", 30)
result = mapper.map((a, b), Target)
```

Note: Objects earlier in the source tuple take precedence for overlapping attributes.

#### Property Exclusions

Exclude specific properties from mapping:

```python
mapper.add_mapping(
    source=Source,
    target=Target,
    exclusions=["email"]
)
```

#### Extra Properties

Provide additional properties during mapping:

```python
result = mapper.map(
    source,
    Target,
    extra={"age": 30}
)
```

**The params on the extra map overrides attributes copied from the source.**

#### Dataclass Support

Map between dataclass objects:

```python
from dataclasses import dataclass

@dataclass
class SourceData:
    name: str
    email: str

@dataclass
class TargetData:
    name: str
    email: str

mapper.add_mapping(source=SourceData, target=TargetData)
```

#### Instance-Based Mapping

Map to existing target instances:

```python
source = Source("John", "john@example.com")
target = Target(None, None)

mapper.add_mapping(source=Source, target=Target)
mapper.map(source, target)  # Updates existing target instance
```

### API Reference

#### Mapper Class

##### `__init__()`

Initialize a new Mapper instance.

##### `add_mapping(*, source, target, mapping=None, exclusions=None)`

Add a mapping configuration.

Parameters:

- `source`: Source class or tuple of source classes
- `target`: Target class
- `mapping`: Dict of property mappings or list of property names
- `exclusions`: List of properties to exclude from mapping

##### `map(source, target, skip_init=False, extra=None)`

Map source object(s) to target.

Parameters:

- `source`: Source object or tuple of objects
- `target`: Target class or instance
- `skip_init`: Skip **init** when creating target instance
- `extra`: Additional attributes to set on target

Returns:

- Instance of target type with mapped properties

### Error Handling

The Mapper provides descriptive error messages for common issues:

- Missing required properties
- Invalid mapping configurations
- Excluded required properties
- Invalid transformation functions

Example error handling:

```python
try:
    mapper.add_mapping(source=Source, target=Target)
    result: Target = mapper.map(source, target)
except TypeError as e:
    print(f"Mapping error: {e}")
except RuntimeError as e:
    print(f"Configuration error: {e}")
```
