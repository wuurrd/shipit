from shipit.models import DataSource, DataFilter


class DummyDataSource(DataSource):
    def update(self):
        pass

    def __iter__(self):
        return iter(range(10))

def is_even(x):
    return x % 2 == 0


class EvenNumberFilter(DataFilter):
    def filter(self, iterable):
        for i in iterable:
            if is_even(i):
                yield i


class GreaterThanFilter(DataFilter):
    def __init__(self, base):
        self.base = base

    def filter(self, iterable):
        for i in iterable:
            if i > self.base:
                yield i


def test_data_filter():
    ds = DummyDataSource()
    even_filter = EvenNumberFilter()
    for x in even_filter.filter(iter(ds)):
        assert is_even(x)

    limit = 3
    greater_than_filter = GreaterThanFilter(limit)
    for x in greater_than_filter.filter(iter(ds)):
        assert x > limit

    # Data filters are composable
    composed = DataFilter.compose(even_filter, greater_than_filter)
    for x in composed(iter(ds)):
        assert x > limit and is_even(x)
