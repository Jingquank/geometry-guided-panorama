#!/usr/bin/env python3
"""Regression tests for the floor-lock revision. No image-model calls or network."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image
from check_pano import VIEWS, REVIEW_VERSION, check, digest, rays, perspective
from geometry_core import Scene
from planar_floor import world_uv, albedo, render, periodic_sample, composite, mask_review_errors
from verify_review import verify
from release_check import verify_pipeline
from execution_guard import report_for

ROOT=Path(__file__).resolve().parent
SPEC={"camera":[0.17,-0.11,1.6],"floor_z":0.0,"origin_xy":[0,0],
      "period_xy":[0.65,0.65],"rotation_degrees":23,
      "colors_srgb":[[224,208,188],[56,75,63]]}


def passed_fixture(image:Path, directory:Path, scene_spec=None):
    check(image,directory,32,scene_spec=scene_spec)
    rp=directory/"visual-review.json"
    data=json.loads(rp.read_text())
    data.update(status="passed",reviewer="SYNTHETIC TEST FIXTURE; NOT ARTWORK APPROVAL",
                reviewed_views=[v[0] for v in VIEWS])
    for item in data["checks"].values():
        item.update(status="pass",evidence="Synthetic record for validator regression only.",
                    views=["nadir","floor-front"])
    rp.write_text(json.dumps(data))
    return rp


class FloorProjectionTests(unittest.TestCase):
    def test_ray_plane_intersections(self):
        spec={**SPEC,"camera":[0,0,2],"period_xy":[1,1],"rotation_degrees":0}
        uv=world_uv(np.array([[0,0,-1],[1,2,-1],[0,1,0],[0,0,1]],float),spec)
        np.testing.assert_allclose(uv[0][:2],[0,2])
        np.testing.assert_allclose(uv[1][:2],[0,4])
        np.testing.assert_array_equal(uv[2],[True,True,False,False])

    def test_nadir_material_coordinates_are_affine(self):
        u,v,visible=world_uv(rays(101,0,-90),SPEC)
        self.assertTrue(np.all(visible))
        # An orthogonal view of a plane has affine UV, not radial coordinates.
        for coord in (u,v):
            np.testing.assert_allclose(np.diff(coord,n=2,axis=0),0,atol=1e-12)
            np.testing.assert_allclose(np.diff(coord,n=2,axis=1),0,atol=1e-12)

    def test_roundtrip_planar_checker_matches_direct_perspective(self):
        img,_=render(1536,SPEC,2)
        actual=np.asarray(perspective(img,128,0,-90),float)
        expected,_=albedo(rays(128,0,-90),SPEC)
        # Ignore exact material discontinuities: bilinear reprojection antialiases them.
        u,v,_=world_uv(rays(128,0,-90),SPEC)
        away=(np.minimum(u%1,1-u%1)>0.035)&(np.minimum(v%1,1-v%1)>0.035)
        self.assertGreater(np.mean(away),0.7)
        self.assertLess(np.mean(np.abs(actual[away]-expected[away])),0.6)

    def test_texture_wraps_on_both_axes(self):
        tex=np.arange(4*6*3,dtype=float).reshape(4,6,3)
        u=np.array([0,.3,.999,-.2]);v=np.array([0,.8,-.02,1.01])
        np.testing.assert_allclose(periodic_sample(tex,u,v),periodic_sample(tex,u+3,v-2),atol=1e-10)

    def test_invalid_floor_spec_and_render_dimensions(self):
        for spec in ({**SPEC,"period_xy":[0,1]},{**SPEC,"camera":[0,0,0]},
                     {**SPEC,"rotation_degrees":float('nan')}):
            with self.assertRaises(ValueError): render(64,spec)
        with self.assertRaises(ValueError): render(65,SPEC)

    def test_checker_geometry_clips_and_has_single_identity(self):
        s=Scene()
        s.checker_floor("floor",(-1.3,-1.1),(1.8,2.2),cell=(.47,.62),rotation_degrees=31,
                        origin=(.18,-.13))
        self.assertEqual(len(s.objects),1)
        area=0
        for a,b,c,_,_ in s.triangles:
            a,b,c=map(np.asarray,(a,b,c))
            area+=np.linalg.norm(np.cross(b-a,c-a))/2
            for point in (a,b,c):
                self.assertGreaterEqual(point[0],-1.3-1e-10)
                self.assertLessEqual(point[0],1.8+1e-10)
                self.assertGreaterEqual(point[1],-1.1-1e-10)
                self.assertLessEqual(point[1],2.2+1e-10)
        self.assertAlmostEqual(area,3.1*3.3,places=8)


class MaskTests(unittest.TestCase):
    def test_composite_protects_zero_mask_pixels(self):
        base=np.arange(8*16*3,dtype=np.uint16).reshape(8,16,3)%256
        floor,coverage=render(32,SPEC,1)
        base=np.tile(base,(2,2,1)).astype(np.float32)
        mask=np.zeros((16,32),float);mask[12:,4:28]=1
        out=composite(base,floor,mask,coverage)
        np.testing.assert_array_equal(out[mask==0],base[mask==0])
        np.testing.assert_array_equal(out[mask==1],np.rint(floor[mask==1]))

    def test_invalid_mask_rejected(self):
        floor,coverage=render(32,SPEC,1)
        with self.assertRaises(ValueError): composite(floor,floor,np.zeros((16,32)),coverage)
        with self.assertRaises(ValueError): composite(floor,floor,np.ones((16,32)),coverage)
        with self.assertRaises(ValueError): composite(floor,floor,np.ones((2,2)),coverage)

    def test_mask_review_hash_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            for name in ('base','mask','spec'): (p/name).write_text(name)
            data={"status":"passed","reviewer":"synthetic","evidence":"test only",
                  "camera_and_layout_aligned":True,"occlusions_and_contacts_checked":True,
                  "candidate_sha256":digest(p/'base'),"mask_sha256":digest(p/'mask'),
                  "floor_spec_sha256":digest(p/'spec')}
            (p/'review').write_text(json.dumps(data))
            self.assertEqual(mask_review_errors(p/'base',p/'mask',p/'spec',p/'review'),[])
            (p/'mask').write_text('changed')
            self.assertTrue(mask_review_errors(p/'base',p/'mask',p/'spec',p/'review'))

    def test_cli_guarded_composite_and_missing_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'spec.json').write_text(json.dumps(SPEC))
            Image.new('RGB',(64,32),(20,30,40)).save(p/'base.png')
            mask=np.zeros((32,64),np.uint8);mask[23:30,10:50]=255
            Image.fromarray(mask).save(p/'mask.png')
            cmd=[sys.executable,str(ROOT/'planar_floor.py'),'--spec',str(p/'spec.json'),
                 '--base',str(p/'base.png'),'--mask',str(p/'mask.png'),'--output',str(p/'out.png')]
            bad=subprocess.run(cmd,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0)
            record={"status":"passed","reviewer":"synthetic","evidence":"test only",
                    "camera_and_layout_aligned":True,"occlusions_and_contacts_checked":True,
                    "candidate_sha256":digest(p/'base.png'),"mask_sha256":digest(p/'mask.png'),
                    "floor_spec_sha256":digest(p/'spec.json')}
            (p/'review.json').write_text(json.dumps(record))
            good=subprocess.run(cmd+['--mask-review',str(p/'review.json')],capture_output=True,text=True)
            self.assertEqual(good.returncode,0,msg=good.stderr)
            out=np.asarray(Image.open(p/'out.png'));base=np.asarray(Image.open(p/'base.png'))
            np.testing.assert_array_equal(out[mask==0],base[mask==0])


class GateTests(unittest.TestCase):
    def test_old_review_schema_invalidated_even_same_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);Image.new('RGB',(64,32)).save(p/'image.png')
            rp=passed_fixture(p/'image.png',p/'check')
            data=json.loads(rp.read_text());data.pop('review_version');rp.write_text(json.dumps(data))
            self.assertTrue(verify(p/'image.png',rp))
            check(p/'image.png',p/'check',32)
            self.assertEqual(json.loads(rp.read_text())['status'],'not_reviewed')

    def test_surface_evidence_requires_downward_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);Image.new('RGB',(64,32)).save(p/'image.png')
            rp=passed_fixture(p/'image.png',p/'check')
            data=json.loads(rp.read_text());data['checks']['surface_pattern']['views']=['front']
            rp.write_text(json.dumps(data))
            self.assertTrue(any('Surface-pattern' in s for s in verify(p/'image.png',rp)))

    def test_release_rejects_direct_generation_interior(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'spec').write_text(json.dumps({'route':'direct_simple','scene_type':'interior'}))
            state={'status':'ready_for_review','scene_spec':{'path':'spec','sha256':digest(p/'spec')}}
            (p/'pipeline').write_text(json.dumps(state))
            errors=verify_pipeline(p/'pipeline')
            self.assertTrue(any('Direct generation' in s for s in errors))
            self.assertTrue(any('candidate' in s for s in errors))

    def test_complete_release_fixture_and_changed_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);Image.new('RGB',(64,32)).save(p/'candidate.png')
            Image.new('RGB',(64,32),(50,60,70)).save(p/'guide.png')
            cr=passed_fixture(p/'candidate.png',p/'final-check')
            gr=passed_fixture(p/'guide.png',p/'guide-check')
            (p/'spec.json').write_text(json.dumps({'route':'geometry_guided','scene_type':'interior',
                                                 'surface_constraints':[{'id':'floor','pattern':'none'}]}))
            spec=json.loads((p/'spec.json').read_text())
            spec['inspection_plan']={'version':1,'targets':[],'no_targets_reason':'Synthetic uniform record fixture only.'}
            (p/'spec.json').write_text(json.dumps(spec))
            cr=passed_fixture(p/'candidate.png',p/'final-check',p/'spec.json')
            gr=passed_fixture(p/'guide.png',p/'guide-check',p/'spec.json')
            (p/'scene.py').write_text('# Synthetic file for release-record testing only\n')
            (p/'request.json').write_text(json.dumps({'authored_prompt':'synthetic fixture',
                'structural_base_sha256':digest(p/'guide.png'),'actual_input_references':['test guide']}))
            state={'status':'ready_for_review', 'pipeline_version':3,
                   'capabilities':{'local_processing':True,'output_bytes_accessible':True,
                                   'post_generation_processing':True},
                   'planned_final_operation':'image_generation'}
            for key,path in [('candidate',p/'candidate.png'),('candidate_review',cr),
                             ('structural_base',p/'guide.png'),('structural_base_review',gr),
                             ('scene_spec',p/'spec.json'),('scene_source',p/'scene.py'),
                             ('generation_request',p/'request.json')]:
                state[key]={'path':str(path),'sha256':digest(path)}
            (p/'pipeline.json').write_text(json.dumps(state))
            (p/'preflight.json').write_text(json.dumps(report_for(p/'pipeline.json')))
            state['preflight_report']={'path':str(p/'preflight.json'),'sha256':digest(p/'preflight.json')}
            (p/'pipeline.json').write_text(json.dumps(state))
            self.assertEqual(verify_pipeline(p/'pipeline.json'),[])
            (p/'scene.py').write_text('# Changed')
            self.assertTrue(any('changed artifact' in s.lower() for s in verify_pipeline(p/'pipeline.json')))


if __name__=='__main__': unittest.main(verbosity=2)
