from pom import Mapper


def test_map():
    class A:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email

    class B:
        def __init__(self, name: str, email:str):
            self.name = name
            self.email = email

    a = A('Johnny', 'johnny@mail.com')

    mapper = Mapper()
    mapper.add_mapping(
        source=A, 
        target=B, 
        mapping={'name': lambda n: n[::-1]})
    b = mapper.map(a, B)


def test_map_aggregate():
    class A:
        def __init__(self, name: str, email: str):
            self.name = name
            self.email = email
            super().__init__()

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

    a = A('Johnny', 'johnny@mail.com')
    b = B('Jodin', 'johnyblaw@blawcloud.com', 30)

    mapper = Mapper()
    mapper.add_mapping(
        source=(A,B), 
        target=C, 
        mapping={'name': lambda n: n[::-1]}
    )
    c = mapper.map((a,b), C)
    assert c.name == "ynnhoJ"
    assert c.email == a.email
    assert c.age == b.age