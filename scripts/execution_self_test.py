#!/usr/bin/env python3
"""Synthetic regressions for v3 guards and last-pixel composition; not art approval."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from check_pano import VIEWS, digest
from execution_guard import binding, read_object, preflight, report_for, patterned_ids
from surface_finish import build, verify_finish, compose, validate_mask
from floor_self_test import passed_fixture
from release_check import verify_pipeline


def write(path, obj):
    path.write_text(json.dumps(obj, indent=2))


def fixture(root: Path, *, mode="masked_surface_finish"):
    spec={"route":"geometry_guided","scene_type":"interior","surface_constraints":[{
        "id":"floor","geometry":"horizontal_plane","pattern":"cartesian_checkerboard",
        "finish_route":"world_space_surface"}]}
    spec['inspection_plan']={'version':1,'targets':[],'no_targets_reason':'Synthetic validator fixture, not artwork.'}
    write(root/'scene-spec.json',spec)
    (root/'scene.py').write_text('# SYNTHETIC UNIT TEST INPUT, NOT EXECUTED SCENE\n')
    base=np.full((32,64,3),[22,40,80],np.uint8)
    yy,xx=np.indices((32,64))
    surf=np.where(((xx//8+yy//8)%2)[...,None],np.array([55,82,64]),np.array([223,210,181])).astype(np.uint8)
    mask=np.zeros((32,64),np.uint8);mask[18:30,4:60]=255
    Image.fromarray(base).save(root/'base.png')
    Image.fromarray(surf).save(root/'surface.png')
    Image.fromarray(mask).save(root/'mask.png')
    gr=passed_fixture(root/'base.png',root/'guide-check',root/'scene-spec.json')
    protected=['nadir']+[v[0] for v in VIEWS if v[0].startswith('floor-')]
    review={"status":"passed","reviewer":"SYNTHETIC TEST FIXTURE ONLY",
        "evidence":"Synthetic record; neither floor nor artwork is visually approved.",
        "scene_spec_sha256":digest(root/'scene-spec.json'),
        "surface_render_sha256":digest(root/'surface.png'),
        "protected_surface_ids":["floor"],"render_role":"final_world_space_surface",
        "camera_and_projection_matched":True,"material_and_pattern_checked":True,
        "reviewed_views":protected}
    write(root/'surface-review.json',review)
    mr={"status":"passed","reviewer":"SYNTHETIC TEST FIXTURE ONLY","evidence":"No art approval.",
        "base_sha256":digest(root/'base.png'),"mask_sha256":digest(root/'mask.png'),
        "surface_render_sha256":digest(root/'surface.png'),"scene_spec_sha256":digest(root/'scene-spec.json'),
        "camera_and_layout_aligned":True,"occlusions_and_contacts_checked":True,
        "full_surface_coverage_checked":True,"boundary_blend_checked":True}
    write(root/'mask-review.json',mr)
    write(root/'render-record.json',{"output_sha256":digest(root/'surface.png'),
        "scene_spec_sha256":digest(root/'scene-spec.json'),"mapping":"world_space",
        "renderer":"SYNTHETIC TEST FIXTURE - NOT AN ACTUAL RENDER",
        "render_settings":{"fixture":True}})
    req={"finish_request_version":1,"mode":mode}
    for key,name in (("scene_spec","scene-spec.json"),("surface_render","surface.png"),
        ("surface_review","surface-review.json"),("render_provenance","render-record.json"),
        ("base","base.png"),("mask","mask.png"),("mask_review","mask-review.json")):
        req[key]=binding(root/name)
    write(root/'finish.json',req)
    state={"pipeline_version":3,"status":"preparing",
        "capabilities":{"local_processing":True,"output_bytes_accessible":True,"post_generation_processing":True},
        "planned_final_operation":mode}
    for key,path in (("scene_spec",root/'scene-spec.json'),("scene_source",root/'scene.py'),
        ("structural_base",root/'base.png'),("structural_base_review",gr)):
        state[key]=binding(path)
    write(root/'pipeline.json',state)
    write(root/'preflight.json',report_for(root/'pipeline.json'))
    state['preflight_report']=binding(root/'preflight.json')
    write(root/'pipeline.json',state)
    return state,req


def complete(root):
    state,req=fixture(root)
    manifest=build(root/'finish.json',root/'out.png')
    cr=passed_fixture(root/'out.png',root/'final-check',root/'scene-spec.json')
    write(root/'request.json',{"authored_prompt":"SYNTHETIC TEST FIXTURE ONLY",
        "actual_input_references":["fixture"],"structural_base_sha256":digest(root/'base.png')})
    state.update(status='ready_for_review',candidate=binding(root/'out.png'),candidate_review=binding(cr),
        generation_request=binding(root/'request.json'),surface_finish=binding(manifest))
    write(root/'pipeline.json',state)
    return state,manifest


class ExecutionGuardTests(unittest.TestCase):
    def test_pattern_assessment_must_be_structured(self):
        for x in (None,[],"checker",[{}],[{"id":"floor","pattern":""}]):
            with self.assertRaises(ValueError): patterned_ids({"surface_constraints":x})
    def test_preflight_accepts_complete_synthetic_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);fixture(p)
            self.assertEqual(preflight(p/'pipeline.json'),[])
    def test_preflight_rejects_terminal_host(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=fixture(p);state['capabilities']['post_generation_processing']=False
            write(p/'pipeline.json',state)
            self.assertTrue(any('post_generation_processing' in s for s in preflight(p/'pipeline.json')))
    def test_preflight_rejects_image_generation_last(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=fixture(p);state['planned_final_operation']='image_generation'
            write(p/'pipeline.json',state)
            self.assertTrue(any('end with' in s for s in preflight(p/'pipeline.json')))
    def test_preflight_rejects_missing_guide(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);fixture(p);(p/'base.png').unlink()
            self.assertTrue(preflight(p/'pipeline.json'))
    def test_preflight_rejects_prefer_only_surface_route(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=fixture(p);spec=read_object(p/'scene-spec.json')
            spec['surface_constraints'][0]['finish_route']='guide_conditioned'
            write(p/'scene-spec.json',spec);state['scene_spec']=binding(p/'scene-spec.json');write(p/'pipeline.json',state)
            self.assertTrue(any('required, not preferred' in s for s in preflight(p/'pipeline.json')))


class FinalPixelTests(unittest.TestCase):
    def test_masked_finalizer_preserves_both_regions(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);fixture(p);mf=build(p/'finish.json',p/'out.png')
            out=np.asarray(Image.open(p/'out.png'));m=np.asarray(Image.open(p/'mask.png'))
            np.testing.assert_array_equal(out[m==0],np.asarray(Image.open(p/'base.png'))[m==0])
            np.testing.assert_array_equal(out[m==255],np.asarray(Image.open(p/'surface.png'))[m==255])
            self.assertEqual(verify_finish(mf,p/'out.png',p/'scene-spec.json'),[])
    def test_rendered_panorama_finalizer(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);fixture(p,mode='rendered_panorama');mf=build(p/'finish.json',p/'out.png')
            np.testing.assert_array_equal(np.asarray(Image.open(p/'out.png')),np.asarray(Image.open(p/'surface.png')))
            self.assertEqual(verify_finish(mf,p/'out.png',p/'scene-spec.json'),[])
    def test_pixel_edit_detected_even_when_output_hash_refreshed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);fixture(p);mf=build(p/'finish.json',p/'out.png')
            a=np.array(Image.open(p/'out.png'));a[25,25]=[1,2,3];Image.fromarray(a).save(p/'out.png')
            m=read_object(mf);m['output']=binding(p/'out.png');write(mf,m)
            self.assertTrue(any('recomputed' in s for s in verify_finish(mf,p/'out.png',p/'scene-spec.json')))
    def test_stale_mask_review_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);_,req=fixture(p);Image.new('L',(64,32),255).save(p/'mask.png')
            req['mask']=binding(p/'mask.png');write(p/'finish.json',req)
            with self.assertRaisesRegex(ValueError,'mask_sha256'):build(p/'finish.json',p/'out.png')
    def test_missing_full_coverage_review_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);_,req=fixture(p);mr=read_object(p/'mask-review.json')
            mr.pop('full_surface_coverage_checked');write(p/'mask-review.json',mr)
            req['mask_review']=binding(p/'mask-review.json');write(p/'finish.json',req)
            with self.assertRaisesRegex(ValueError,'full_surface_coverage'):build(p/'finish.json',p/'out.png')
    def test_guide_cannot_be_labeled_final_role(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);_,req=fixture(p);sr=read_object(p/'surface-review.json');sr['render_role']='calibration'
            write(p/'surface-review.json',sr);req['surface_review']=binding(p/'surface-review.json');write(p/'finish.json',req)
            with self.assertRaisesRegex(ValueError,'not a final'):build(p/'finish.json',p/'out.png')
    def test_broad_feather_and_soft_only_mask_rejected(self):
        for mask in (np.full((32,64),128,np.uint8),np.pad(np.full((14,62),255,np.uint8),((9,9),(1,1)),constant_values=128)):
            with self.assertRaises(ValueError):validate_mask(mask)
    def test_one_pixel_boundary_blend_supported(self):
        m=np.zeros((8,16),np.uint8);m[3:7,3:13]=255;m[2,3:13]=128
        validate_mask(m)
        out=compose(np.zeros((8,16,3),np.uint8),np.full((8,16,3),255,np.uint8),m)
        self.assertTrue(np.all((out[2,3:13]>180)&(out[2,3:13]<190)))
    def test_missing_downward_surface_views_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);_,req=fixture(p);sr=read_object(p/'surface-review.json');sr['reviewed_views']=['nadir']
            write(p/'surface-review.json',sr);req['surface_review']=binding(p/'surface-review.json');write(p/'finish.json',req)
            with self.assertRaisesRegex(ValueError,'required views'):build(p/'finish.json',p/'out.png')


class ReleaseTests(unittest.TestCase):
    def test_v3_complete_synthetic_chain_passes(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);complete(p)
            self.assertEqual(verify_pipeline(p/'pipeline.json'),[])
    def test_patterned_chain_without_finish_fails(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=complete(p);state.pop('surface_finish');write(p/'pipeline.json',state)
            self.assertTrue(any('surface_finish' in s for s in verify_pipeline(p/'pipeline.json')))
    def test_v2_pipeline_cannot_reuse_v3_gate(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=complete(p);state.pop('pipeline_version');write(p/'pipeline.json',state)
            self.assertTrue(any('pipeline_version' in s for s in verify_pipeline(p/'pipeline.json')))
    def test_stale_preflight_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=complete(p);state['planned_final_operation']='rendered_panorama';write(p/'pipeline.json',state)
            self.assertTrue(any('Preflight is stale' in s for s in verify_pipeline(p/'pipeline.json')))
    def test_renderer_only_request_needs_no_fictitious_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=complete(p)
            write(p/'request.json',{'mode':'render_existing_materials','actual_render_inputs':['synthetic fixture']})
            state['generation_request']=binding(p/'request.json');write(p/'pipeline.json',state)
            self.assertEqual(verify_pipeline(p/'pipeline.json'),[])


if __name__=='__main__': unittest.main(verbosity=2)
