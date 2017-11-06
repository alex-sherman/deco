import unittest
import ast
import inspect
from deco import *

@concurrent
def conc_func(*args, **kwargs):
    return kwargs

@synchronized
def body_cases():
    conc_func()
    a = True if False else False
    b = (lambda : True)()

@synchronized
def tainted_return():
    data = []
    data.append(conc_func(data))
    return data

def indented():
    @synchronized
    def _indented():
        conc_func()

    return _indented()

@synchronized
def kwarged_sync(**kwargs):
    data = []
    data.append(conc_func(**kwargs))
    return data[0]

@synchronized
def subscript_args():
    d = type('', (object,), {"items": {(0,0): 0}})()
    conc_func(d.items[0, 0])
    #Read d to force a synchronization event
    d = d
    output = conc_func.in_progress
    return output

class TestAST(unittest.TestCase):

    #This just shouldn't throw any exceptions
    def test_body_cases(self):
        body_cases()

    #This just shouldn't throw any exceptions
    def test_indent_cases(self):
        indented()

    #This just shouldn't throw any exceptions
    def test_tainted_return(self):
        tainted_return()

    def test_subscript_args(self):
        self.assertFalse(subscript_args())

    def test_kwarged_sync(self):
        self.assertTrue(kwarged_sync(test = "test")["test"] == "test")

if __name__ == "__main__":
    unittest.main()
