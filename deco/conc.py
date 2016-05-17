from multiprocessing import Pool
import inspect
import ast
from . import astutil
import types


def concWrapper(f, args):
    result = concurrent.functions[f](*args)
    operations = [inner for outer in args if type(outer) is argProxy for inner in outer.operations]
    return result, operations


class argProxy(object):
    def __init__(self, arg_id, value):
        self.arg_id = arg_id
        self.operations = []
        self.value = value

    def __getattr__(self, name):
        if name in ["__getstate__", "__setstate__"]:
            raise AttributeError
        if hasattr(self, 'value') and hasattr(self.value, name):
            return getattr(self.value, name)
        raise AttributeError

    def __setitem__(self, key, value):
        self.value.__setitem__(key, value)
        self.operations.append((self.arg_id, key, value))

    def __getitem__(self, key):
        return self.value.__getitem__(key)


class synchronized(object):
    def __init__(self, f):
        self.orig_f = f
        self.f = None

    def __call__(self, *args, **kwargs):
        if self.f is None:
            source = inspect.getsourcelines(self.orig_f)
            source = "".join(source[0])
            fast = ast.parse(source)
            node = fast
            rewriter = astutil.SchedulerRewriter(concurrent.functions.keys())
            rewriter.visit(node.body[0])
            ast.fix_missing_locations(node)
            out = compile(node, "<string>", "exec")
            exec(out, self.orig_f.__globals__)
            self.f = self.orig_f.__globals__[self.orig_f.__name__]
        return self.f(*args, **kwargs)


class concurrent(object):
    functions = {}

    def __init__(self, *args, **kwargs):
        self.pool_args = []
        self.pool_kwargs = {}
        if len(args) > 0 and isinstance(args[0], types.FunctionType):
            self.setFunction(args[0])
        else:
            self.pool_args = args
            self.pool_kwargs = kwargs
        self.results = []
        self.assigns = []
        self.arg_proxies = {}
        self.pool = None

    def replaceWithProxies(self, args):
        args_iter = args.iteritems() if type(args) is dict else enumerate(args)
        for i, arg in args_iter:
            if type(arg) is dict or type(arg) is list:
                if not id(arg) in self.arg_proxies:
                    self.arg_proxies[id(arg)] = argProxy(id(arg), arg)
                args[i] = self.arg_proxies[id(arg)]

    def setFunction(self, f):
        concurrent.functions[f.__name__] = f
        self.f_name = f.__name__

    def assign(self, target, *args, **kwargs):
        self.assigns.append((target, self(*args, **kwargs)))

    def __call__(self, *args, **kwargs):
        if len(args) > 0 and isinstance(args[0], types.FunctionType):
            self.setFunction(args[0])
            return self
        if self.pool is None:
            self.pool = Pool(*self.pool_args, **self.pool_kwargs)
        args = list(args)
        self.replaceWithProxies(args)
        result = self.pool.apply_async(concWrapper, [self.f_name, args])
        self.results.append(result)
        return result

    def process_operation_queue(self, ops):
        for arg_id, key, value in ops:
            self.arg_proxies[arg_id].value.__setitem__(key, value)

    def wait(self):
        results = []
        while len(self.results) > 0:
            result, operations = self.results.pop().get()
            self.process_operation_queue(operations)
            results.append(result)
        for assign in self.assigns:
            assign[0][0][assign[0][1]] = assign[1].get()[0]
        self.arg_proxies = {}
        return results
