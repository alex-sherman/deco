from __future__ import print_function
from deco import *
import time


@concurrent
def work():
    time.sleep(0.1)


@synchronized
def run():
    for _ in range(100):
        work()


if __name__ == "__main__":
    start = time.time()
    run()
    print("Executing in serial should take 10 seconds")
    print("Executing in parallel took:", time.time() - start, "seconds")