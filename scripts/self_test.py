#!/usr/bin/env python3
"""Local regression tests; no AI calls, network access, or dependency installation."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

from check_pano import VIEWS, check, perspective, rays, sample_equirectangular
from geometry_core import Scene
from verify_review import verify

ROOT = Path(__file__).resolve().parent


def direction_texture(width=512):
    height=width//2
    yaw=2*np.pi*((np.arange(width)+0.5)/width-0.5)
    pitch=np.pi*(0.5-(np.arange(height)+0.5)/height)
    cp=np.cos(pitch)[:,None]
    xyz=np.stack([np.sin(yaw)[None,:]*cp,np.cos(yaw)[None,:]*cp,
                  np.broadcast_to(np.sin(pitch)[:,None],(height,width))],axis=-1)
    return np.rint((xyz+1)*127.5).astype(np.uint8)


class ProjectionTests(unittest.TestCase):
    def test_cardinal_directions(self):
        expected={"front":(0,1,0),"right":(1,0,0),"back-seam":(0,-1,0),
                  "left":(-1,0,0),"zenith":(0,0,1),"nadir":(0,0,-1)}
        for name,yaw,pitch in VIEWS:
            if name in expected:
                np.testing.assert_allclose(rays(1,yaw,pitch)[0,0],expected[name],atol=1e-12)

    def test_texture_reprojection_centers(self):
        image=direction_texture().astype(float)
        for _,yaw,pitch in VIEWS:
            expected=(rays(1,yaw,pitch)[0,0]+1)*127.5
            actual=np.asarray(perspective(image,33,yaw,pitch))[16,16]
            np.testing.assert_allclose(actual,expected,atol=1.1)

    def test_horizontal_wrap_interpolation(self):
        image=np.zeros((4,8,3),float)
        image[:,-1]=200
        direction=np.array([[[0.0,-1.0,0.0]]])
        np.testing.assert_allclose(sample_equirectangular(image,direction)[0,0],100,atol=1e-8)

    def test_roll_inverse_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); original=direction_texture(128)
            Image.fromarray(original).save(p/"in.png")
            for source,target,amount in [("in.png","rolled.png",64),("rolled.png","out.png",-64)]:
                subprocess.run([sys.executable,str(ROOT/"roll_pano.py"),str(p/source),str(p/target),
                                "--columns",str(amount)],check=True,capture_output=True)
            np.testing.assert_array_equal(np.asarray(Image.open(p/"out.png")),original)


class ReviewTests(unittest.TestCase):
    def test_check_does_not_auto_approve(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); Image.fromarray(direction_texture(128)).save(p/"p.png")
            result=check(p/"p.png",p/"check",32)
            self.assertTrue(all(result["automated_file_checks"].values()))
            self.assertEqual(len(result["views"]),len(VIEWS))
            self.assertEqual(json.loads((p/"check/visual-review.json").read_text())["status"],"not_reviewed")
            self.assertTrue(verify(p/"p.png",p/"check/visual-review.json"))

    def test_wrong_aspect_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); Image.new("RGB",(120,80)).save(p/"bad.png")
            result=check(p/"bad.png",p/"check",32)
            self.assertFalse(result["automated_file_checks"]["exact_2_to_1"])
            self.assertEqual(result["views"],[])

    def test_transparency_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); Image.new("RGBA",(128,64),(255,255,255,0)).save(p/"bad.png")
            result=check(p/"bad.png",p/"check",32)
            self.assertFalse(result["automated_file_checks"]["opaque"])

    def test_changed_file_invalidates_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); pixels=direction_texture(128); Image.fromarray(pixels).save(p/"p.png")
            check(p/"p.png",p/"check",32)
            rp=p/"check/visual-review.json"; review=json.loads(rp.read_text())
            review["status"]="passed"; review["reviewer"]="synthetic test record only"
            review["reviewed_views"]=[v[0] for v in VIEWS]
            for item in review["checks"].values():
                item.update(status="pass",evidence="Synthetic fixture, not artwork approval.",views=["front", "nadir", "floor-front"])
            rp.write_text(json.dumps(review))
            self.assertEqual(verify(p/"p.png",rp),[])
            check(p/"p.png",p/"check",32)
            self.assertEqual(json.loads(rp.read_text())["status"],"passed")
            pixels[0,0]=[7,8,9]; Image.fromarray(pixels).save(p/"p.png")
            self.assertTrue(any("SHA-256" in error for error in verify(p/"p.png",rp)))
            check(p/"p.png",p/"check",32)
            self.assertEqual(json.loads(rp.read_text())["status"],"not_reviewed")
            self.assertEqual(len(list((p/"check").glob("visual-review.stale-*.json"))),1)


class GeometryTests(unittest.TestCase):
    def test_multipart_identity(self):
        s=Scene();s.box("table-01",(0,0,0),(1,1,1),(0.5,0.5,0.5))
        s.box("table-01",(1,1,0),(2,2,1),(0.5,0.5,0.5))
        self.assertEqual(len(s.objects),1);self.assertEqual(len(s.triangles),24)

    def test_invalid_geometry(self):
        with self.assertRaises(ValueError):
            Scene().triangle("bad",(0,0,0),(1,1,1),(2,2,2),(1,1,1))
        with self.assertRaises(ValueError):
            Scene().box("bad",(1,1,1),(0,0,0),(1,1,1))
        with self.assertRaises(ValueError):
            Scene().cylinder("bad",(0,0,0),-1,2,(1,1,1))

    def test_cpp_render_axes_cache_and_determinism(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            scene_text='''from geometry_core import Scene

def build_scene():
    s=Scene(camera=(0,0,0),ambient=1)
    s.quad("front",[(-2,2,-2),(2,2,-2),(2,2,2),(-2,2,2)],(1,0,0))
    s.quad("right",[(2,-2,-2),(2,2,-2),(2,2,2),(2,-2,2)],(0,1,0))
    s.quad("back",[(-2,-2,-2),(2,-2,-2),(2,-2,2),(-2,-2,2)],(0,0,1))
    s.quad("left",[(-2,-2,-2),(-2,2,-2),(-2,2,2),(-2,-2,2)],(1,1,0))
    s.quad("zenith",[(-2,-2,2),(2,-2,2),(2,2,2),(-2,2,2)],(1,0,1))
    s.quad("nadir",[(-2,-2,-2),(2,-2,-2),(2,2,-2),(-2,2,-2)],(0,1,1))
    return s
'''
            (p/"scene.py").write_text(scene_text)
            command=[sys.executable,str(ROOT/"render_guide.py"),"--scene",str(p/"scene.py"),
                     "--cache-dir",str(p/"cache"),"--width","128","--samples","4"]
            for i,threads in [(1,1),(2,2)]:
                result=subprocess.run([*command,"--threads",str(threads),"--output-dir",str(p/f"out{i}")],
                                      capture_output=True,text=True,timeout=120)
                self.assertEqual(result.returncode,0,msg=result.stderr)
            a=json.loads((p/"out1/guide-manifest.json").read_text())
            b=json.loads((p/"out2/guide-manifest.json").read_text())
            self.assertTrue(a["compiled_this_run"]);self.assertFalse(b["compiled_this_run"])
            self.assertEqual(a["guide_sha256"],b["guide_sha256"])
            image=np.asarray(Image.open(p/"out1/geometry-guide.png"),dtype=float)
            expected={"front":(255,0,0),"right":(0,255,0),"back-seam":(0,0,255),
                      "left":(255,255,0),"zenith":(255,0,255),"nadir":(0,255,255)}
            for name,yaw,pitch in VIEWS:
                if name in expected:
                    actual=np.asarray(perspective(image,33,yaw,pitch))[16,16]
                    np.testing.assert_allclose(actual,expected[name],atol=1)
            depth=np.load(p/"out1/depth.npy")
            self.assertTrue(np.all(np.isfinite(depth)))
            self.assertGreater(float(depth.min()),1.99)
            self.assertLess(float(depth.max()),3.47)
            ids=np.asarray(Image.open(p/"out1/object-ids.png"))
            unique=np.unique(ids[...,0].astype(int)+256*ids[...,1].astype(int)+65536*ids[...,2].astype(int))
            self.assertEqual(set(unique),{1,2,3,4,5,6})


if __name__=="__main__":
    unittest.main(verbosity=2)
