from deco import concurrent

class Body(object):
    def __init__(self, x, y, vx, vy, mass):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mass = mass
    def update(self, fx, fy, dt):
        self.vx += fx / self.mass * dt
        self.vy += fy / self.mass * dt
        self.x += self.vx * dt
        self.y += self.vy * dt
    def distanceSquared(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

@concurrent(3)
def SimulateBody(body_list, next_body_list, index, iterations, dt):
    simulated_body = body_list[index]
    for _ in range(iterations):
        fx = 0
        fy = 0
        for key in body_list.keys():
            if key == index: continue
            body = body_list[key]
            distanceSquared = body.distanceSquared(simulated_body)
            f = body.mass * simulated_body.mass / distanceSquared
            d = distanceSquared ** 0.5
            fx += (body.x - simulated_body.x) / d * f
            fy += (body.y - simulated_body.y) / d * f
        simulated_body.update(fx, fy, dt / iterations)
    next_body_list[index] = simulated_body

def Simulate(body_list, dt, iterations):
    next_body_list = {}
    for i in body_list.keys():
        SimulateBody(body_list, next_body_list, i, iterations, dt)
    SimulateBody.wait()
    body_list.update(next_body_list)