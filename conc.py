import multiprocessing
import multiprocessing.reduction
from multiprocessing import Process, Pipe, Queue, Pool
from threading import Thread
from itertools import izip
import time, inspect
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

    def __setitem__(self, key, value):
        self.value.__setitem__(key, value)
        self.result_queue.put((self.arg_id, key, value))

    def __getitem__(self, key):
        return self.value.__getitem__(key)

class concurrent(object):
    def __init__(self, *args):
        self.globals = []
        if len(args) > 0 and type(args[0]) == types.FunctionType:
            self.f = args[0]
        else:
            self.globals = list(args)
        self.num_workers = 4
        self.param_list = []
        self.processes = None
        self.manager = None
        self.task_queues = [Pipe(False) for _ in range(self.num_workers)]
        self.qi = 0
        self.t3 = 0
        self.arg_proxies = {}

    def __call__(self, *args):
        if len(args) > 0 and type(args[0]) == types.FunctionType:
            self.f = args[0]
            #exit()
            return self
        if self.manager == None:
            self.manager = multiprocessing.Manager()
        if self.processes == None:
            self.operation_queue = self.manager.Queue()
            self.processes = [Process(target = concEntry, args=(i, marshal.dumps(self.f.func_code), q[0]))
                for i, q in enumerate(self.task_queues)]
            for proc in self.processes: proc.start()
        args = list(args)
        frm = inspect.stack()[1]
        mod = inspect.getmodule(frm[0])
        args =  args
        global_args = {g: getattr(mod, g) for g in self.globals}
        for i, arg in enumerate(args):
            if type(arg) is dict or type(arg) is list:
                if not id(arg) in self.arg_proxies:
                    value = argValue(id(arg), arg, self.operation_queue)
                    self.arg_proxies[id(arg)] = value
                    for queue in self.task_queues:
                        queue[1].send(value)
                args[i] = self.arg_proxies[id(arg)].proxy
        self.task_queues[self.qi][1].send((args, global_args))
        self.qi += 1
        self.qi %= self.num_workers
    def process_operation_queue(self):
        arg_id, key, value = self.operation_queue.get()
        self.arg_proxies[arg_id].value.__setitem__(key, value)
    def wait(self):
        for task_queue in self.task_queues:
            task_queue[1].send(None)
        t1 = time.time()
        for proc in self.processes:
            proc.join()
        t2 = time.time()
        while not self.operation_queue.empty():
            self.process_operation_queue()
        t3 = time.time()
        print "Join Time:", t2 - t1
        print "Op Queue Time:", t3 - t2
        self.processes = None
        self.arg_proxies = {}
