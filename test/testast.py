import unittest
import ast
import inspect
from deco import *

@concurrent
def conc_func():
    pass

@synchronized
def body_cases():
    conc_func()
    a = True if False else False
    b = (lambda : True)()

class TestAST(unittest.TestCase):

    def test_body_cases(self):
        body_cases()

if __name__ == "__main__":
    unittest.main()
