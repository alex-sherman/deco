import unittest
from deco import *

@concurrent
def kwarg_func(kwarg = None):
    return kwarg

class TestAST(unittest.TestCase):

    def test_kwargs(self):
        self.assertEqual(kwarg_func(kwarg = "kwarged").get(), "kwarged")

if __name__ == "__main__":
    unittest.main()
