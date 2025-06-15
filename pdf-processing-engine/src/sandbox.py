class A():
    def __init__(self) -> None:
        self.id = [1]

    def __repr__(self) -> str:
        return f'A({self.id})'

    def set_id(self, id):
        self.id = id


class B():
    def __init__(self) -> None:
        self.a = A()

    def __repr__(self) -> str:
        return f'B({self.a})'


a = A()
b = B()

a
b

a.id.append(2)
a
b
