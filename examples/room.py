"""API example only. Rebuild the layout for the user's actual scene."""
from geometry_core import Scene


def build_scene() -> Scene:
    s = Scene(camera=(0, -0.7, 1.55))
    wall, floor = (0.73, 0.70, 0.64), (0.39, 0.27, 0.17)
    s.quad("floor", [(-3,-3,0),(3,-3,0),(3,3,0),(-3,3,0)], floor)
    s.quad("ceiling", [(-3,-3,3.2),(-3,3,3.2),(3,3,3.2),(3,-3,3.2)], (0.85,0.85,0.82))
    s.quad("left-wall", [(-3,-3,0),(-3,3,0),(-3,3,3.2),(-3,-3,3.2)], wall)
    s.quad("right-wall", [(3,-3,0),(3,3,0),(3,3,3.2),(3,-3,3.2)], wall)
    s.quad("back-wall", [(-3,-3,0),(3,-3,0),(3,-3,3.2),(-3,-3,3.2)], wall)
    # The front wall has one real doorway, assembled from three wall panels.
    s.quad("front-wall", [(-3,3,0),(-0.6,3,0),(-0.6,3,3.2),(-3,3,3.2)], wall)
    s.quad("front-wall", [(0.6,3,0),(3,3,0),(3,3,3.2),(0.6,3,3.2)], wall)
    s.quad("front-wall", [(-0.6,3,2.3),(0.6,3,2.3),(0.6,3,3.2),(-0.6,3,3.2)], wall)
    s.quad("doorway-floor", [(-0.6,3,0),(0.6,3,0),(0.6,4.2,0),(-0.6,4.2,0)], floor)
    s.quad("doorway-recess", [(-0.6,4.2,0),(0.6,4.2,0),(0.6,4.2,2.3),(-0.6,4.2,2.3)], (0.20,0.24,0.28))
    # All five components below share one table identity.
    s.box("table-01", (-1.3,0.6,0.76), (0.8,1.6,0.88), (0.40,0.22,0.11))
    for x in (-1.2,0.6):
        for y in (0.7,1.4):
            s.box("table-01", (x,y,0), (x+0.13,y+0.13,0.76), (0.25,0.15,0.08))
    s.cylinder("pedestal-01", (2.1,1.6,0), 0.33, 1.0, (0.65,0.64,0.61), segments=32)
    return s
