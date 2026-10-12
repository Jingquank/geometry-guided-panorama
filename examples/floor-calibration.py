"""Calibration fixture, not a reconstruction of the user's lobby or a scene preset."""
from geometry_core import Scene


def build_scene():
    s=Scene(camera=(0.17,-0.11,1.6),ambient=1.0)
    s.checker_floor("floor",(-6,-6),(6,6),cell=(0.65,0.65),
                    origin=(0,0),rotation_degrees=23,
                    colors=((0.75,0.65,0.50),(0.04,0.07,0.05)))
    s.quad("front",[(-6,6,0),(6,6,0),(6,6,4),(-6,6,4)],(0.55,0.25,0.17))
    s.quad("back",[(-6,-6,0),(6,-6,0),(6,-6,4),(-6,-6,4)],(0.15,0.24,0.42))
    s.quad("left",[(-6,-6,0),(-6,6,0),(-6,6,4),(-6,-6,4)],(0.16,0.38,0.27))
    s.quad("right",[(6,-6,0),(6,6,0),(6,6,4),(6,-6,4)],(0.5,0.38,0.13))
    s.quad("ceiling",[(-6,-6,4),(6,-6,4),(6,6,4),(-6,6,4)],(0.65,0.61,0.54))
    return s
