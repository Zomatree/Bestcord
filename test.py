class Foo:
    a: bool

    def __init_subclass__(cls, *, a=False) -> None:
        cls.a = a

class Bar(Foo, a=True):
    pass

print(Bar.a)
