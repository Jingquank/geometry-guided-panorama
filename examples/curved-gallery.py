"""Curved-wall example. Preserve intended curvature; do not 'correct' it into a box."""
import math
from geometry_core import Scene


def build_scene() -> Scene:
    s = Scene(camera=(0,-1.1,1.6), ambient=0.55)
    segments, radius, height = 96, 5, 3.4
    ring = [(radius*math.cos(i*2*math.pi/segments), radius*math.sin(i*2*math.pi/segments), 0)
            for i in range(segments)]
    for i in range(segments):
        a, b = ring[i], ring[(i+1)%segments]
        s.triangle("floor", (0,0,0), a, b, (0.43,0.42,0.39))
        s.triangle("ceiling", (0,0,height), (b[0],b[1],height), (a[0],a[1],height), (0.78,0.76,0.72))
        s.quad("curved-wall", [a,b,(b[0],b[1],height),(a[0],a[1],height)], (0.62,0.55,0.45))
    s.cylinder("column-01", (1.7,1.8,0), 0.32, height, (0.80,0.77,0.69), segments=32)
    s.cylinder("plinth-01", (-1.8,1.9,0), 0.6, 0.7, (0.46,0.47,0.48), segments=48)
    return s
