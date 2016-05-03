import multiprocessing
import multiprocessing.reduction
from multiprocessing import Process, Pipe, Queue, Pool
from threading import Thread
from itertools import izip
import time, inspect, ast
import marshal, types

def concWrapper(args, global_args):
        globals().update(global_args)
        result = f(*args)
        operations = [inner for outer in args if type(outer) is argProxy for inner in outer.operations]
        return result, operations

class argProxy(object):
    def __init__(self, arg_id, value):
        self.arg_id = arg_id
        self.operations = []
        self.value = value

    def __getattr__(self, name):
        if hasattr(self, 'value') and hasattr(self.value, name):
            return getattr(self.value, name)
        raise AttributeError

    def __setitem__(self, key, value):
        self.value.__setitem__(key, value)
        self.operations.append((self.arg_id, key, value))

    def __getitem__(self, key):
        return self.value.__getitem__(key)

class concurrent(object):
    params = ['processes']
    def __init__(self, *args, **kwargs):
        self.processes = 3
        if len(args) > 0 and type(args[0]) == types.FunctionType:
            self.setFunction(args[0])
        else:
            self.__dict__.update({concurrent.params[i]: arg for i, arg in enumerate(args)})
            self.__dict__.update({key: kwargs[key] for key in concurrent.params if key in kwargs})
        self.results = []
        self.arg_proxies = {}
        self.p = None

    def replaceWithProxies(self, args):
        for i, arg in enumerate(args):
            if type(arg) is dict or type(arg) is list:
                if not id(arg) in self.arg_proxies:
                    self.arg_proxies[id(arg)] = argProxy(id(arg), arg)
                args[i] = self.arg_proxies[id(arg)]

    def setFunction(self, f):
        def findFreeNames(f):
            source = inspect.getsourcelines(f)
            source = "".join(source[0])
            fast = ast.parse(source)
            f_args_names = set([a.id for a in fast.body[0].args.args])
            f_body = fast.body[0].body
            f_vars_names = set()
            f_free_names = set()
            for line in f_body:
                for n in ast.walk(line):
                    if isinstance(n, ast.Name):
                        f_vars_names.add(n.id)
            f_free_names = f_vars_names.difference(f_args_names)
            return f_free_names
        self.f = f
        globals()['f'] = f
        self.free_names = findFreeNames(f)
    def __call__(self, *args):
        if len(args) > 0 and type(args[0]) == types.FunctionType:
            self.setFunction(args[0])
            return self
        if self.p == None:
            self.p = Pool(self.processes)
        args = list(args)
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        global_arg_keys = [g for g in self.free_names if hasattr(mod, g) and type(getattr(mod, g)) != types.ModuleType]
        global_args = [getattr(mod, g) for g in global_arg_keys]
        self.replaceWithProxies(args)
        self.replaceWithProxies(global_args)
        self.results.append(self.p.apply_async(concWrapper, [args, dict(zip(global_arg_keys, global_args))]))
    def process_operation_queue(self, ops):
        for arg_id, key, value in ops:
            self.arg_proxies[arg_id].value.__setitem__(key, value)
    def wait(self):
        results = []
        while len(self.results) > 0:
            result, operations = self.results.pop().get()
            self.process_operation_queue(operations)
            results.append(result)
        self.arg_proxies = {}
        return results
