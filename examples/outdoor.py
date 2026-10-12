"""Terrain and skyline example: no enclosing room or inherited indoor objects."""
import math
from geometry_core import Scene


def build_scene() -> Scene:
    s = Scene(camera=(0, 0, 1.7), ambient=0.45)
    # A flat foreground connects to undulating distant terrain.
    n, step = 24, 5.0
    verts = []
    for j in range(n+1):
        for i in range(n+1):
            x, y = (i-n/2)*step, (j-n/2)*step
            radius = math.hypot(x, y)
            z = max(0.0, radius-15.0) * 0.10 * (1.1 + math.sin(x*0.08)*math.cos(y*0.07))
            verts.append((x, y, z))
    faces = []
    for j in range(n):
        for i in range(n):
            a = j*(n+1)+i
            faces.extend([(a,a+1,a+n+2),(a,a+n+2,a+n+1)])
    s.mesh("terrain", verts, faces, (0.25,0.36,0.17))
    s.box("stone-01", (-3,4,0), (-1.8,5.2,1.4), (0.37,0.39,0.36))
    s.box("stone-02", (4,-4,0), (5.8,-2.5,0.8), (0.40,0.38,0.33))
    return s
