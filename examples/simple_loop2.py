from __future__ import print_function
from deco import *
import time


@concurrent
def work(i):
    time.sleep(0.1)
    return i


@synchronized
def run():
    output = []
    for i in range(100):
        output.append(work(i))
    return output


if __name__ == "__main__":
    start = time.time()
    print(run())
    print("Executing in serial should take 10 seconds")
    print("Executing in parallel took:", time.time() - start, "seconds")