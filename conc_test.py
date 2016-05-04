import deco, time, math

@deco.concurrent
def test(sleep_time):
    time.sleep(sleep_time)

SIZE = 100
if __name__ == "__main__":
    processes = [1,2,3,4]
    times = [0, 0.1, 0.25, 0.5, 1]
    for process_count in processes:
        for time_duration in times:
            test.processes = process_count
            test.p = None
            start = time.time()
            for _ in range(SIZE):
                test(time_duration)
            test.wait()
            print process_count, time_duration, time.time() - start