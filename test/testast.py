import unittest
import ast
import inspect
from deco import *

@concurrent
def conc_func(*args, **kwargs):
    pass

@synchronized
def body_cases():
    conc_func()
    a = True if False else False
    b = (lambda : True)()

def indented():
    @synchronized
    def _indented():
        return conc_func()

    return _indented()

@synchronized
def subscript_args():
    d = type('', (object,), {"items": {(0,0): 0}})()
    conc_func(d.items[0, 0])
    #Read d to force a synchronization event
    d = d
    return conc_func.in_progress

class TestAST(unittest.TestCase):

    #This just shouldn't throw any exceptions
    def test_body_cases(self):
        body_cases()

    #This just shouldn't throw any exceptions
    def test_indent_cases(self):
        indented()

    def test_subscript_args(self):
        self.assertFalse(subscript_args())

if __name__ == "__main__":
    unittest.main()
