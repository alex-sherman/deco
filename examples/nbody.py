#!/usr/bin/python

from __future__ import print_function
import pygame
import random
import math
import time
from deco import *


iterations = 50


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


@synchronized
def Simulate(body_list, dt):
    next_body_list = {}
    for i in body_list.keys():
        SimulateBody(body_list, next_body_list, i, dt)
    body_list.update(next_body_list)


@concurrent
def SimulateBody(body_list, next_body_list, index, dt):
    simulated_body = body_list[index]
    for _ in range(iterations):
        fx = 0
        fy = 0
        for key in body_list.keys():
            if key == index:
                continue
            body = body_list[key]
            distanceSquared = body.distanceSquared(simulated_body)
            f = body.mass * simulated_body.mass / distanceSquared
            d = distanceSquared ** 0.5
            fx += (body.x - simulated_body.x) / d * f
            fy += (body.y - simulated_body.y) / d * f
        simulated_body.update(fx, fy, dt / iterations)
    next_body_list[index] = simulated_body


if __name__ == "__main__":
    frame_limit = 10
    random.seed(0)

    pygame.init()
    screen_size = 700
    screen = pygame.display.set_mode((screen_size, screen_size))
    points = {}
    point_count = 10
    cs = math.cos(math.pi/3)
    sn = math.sin(math.pi/3)
    key = 0
    for x in range(point_count):
        for y in range(point_count):
            dx = point_count / 2 - x
            dy = point_count / 2 - y
            d_len = math.pow(math.pow(dx, 2) + math.pow(dy, 2), .5)
            if d_len == 0:
                m = 1000
                vx = 0
                vy = 0
            else:
                dx /= d_len
                dy /= d_len
                m = 10000 * random.random()
                vx = (dx * cs - dy * sn) * 30 + (random.random() - .5) / 700
                vy = (dx * sn + dy * cs) * 30 + (random.random() - .5) / 700

            points[key] = Body(
                1.0 * screen_size * x / point_count, 1.0 * screen_size * y / point_count,
                vx, vy, m)
            key += 1

    body_count = len(points)

    i = 0
    start = time.time()
    while True:
        screen.fill((0, 0, 0))
        for point in points.values():
            pygame.draw.circle(
                screen, (128, 128, 128),
                (int(point.x), int(point.y)),
                int(math.pow(point.mass/200, .5)), 0)

        pygame.display.update()
        Simulate(points, .1)
        if i < frame_limit:
            i += 1
            if i == frame_limit:
                print("Time:", time.time() - start)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
