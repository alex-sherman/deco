import unittest
from deco import *

@concurrent
def kwarg_func(kwarg = None):
    kwarg[0] = "kwarged"
    return kwarg

@concurrent
def add_one(value):
    return value + 1

@synchronized
def for_loop(values):
    output = []
    for i in values:
        output.append(add_one(i))
    return [i - 1 for i in output]

class TestCONC(unittest.TestCase):

    def test_kwargs(self):
        list_ = [0]
        kwarg_func(kwarg = list_)
        kwarg_func.wait()
        self.assertEqual(list_[0], "kwarged")

    def test_for_loop(self):
        values = range(30)
        self.assertEqual(list(values), for_loop(values))

if __name__ == "__main__":
    unittest.main()
