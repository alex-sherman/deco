from deco import concurrent

BODIES = [90]


def run():
    BODIES.append(210)
    simulate()
    simulate.wait()


@concurrent
def simulate():
    print BODIES

if __name__ == "__main__":
    run()
