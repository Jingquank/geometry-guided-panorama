#!/usr/bin/env python3
"""Synthetic contract/projection regressions, NOT scene-generation quality tests."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from PIL import Image
import numpy as np
from inspection_plan import validate_plan, target_views, plan_digest
from check_pano import check, perspective, rays, sample_equirectangular
from verify_review import verify
from execution_self_test import complete, write
from execution_guard import binding, report_for, preflight
from release_check import verify_pipeline


def spec(kind='organic_form', label='ridge'):
    return {'inspection_plan': {'version':1,'targets':[{'id':label,'kind':kind,
        'basis':'observed','source_evidence':'SYNTHETIC source-region fixture',
        'preserve':'SYNTHETIC feature shape', 'failure_signal':'SYNTHETIC shape drift',
        'yaw':20, 'pitch':-10, 'fov':60}]}}


def approve(path):
    r=json.loads(path.read_text());r.update(status='passed', reviewer='SYNTHETIC TEST ONLY',reviewed_views=r['required_views'])
    for c in r['checks'].values():c.update(status='pass', evidence='SYNTHETIC',views=['nadir','floor-front'])
    for key,c in r['target_checks'].items():c.update(status='pass',evidence='SYNTHETIC',views=[f'target-{key}-a',f'target-{key}-b'])
    write(path,r)
    return r


class GeneralSceneTests(unittest.TestCase):
    def test_scene_constraints_are_not_rectangular_templates(self):
        for kind,label in [('planar_surface','counter'),('straight_edge','facade'),
            ('organic_form','ridge'),('curved_form','arch'),('contact_occlusion','tree-rock'),
            ('lighting_reflection','water-light'),('repetition','columns')]:
            s=spec(kind,label);self.assertEqual(validate_plan(s)['targets'][0]['kind'],kind)
    def test_empty_sky_requires_reason(self):
        with self.assertRaises(ValueError):validate_plan({'inspection_plan':{'version':1,'targets':[]}})
        self.assertEqual(validate_plan({'inspection_plan':{'version':1,'targets':[],
            'no_targets_reason':'Featureless synthetic sky'}})['targets'],[])
    def test_missing_evidence_and_bad_angles_rejected(self):
        for field,value in [('source_evidence',''),('basis','guessed-as-observed'),('yaw',float('nan')),('fov',180),('pitch',100),('id','../escape')]:
            s=spec();s['inspection_plan']['targets'][0][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):validate_plan(s)
    def test_duplicate_target_rejected(self):
        s=spec();s['inspection_plan']['targets']*=2
        with self.assertRaises(ValueError):validate_plan(s)
    def test_overlapping_target_uses_requested_fov(self):
        p=validate_plan(spec());vs=target_views(p)
        self.assertEqual(vs[1][1]-vs[0][1],12)
        a=rays(64,20,-10,60);b=rays(64,20,-10,90)
        self.assertFalse(np.allclose(a,b))
        image=np.random.default_rng(42).uniform(0,255,(64,128,3))
        expected=np.clip(np.rint(sample_equirectangular(image,a)),0,255).astype(np.uint8)
        self.assertTrue(np.array_equal(np.asarray(perspective(image,64,20,-10,60)),expected))
    def fixture(self,p):
        Image.new('RGB',(128,64),'tan').save(p/'p.png');write(p/'spec.json',spec())
        check(p/'p.png',p/'qa',32,scene_spec=p/'spec.json')
        return p/'qa/visual-review.json'
    def test_target_exports_never_auto_approve(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);rp=self.fixture(p);r=json.loads(rp.read_text())
            self.assertEqual(len(r['required_views']),20)
            self.assertTrue((p/'qa/target-ridge-b.png').is_file())
            self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
    def test_missing_target_view_or_evidence_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);rp=self.fixture(p);r=approve(rp)
            self.assertEqual(verify(p/'p.png',rp,p/'spec.json'),[])
            r['target_checks']['ridge']['views'].pop();write(rp,r)
            self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
            r=approve(rp);r['reviewed_views'].pop();write(rp,r)
            self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
    def test_new_shared_checks_cannot_be_omitted(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);rp=self.fixture(p)
            baseline=approve(rp)
            for key in ('lighting_consistency','spatial_relations','cross_view_consistency'):
                r=copy.deepcopy(baseline);r['checks'].pop(key);write(rp,r)
                self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
                check(p/'p.png',p/'qa',32,scene_spec=p/'spec.json')
    def test_plan_change_resets_review_even_same_png(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);rp=self.fixture(p);approve(rp)
            s=spec();s['inspection_plan']['targets'][0]['fov']=45;write(p/'spec.json',s)
            self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
            check(p/'p.png',p/'qa',32,scene_spec=p/'spec.json')
            self.assertEqual(json.loads(rp.read_text())['status'],'not_reviewed')
    def test_downstream_pass_cannot_replace_panorama_pass(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);rp=self.fixture(p);r=approve(rp)
            r['downstream_validation']={'status':'passed'};write(rp,r)
            self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
            r['downstream_validation'].update(system='Synthetic',workflow='fixture',evidence='fixture',artifact='fixture')
            r['status']='failed';write(rp,r)
            self.assertTrue(verify(p/'p.png',rp,p/'spec.json'))
    def test_release_requires_plan_even_for_direct_sky(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=complete(p)
            s={'route':'direct_simple','scene_type':'sky','acceptance':{'structure_sensitive':False}}
            write(p/'scene-spec.json',s);state['scene_spec']=binding(p/'scene-spec.json');write(p/'pipeline.json',state)
            self.assertTrue(any('inspection_plan' in e for e in preflight(p/'pipeline.json')))
    def test_release_rejects_detached_final_plan(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);state,_=complete(p)
            rp=Path(state['candidate_review']['path']);r=json.loads(rp.read_text());r['inspection_plan']=None;write(rp,r)
            state['candidate_review']=binding(rp);write(p/'pipeline.json',state)
            self.assertTrue(any('inspection plan' in e for e in verify_pipeline(p/'pipeline.json')))

if __name__=='__main__':unittest.main(verbosity=2)
