import conc, time, math

SLEEP_TIME = 0.1
@conc.concurrent("SLEEP_TIME")
def test(a,y):
    time.sleep(SLEEP_TIME)
    a[y] = y ** 2

SIZE = 100
if __name__ == "__main__":
    a = dict([(i, 0) for i in range(1000)])
    b = {}
    start = time.time()
    for x in range(SIZE):
        test(a, x)
    test.wait()
    ctime = time.time() - start
    #print "Result of a:", a
    start = time.time()
    for x in range(SIZE):
        test.f(b, x)
    stime = time.time() - start
    #print "Result of b:", b
    print "Concurrent style:", ctime
    print "Serial style:", stime