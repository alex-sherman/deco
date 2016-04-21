#!/usr/bin/python

import pygame
import random
import math
import sys, time
from simulate import *

if __name__ == "__main__":
    frame_limit = 10
    random.seed(0)

    pygame.init()
    screen_size = 700
    screen = pygame.display.set_mode((screen_size, screen_size))
    #points = [[0,0,1], [0,1,1], [1,0,1], [1,1,1]]
    points = {}
    point_count = 10
    cs = math.cos(math.pi/3)
    sn = math.sin(math.pi/3)
    key = 0
    for x in range(point_count):
        for y in range(point_count):
            dx = point_count / 2 - x
            dy = point_count / 2 - y
            d_len = math.pow(math.pow(dx,2) + math.pow(dy,2),.5)
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

            points[key] = Body(1.0 * screen_size * x / point_count, 1.0 * screen_size * y / point_count,
                vx, vy,
                m)
            key += 1

    body_count = len(points)

    i = 0
    start = time.time()
    while True:
        screen.fill((0,0,0))
        for point in points.values():
            pygame.draw.circle(screen, (128,128,128), (int(point.x), int(point.y)), int(math.pow(point.mass/200, .5)), 0)

        pygame.display.update()
        if i < frame_limit:
            Simulate(points, .1, 50)
            i += 1
            if i == frame_limit:
                print "Time:", time.time() - start

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()