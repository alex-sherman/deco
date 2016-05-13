import deco
import time
import md5


def test_synchronous(sleep_time):
    starttime = time.time()
    m = md5.new("Nobody inspects the spammish repetition")
    count = 0
    while((time.time() - starttime) < sleep_time/1000.0):
        m.update("p")
        a = m.hexdigest()
        count += 1
    return count


@deco.concurrent
def test(sleep_time):
    starttime = time.time()
    m = md5.new("Nobody inspects the spammish repetition")
    count = 0
    while((time.time() - starttime) < sleep_time/1000.0):
        m.update(" repetition")
        a = m.hexdigest()
        count += 1
    return count

test_time = 2
if __name__ == "__main__":
    times = [0.001, 0.005, 0.01, 0.1, 0.5, 1, 2, 5, 10, 20, 30]
    print("Measuring hashes/sec with single threaded synchronous calls")
    for time_duration in times:
        hashes = 0
        start = time.time()
        iterations = int(test_time/(time_duration/1000.0))
        if iterations > 20000:
            iterations = 20000
        for _ in range(iterations):
            hashes += test_synchronous(time_duration)
        print(time_duration, hashes / (time.time() - start))
    print("Measuring hashes/sec with deco multiprocess calls (3 workers)")
    for time_duration in times:
        hashes = 0
        start = time.time()
        iterations = int(test_time/(time_duration/1000.0))
        if iterations > 20000:
            iterations = 20000
        for _ in range(iterations):
            test(time_duration)
        result = test.wait()
        hashes = sum(result)
        print(hashes / (time.time() - start))
