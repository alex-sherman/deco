from conc import concurrent

class Body(object):
    def __init__(self, x, y, vx, vy, mass):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.mass = mass
    def distanceSquared(self, other):
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
#@concurrent
def SimulateBody(body_list, index, iterations, dt):
    simulated_body = body_list[index]
    for _ in range(iterations):
        fx = 0
        fy = 0
        for i, body in enumerate(body_list):
            if i == index: continue
            distanceSquared = body.distanceSquared(simulated_body)
            f = body.mass * simulated_body.mass / distanceSquared
            d = distanceSquared ** 0.5
            fx += (body.x - simulated_body.x) / d * f
            fy += (body.y - simulated_body.y) / d * f
        simulated_body.vx += fx / simulated_body.mass * dt / iterations
        simulated_body.vy += fy / simulated_body.mass * dt / iterations
        simulated_body.x += simulated_body.vx * dt / iterations
        simulated_body.y += simulated_body.vy * dt / iterations
    body_list[index] = simulated_body

def Simulate(body_list, dt, iterations):
    for i in range(len(body_list)):
        SimulateBody(body_list, i, iterations, dt)
    #SimulateBody.wait()