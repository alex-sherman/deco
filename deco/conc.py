import multiprocessing
import multiprocessing.reduction
from multiprocessing import Process, Pipe, Queue, Pool
from threading import Thread
from itertools import izip
import time, inspect, ast
import marshal, types

def reduce(connection):
    return multiprocessing.reduction.reduce_connection(connection)

def concEntry(index, target_function, arg_pipe):
    code = marshal.loads(target_function)
    f = types.FunctionType(code, globals(), "f")
    globals()['f'] = f
    argValues = {}
    while True:
        recv = arg_pipe.recv()
        if recv == None: return
        if type(recv) is argValue:
            argValues[recv.arg_id] = recv
            continue
        args, global_args = recv
        for arg in global_args.values():
            if type(arg) is argProxy:
                arg.with_backing(argValues[arg.arg_id])
        args = [arg.with_backing(argValues[arg.arg_id]) if type(arg) is argProxy else arg for arg in args]
        globals().update(global_args)
        f(*args)

class argValue(object):
    def __init__(self, arg_id, value, result_queue):
        self.arg_id = arg_id
        self.value = value
        self.result_queue = result_queue
        self.proxy = argProxy(arg_id)

class argProxy(object):
    def __init__(self, arg_id):
        self.arg_id = arg_id

    def with_backing(self, arg_value):
        self.result_queue = arg_value.result_queue
        self.value = arg_value.value
        return self

    def __getattr__(self, name):
        if hasattr(self, 'value') and hasattr(self.value, name):
            return getattr(self.value, name)
        raise AttributeError

    def __setitem__(self, key, value):
        self.value.__setitem__(key, value)
        self.result_queue.put((self.arg_id, key, value))

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
        self.param_list = []
        self.workers = None
        self.manager = None
        self.task_queues = [Pipe(False) for _ in range(self.processes)]
        self.qi = 0
        self.t3 = 0
        self.arg_proxies = {}

    def replaceWithProxies(self, args):
        for i, arg in enumerate(args):
            if type(arg) is dict or type(arg) is list:
                if not id(arg) in self.arg_proxies:
                    value = argValue(id(arg), arg, self.operation_queue)
                    self.arg_proxies[id(arg)] = value
                    for queue in self.task_queues:
                        queue[1].send(value)
                args[i] = self.arg_proxies[id(arg)].proxy

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
        self.free_names = findFreeNames(f)
    def __call__(self, *args):
        if len(args) > 0 and type(args[0]) == types.FunctionType:
            self.setFunction(args[0])
            return self
        if self.manager == None:
            self.manager = multiprocessing.Manager()
        if self.workers == None:
            self.operation_queue = self.manager.Queue()
            self.workers = [Process(target = concEntry, args=(i, marshal.dumps(self.f.func_code), q[0]))
                for i, q in enumerate(self.task_queues)]
            for proc in self.workers: proc.start()
        args = list(args)
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        global_arg_keys = [g for g in self.free_names if hasattr(mod, g)]
        global_args = [getattr(mod, g) for g in global_arg_keys]
        self.replaceWithProxies(args)
        self.replaceWithProxies(global_args)
        self.task_queues[self.qi][1].send((args, dict(zip(global_arg_keys, global_args))))
        self.qi += 1
        self.qi %= self.processes
    def process_operation_queue(self):
        arg_id, key, value = self.operation_queue.get()
        self.arg_proxies[arg_id].value.__setitem__(key, value)
    def wait(self):
        for task_queue in self.task_queues:
            task_queue[1].send(None)
        for proc in self.workers:
            proc.join()
        while not self.operation_queue.empty():
            self.process_operation_queue()
        self.workers = None
        self.arg_proxies = {}
