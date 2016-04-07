import multiprocessing
import multiprocessing.reduction
from multiprocessing import Process, Pipe, Queue, Pool
from threading import Thread
from itertools import izip
import time
import marshal, types

def reduce(connection):
    return multiprocessing.reduction.reduce_connection(connection)

def concEntry(index, target_function, arg_pipe):
    code = marshal.loads(target_function)
    f = types.FunctionType(code, globals(), "f")
    while True:
        args = arg_pipe.recv()
        if args == None: return
        f(*args)

class argProxy(object):
    def __init__(self, arg_id, value, result_queue):
        self.arg_id = arg_id
        self.value = value
        self.result_queue = result_queue

    def __setitem__(self, key, value):
        self.value.__setitem__(key, value)
        self.result_queue.put((self.arg_id, key, value))

    def __getitem__(self, key):
        return self.value.__getitem__(key)

class concurrent_thread(Thread):
    def __init__(self, conc):
        self.conc = conc
        Thread.__init__(self)

class concurrent(object):
    def __init__(self, f):
        self.num_workers = 4
        self.f = f
        self.param_list = []
        #self.procs = None
        self.processes = None
        self.task_queues = [Pipe(False) for _ in range(self.num_workers)]
        self.qi = 0
        self.t3 = 0
        self.arg_proxies = {}

    def __call__(self, *args):
        if self.processes == None:
            self.manager = multiprocessing.Manager()
            self.operation_queue = self.manager.Queue()
            #self.result = self.pool.map_async(concEntry,
            #    [(i, marshal.dumps(self.f.func_code), reduce(q[0]), self.operation_queue) for i, q in enumerate(self.task_queues)])
            self.processes = [Process(target = concEntry, args=(i, marshal.dumps(self.f.func_code), q[0]))
                for i, q in enumerate(self.task_queues)]
            for proc in self.processes: proc.start()
        args = list(args)
        for i, arg in enumerate(args):
            if type(arg) is dict:
                if not id(arg) in self.arg_proxies:
                    self.arg_proxies[id(arg)] = argProxy(id(arg), arg, self.operation_queue)
                args[i] = self.arg_proxies[id(arg)]
        self.task_queues[self.qi][1].send(args)
        self.qi += 1
        self.qi %= self.num_workers
    def process_operation_queue(self):
        arg_id, key, value = self.operation_queue.get()
        self.arg_proxies[arg_id].value.__setitem__(key, value)
    def wait(self):
        for task_queue in self.task_queues:
            task_queue[1].send(None)
        for proc in self.processes:
            proc.join(timeout = 1)
        while not self.operation_queue.empty():
            self.process_operation_queue()
