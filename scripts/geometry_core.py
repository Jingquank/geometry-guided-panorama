"""Small triangle-scene API for geometry guides, not a production renderer.

Coordinate convention: +X right, +Y forward, +Z up. Distances are scene units.
Colors are linear RGB values in [0, 1]. All triangles render two-sided.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Sequence

Vec3 = tuple[float, float, float]


def vec3(value: Sequence[float], label: str = "vector") -> Vec3:
    if len(value) != 3:
        raise ValueError(f"{label} must contain three numbers")
    result = tuple(float(x) for x in value)
    if not all(math.isfinite(x) for x in result):
        raise ValueError(f"{label} must be finite")
    return result  # type: ignore[return-value]


def color3(value: Sequence[float]) -> Vec3:
    color = vec3(value, "color")
    if not all(0.0 <= x <= 1.0 for x in color):
        raise ValueError("color must be linear RGB in [0, 1]")
    return color


@dataclass
class Scene:
    camera: Vec3 = (0.0, 0.0, 1.6)
    sky_top: Vec3 = (0.38, 0.58, 0.80)
    sky_horizon: Vec3 = (0.72, 0.76, 0.78)
    sky_bottom: Vec3 = (0.32, 0.34, 0.36)
    sun_direction: Vec3 = (-0.5, -0.7, 1.0)
    ambient: float = 0.38
    triangles: list[tuple] = field(default_factory=list, init=False)
    objects: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.camera = vec3(self.camera, "camera")
        self.sky_top = color3(self.sky_top)
        self.sky_horizon = color3(self.sky_horizon)
        self.sky_bottom = color3(self.sky_bottom)
        self.sun_direction = vec3(self.sun_direction, "sun_direction")
        if sum(x * x for x in self.sun_direction) < 1e-16:
            raise ValueError("sun_direction cannot be zero")
        if not math.isfinite(self.ambient) or not 0 <= self.ambient <= 1:
            raise ValueError("ambient must be in [0, 1]")

    def triangle(self, object_id: str, a: Sequence[float], b: Sequence[float],
                 c: Sequence[float], color: Sequence[float]) -> None:
        if not isinstance(object_id, str) or not object_id.strip():
            raise ValueError("object_id must be a nonempty string")
        av, bv, cv = vec3(a), vec3(b), vec3(c)
        e1 = tuple(bv[i] - av[i] for i in range(3))
        e2 = tuple(cv[i] - av[i] for i in range(3))
        cross = (e1[1] * e2[2] - e1[2] * e2[1],
                 e1[2] * e2[0] - e1[0] * e2[2],
                 e1[0] * e2[1] - e1[1] * e2[0])
        if sum(x * x for x in cross) < 1e-20:
            raise ValueError(f"degenerate triangle in {object_id}")
        rgb = color3(color)
        if object_id not in self.objects:
            if len(self.objects) >= 16777214:
                raise ValueError("too many object IDs for the 24-bit ID map")
            self.objects[object_id] = len(self.objects) + 1
        self.triangles.append((av, bv, cv, rgb, self.objects[object_id]))

    def quad(self, object_id: str, vertices: Sequence[Sequence[float]],
             color: Sequence[float]) -> None:
        """Add a planar, convex quad with vertices in perimeter order."""
        if len(vertices) != 4:
            raise ValueError("quad requires four perimeter-ordered vertices")
        self.triangle(object_id, vertices[0], vertices[1], vertices[2], color)
        self.triangle(object_id, vertices[0], vertices[2], vertices[3], color)

    def box(self, object_id: str, minimum: Sequence[float], maximum: Sequence[float],
            color: Sequence[float]) -> None:
        lo, hi = vec3(minimum), vec3(maximum)
        if any(lo[i] >= hi[i] for i in range(3)):
            raise ValueError("box minimum must be below maximum on all axes")
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        vertices = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                    (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        for indices in [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
                        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]:
            self.quad(object_id, [vertices[i] for i in indices], color)

    def mesh(self, object_id: str, vertices: Sequence[Sequence[float]],
             faces: Iterable[Sequence[int]], color: Sequence[float]) -> None:
        """Add triangles or convex planar quads; triangulate other polygons first."""
        for face in faces:
            if len(face) not in (3, 4):
                raise ValueError("mesh faces must have three or four indices")
            if any(not isinstance(i, int) or i < 0 or i >= len(vertices) for i in face):
                raise ValueError("mesh face index out of range")
            points = [vertices[i] for i in face]
            if len(face) == 3:
                self.triangle(object_id, *points, color)
            else:
                self.quad(object_id, points, color)

    def cylinder(self, object_id: str, base: Sequence[float], radius: float,
                 height: float, color: Sequence[float], segments: int = 32,
                 capped: bool = True) -> None:
        """Vertical faceted cylinder; use a mesh for arches or curved wall openings."""
        x, y, z = vec3(base)
        if not (math.isfinite(radius) and math.isfinite(height) and radius > 0 and height > 0):
            raise ValueError("cylinder radius and height must be finite and positive")
        if not isinstance(segments, int) or not 3 <= segments <= 4096:
            raise ValueError("segments must be an integer from 3 to 4096")
        ring = [(x + radius * math.cos(2 * math.pi * i / segments),
                 y + radius * math.sin(2 * math.pi * i / segments), z)
                for i in range(segments)]
        for i in range(segments):
            a, b = ring[i], ring[(i + 1) % segments]
            at, bt = (a[0], a[1], z + height), (b[0], b[1], z + height)
            self.quad(object_id, [a, b, bt, at], color)
            if capped:
                self.triangle(object_id, (x, y, z), b, a, color)
                self.triangle(object_id, (x, y, z + height), at, bt, color)

    def checker_floor(self, object_id: str, minimum_xy: Sequence[float],
                      maximum_xy: Sequence[float], z: float = 0.0,
                      cell: Sequence[float] = (0.65, 0.65),
                      origin: Sequence[float] = (0.0, 0.0),
                      rotation_degrees: float = 0.0,
                      colors: Sequence[Sequence[float]] = ((0.75,0.65,0.50),(0.04,0.07,0.05))) -> None:
        """Planar checker tiles clipped to a world-axis-aligned rectangle.

        Tile seams share one Cartesian phase; rotation is world +X toward +Y.
        Colors are linear RGB. No polar texture coordinates and no physical grout.
        Do not overlap a second coplanar ground quad beneath these triangles.
        """
        def pair(value, label):
            if len(value) != 2 or not all(math.isfinite(float(x)) for x in value):
                raise ValueError(f"{label} requires two finite values")
            return tuple(float(x) for x in value)
        lo, hi = pair(minimum_xy,"minimum_xy"), pair(maximum_xy,"maximum_xy")
        step, offset = pair(cell,"cell"), pair(origin,"origin")
        if any(lo[i] >= hi[i] for i in range(2)) or min(step) <= 0:
            raise ValueError("Invalid floor bounds or cell dimensions")
        if not math.isfinite(z) or not math.isfinite(rotation_degrees) or len(colors) != 2:
            raise ValueError("Invalid floor elevation, angle, or colors")
        colors = [color3(c) for c in colors]
        angle = math.radians(rotation_degrees)
        c, sn = math.cos(angle), math.sin(angle)
        def local(x,y):
            x,y=x-offset[0],y-offset[1]
            return ((c*x+sn*y)/step[0],(-sn*x+c*y)/step[1])
        def world(u,v):
            u,v=u*step[0],v*step[1]
            return (offset[0]+c*u-sn*v,offset[1]+sn*u+c*v)
        corners=[local(x,y) for x in (lo[0],hi[0]) for y in (lo[1],hi[1])]
        u0,u1=math.floor(min(x[0] for x in corners)),math.ceil(max(x[0] for x in corners))
        v0,v1=math.floor(min(x[1] for x in corners)),math.ceil(max(x[1] for x in corners))
        if (u1-u0)*(v1-v0)>100000:
            raise ValueError("Too many floor cells; use a texture-mapped renderer")
        def clip(poly,axis,bound,greater):
            if not poly: return []
            out=[]
            a=poly[-1]
            ain=a[axis]>=bound if greater else a[axis]<=bound
            for b in poly:
                bin_=b[axis]>=bound if greater else b[axis]<=bound
                if ain!=bin_:
                    t=(bound-a[axis])/(b[axis]-a[axis])
                    out.append(tuple(a[k]+t*(b[k]-a[k]) for k in range(2)))
                if bin_: out.append(b)
                a,ain=b,bin_
            return out
        for i in range(u0,u1):
            for j in range(v0,v1):
                poly=[world(i,j),world(i+1,j),world(i+1,j+1),world(i,j+1)]
                for axis in range(2):
                    poly=clip(poly,axis,lo[axis],True)
                    poly=clip(poly,axis,hi[axis],False)
                for k in range(1,len(poly)-1):
                    a,b,d=poly[0],poly[k],poly[k+1]
                    area=(b[0]-a[0])*(d[1]-a[1])-(b[1]-a[1])*(d[0]-a[0])
                    if abs(area)>1e-9:
                        self.triangle(object_id,(*a,z),(*b,z),(*d,z),colors[(i+j)%2])
