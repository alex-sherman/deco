Decorated Concurrency
===========

A simplified parallel computing model for Python.
DECO automatically parallelizes Python programs, and requires minimal modifications to existing serial programs.

Install using pip:

```
pip install deco
```

General Usage
---------------

Using DECO is as simple as finding, or creating, two functions in your Python program.
The first function is the one we want to run in parallel, and is decorated with `@concurrent`.
The second function is the function which calls the `@concurrent` function and is decorated with `@synchronized`.
Decorating the second function is optional, but provides some very cool benefits.
Let's take a look at an example.


```python
@concurrent # We add this for the concurrent function
def process_lat_lon(lat, lon, data):
  #Does some work which takes a while
  return result

@synchronized # And we add this for the function which calls the concurrent function
def process_data_set(data):
  results = defaultdict(dict)
  for lat in range(...):
    for lon in range(...):
      results[lat][lon] = process_lat_lon(lat, lon, data)
  return results
```

That's it, two lines of changes is all we need in order to parallelize this program.
Now this program will make use of all the cores on the machine it's running on, allowing it to run significantly faster.

What it does
-------------

  - The `@concurrent` decorator uses multiprocessing.pool to parallelize calls to the target function
  - Indexed based mutation of function arguments is handled automatically, which pool cannot do
  - The `@synchronized` decorator automatically inserts synchronization events 
  - It also automatically refactors assignments of the results of `@concurrent` function calls to happen during synchronization events

Limitations
-------------
  - The `@concurrent` decorator will only speed up functions that take longer than ~1ms
    - If they take less time your code will run slower!
  - The `@synchronized` decorator only works on 'simple' functions, make sure the function meets the following criteria
    - Only calls, or assigns the result of `@concurrent` functions to indexable objects such as:
      - concurrent(...)
      - result[key] = concurrent(...)
    - Never indirectly reads objects that get assigned to by calls of the `@concurrent` function

How it works
-------------

For an in depth discussion of the mechanisms at work, we wrote a paper for a class
which [can be found here](https://drive.google.com/file/d/0B_olmC0u8E3gWTBmN3pydGxHdEE/view).

As an overview, DECO is mainly just a smart wrapper for Python's multiprocessing.pool.
When `@concurrent` is applied to a function it replaces it with calls to pool.apply_async.
Additionally when arguments are passed to pool.apply_async, DECO replaces any index mutable objects with proxies, allowing it to detect and synchronize mutations of these objects.
The results of these calls can then be obtained by calling wait() on the concurrent function, invoking a synchronization event.
These events can be placed automatically in your code by using the `@synchronized` decorator on functions that call `@concurrent` functions.
Additionally while using `@synchronized`, you can directly assign the result of concurrent function calls to index mutable objects.
These assignments get refactored by DECO to automatically occur during the next synchronization event.
All of this means that in many cases, parallel programming using DECO appears exactly the same as simpler serial programming.


