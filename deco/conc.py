from multiprocessing import Pool
import inspect
import ast
import types
from ast import NodeTransformer


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
        if hasattr(self, 'value') and hasattr(self.value, name):
            return getattr(self.value, name)
        raise AttributeError

    def __setitem__(self, key, value):
        self.value.__setitem__(key, value)
        self.operations.append((self.arg_id, key, value))

    def __getitem__(self, key):
        return self.value.__getitem__(key)


class SchedulerRewriter(NodeTransformer):
    def __init__(self, concurrent_funcs):
        self.arguments = set()
        self.concurrent_funcs = concurrent_funcs
        self.encountered_funcs = set()

    def references_arg(self, node):
        if not isinstance(node, ast.AST):
            return False
        if type(node) is ast.Name:
            return type(node.ctx) is ast.Load and node.id in self.arguments
        for field in node._fields:
            if field == "body": continue
            value = getattr(node, field)
            if not hasattr(value, "__iter__"):
                value = [value]
            if any([self.references_arg(child) for child in value]):
                return True
        return False

    @staticmethod
    def subscript_name(node):
        if type(node) is ast.Name:
            return node.id
        elif type(node) is ast.Subscript:
            return SchedulerRewriter.subscript_name(node.value)
        raise ValueError("Assignment attempted on something that is not index based")

    def is_concurrent_call(self, node):
        return type(node) is ast.Call and type(node.func) is ast.Name and node.func.id in self.concurrent_funcs

    def is_valid_assignment(self, node):
        return type(node) is ast.Assign and self.is_concurrent_call(node.value)

    def encounter_call(self, call):
        self.encountered_funcs.add(call.func.id)
        for arg in call.args:
            self.arguments.add(SchedulerRewriter.subscript_name(arg))

    def generic_visit(self, node):
        super(NodeTransformer, self).generic_visit(node)
        if hasattr(node, 'body'):
            returns = [i for i, child in enumerate(node.body) if type(child) is ast.Return]
            if len(returns) > 0:
                for wait in self.get_waits():
                    node.body.insert(returns[0], wait)
            inserts = []
            for i, child in enumerate(node.body):
                if type(child) is ast.Expr and self.is_concurrent_call(child.value):
                    self.encounter_call(child.value)
                elif self.is_valid_assignment(child):
                    call = child.value
                    self.encounter_call(call)
                    name = child.targets[0].value
                    self.arguments.add(SchedulerRewriter.subscript_name(name))
                    index = child.targets[0].slice.value
                    call.func = ast.Attribute(call.func, 'assign', ast.Load())
                    call.args = [ast.Tuple([name, index], ast.Load())] + call.args
                    node.body[i] = ast.Expr(call)
                elif self.references_arg(child):
                    inserts.insert(0, i)
            for index in inserts:
                for wait in self.get_waits():
                    node.body.insert(index, wait)

    def get_waits(self):
        return [ast.Expr(ast.Call(ast.Attribute(ast.Name(fname, ast.Load()), 'wait', ast.Load()), [], [], None, None)) for fname in self.encountered_funcs]

    def visit_FunctionDef(self, node):
        node.decorator_list = []
        self.generic_visit(node)
        node.body += self.get_waits()
        return node


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
            rewriter = SchedulerRewriter(concurrent.functions.keys())
            rewriter.visit(node.body[0])
            ast.fix_missing_locations(node)
            out = compile(node, "<string>", "exec")
            exec out in self.orig_f.func_globals
            self.f = self.orig_f.func_globals[self.orig_f.__name__]
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
        for i, arg in enumerate(args):
            if type(arg) is dict or type(arg) is list:
                if not id(arg) in self.arg_proxies:
                    self.arg_proxies[id(arg)] = argProxy(id(arg), arg)
                args[i] = self.arg_proxies[id(arg)]

    def setFunction(self, f):
        concurrent.functions[f.__name__] = f
        self.f_name = f.__name__

    def assign(self, target, *args):
        self.assigns.append((target, self(*args)))

    def __call__(self, *args):
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
