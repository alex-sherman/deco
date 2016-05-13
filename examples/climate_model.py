from deco import *
import time
import random
from collections import defaultdict


@concurrent  # We add this for the concurrent function
def process_lat_lon(lat, lon, data):
    time.sleep(0.1)
    return data[lat + lon]


@synchronized  # And we add this for the function which calls the concurrent function
def process_data_set(data):
    results = defaultdict(dict)
    for lat in range(5):
        for lon in range(5):
            results[lat][lon] = process_lat_lon(lat, lon, data)
    return dict(results)

if __name__ == "__main__":
    random.seed(0)
    data = [random.random() for _ in range(200)]
    start = time.time()
    print(process_data_set(data))
    print(time.time() - start)
