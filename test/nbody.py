#!/usr/bin/python

import pygame
import random
import math
import sys, time
from simulate import *

if __name__ == "__main__":
    random.seed(0)

    pygame.init()
    screen_size = 700
    screen = pygame.display.set_mode((screen_size, screen_size))
    #points = [[0,0,1], [0,1,1], [1,0,1], [1,1,1]]
    points = []
    point_count = 20
    cs = math.cos(math.pi/3)
    sn = math.sin(math.pi/3)
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

            points.append(Body(1.0 * screen_size * x / point_count, 1.0 * screen_size * y / point_count,
                vx, vy,
                m))

    body_count = len(points)

    while True:
        screen.fill((0,0,0))
        for point in points:
            pygame.draw.circle(screen, (128,128,128), (int(point.x), int(point.y)), int(math.pow(point.mass/200, .5)), 0)

        pygame.display.update()
        start = time.time()
        Simulate(points, .1, 5)
        #exit()
        end = time.time()
        print end - start
        #time.sleep(1)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()