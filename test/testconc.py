import unittest
from deco import *

@concurrent
def kwarg_func(kwarg = None):
    kwarg[0] = "kwarged"
    return kwarg

class TestAST(unittest.TestCase):

    def test_kwargs(self):
        list_ = [0]
        kwarg_func(kwarg = list_)
        kwarg_func.wait()
        self.assertEqual(list_[0], "kwarged")


if __name__ == "__main__":
    unittest.main()
