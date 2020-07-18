# Python Object Mapper

Not ready for production.

## Quick Start



Somple classes.

```python
class A:
    def __init__(self, name: str, email: str):
        self.name = name
        self.email = email

class B:
    def __init__(self, name: str, email:str, age: str):
        self.name = name
        self.email = email
        self.age = age
        super().__init__()

class C:
    def __init__(self, name: str, email: str, age: str):
        self.name = name
        self.email  = email
        self.age = age
        super().__init__()
```

### Mapping only one object

```python
from pom import Mapper



mapper = Mapper()
mapper.add_mapping(
    source=A, 
    target=B, 
    mapping={'name': lambda n: n[::-1]})

a = A('Johnny', 'johnny@mail.com')
b = mapper.map(a, B)
```

### Using multiple object


```python
mapper = Mapper()
mapper.add_mapping(
    source=(A,B), 
    target=C, 
    mapping={'name': lambda n: n[::-1]}
)

a = A('Johnny', 'johnny@mail.com')
b = B('Jodin', 'johnyblaw@blawcloud.com', 30)
c = mapper.map((a,b), C)
```

Objects in the left of the source tuple have precedence in attribute discovery.