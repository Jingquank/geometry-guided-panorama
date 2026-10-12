"""Evidence-led adaptive QA. Records constrain review, not scene interpretation."""
import hashlib
import json
import math
import re

KINDS = {'straight_edge', 'planar_surface', 'curved_form', 'organic_form',
         'repetition', 'contact_occlusion', 'lighting_reflection'}


def validate_plan(spec):
    plan = spec.get('inspection_plan')
    if not isinstance(plan, dict) or plan.get('version') != 1:
        raise ValueError('inspection_plan version 1 is required for every scene')
    if not isinstance(plan.get('targets'), list):
        raise ValueError('inspection_plan.targets must be a list')
    if not plan['targets'] and not str(plan.get('no_targets_reason', '')).strip():
        raise ValueError('An empty inspection plan requires no_targets_reason')
    seen = set()
    for t in plan['targets']:
        if not isinstance(t, dict):
            raise ValueError('Inspection target must be an object')
        key = t.get('id', '')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,63}', key) or key in seen:
            raise ValueError('Target IDs must be unique, safe lowercase names')
        seen.add(key)
        if t.get('kind') not in KINDS or t.get('basis') not in {'observed', 'user_requested', 'inferred'}:
            raise ValueError(f'{key}: unsupported kind or evidence basis')
        for field in ('source_evidence', 'preserve', 'failure_signal'):
            if not isinstance(t.get(field), str) or not t[field].strip():
                raise ValueError(f'{key}: missing {field}')
        for field, lo, hi in [('yaw', -180, 180), ('pitch', -90, 90), ('fov', 20, 110)]:
            value = t.get(field)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not lo <= value <= hi:
                raise ValueError(f'{key}: invalid {field}')
    return plan


def plan_digest(plan):
    return hashlib.sha256(json.dumps(plan, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def target_views(plan):
    """Two overlapping rotations around the SAME center, not independent 3D views."""
    result = []
    for t in plan['targets']:
        for suffix, yaw in [('a', t['yaw']), ('b', (t['yaw'] + t['fov']*.2 + 180) % 360 - 180)]:
            result.append((f"target-{t['id']}-{suffix}", yaw, t['pitch'], t['fov']))
    return result


def target_records(plan):
    return {t['id']: {'status': 'not_reviewed', 'evidence': '', 'views': []}
            for t in plan['targets']}
