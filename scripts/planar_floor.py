#!/usr/bin/env python3
"""World-space planar albedo projection and guarded compositing; not a PBR renderer.

Without --base, produce a calibration image / albedo guide. It is NOT final art.
With --base, require a reviewed, hash-bound visible-floor mask. Preserve every
zero-mask base pixel. Never infer visibility from the bottom half of an image.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np
from PIL import Image
from check_pano import digest, read_rgb


def vector(value: Any, count: int, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (count,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must have {count} finite components")
    return result


def validate_spec(spec: dict) -> dict:
    camera = vector(spec["camera"], 3, "camera")
    floor_z = float(spec["floor_z"])
    origin = vector(spec["origin_xy"], 2, "origin_xy")
    period = vector(spec["period_xy"], 2, "period_xy")
    angle = float(spec["rotation_degrees"])
    if not math.isfinite(floor_z) or camera[2] <= floor_z:
        raise ValueError("camera must lie strictly above the horizontal floor")
    if np.any(period <= 0) or not math.isfinite(angle):
        raise ValueError("period_xy must be positive; rotation must be finite")
    colors = np.asarray(spec.get("colors_srgb", [[224,208,178],[55,76,60]]), dtype=float)
    if colors.shape != (2,3) or not np.all(np.isfinite(colors)) or np.any((colors < 0)|(colors > 255)):
        raise ValueError("colors_srgb must contain two RGB triplets in [0,255]")
    return {"camera":camera,"floor_z":floor_z,"origin":origin,"period":period,
            "angle":math.radians(angle),"colors":colors}


def world_uv(directions: np.ndarray, spec: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Ray-plane intersection followed by one fixed Cartesian material frame.

    Positive rotation rotates the material U axis from world +X toward +Y.
    This is NOT the image-yaw convention. No camera-centric polar texture UVs.
    """
    d = np.asarray(directions, dtype=np.float64)
    if d.shape[-1] != 3 or not np.all(np.isfinite(d)):
        raise ValueError("directions must be finite XYZ vectors")
    s = validate_spec(spec)
    valid = d[...,2] < -1e-10
    t = np.divide(s["floor_z"]-s["camera"][2], d[...,2],
                  out=np.zeros_like(d[...,2]), where=valid)
    x = s["camera"][0] + t*d[...,0] - s["origin"][0]
    y = s["camera"][1] + t*d[...,1] - s["origin"][1]
    c, sn = math.cos(s["angle"]), math.sin(s["angle"])
    u = (c*x + sn*y)/s["period"][0]
    v = (-sn*x + c*y)/s["period"][1]
    return u, v, valid


def periodic_sample(texture: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Bilinear periodic sampling, both axes wrapping; image top is material v=0."""
    h,w = texture.shape[:2]
    x,y = np.mod(u,1)*w-0.5, np.mod(v,1)*h-0.5
    ix,iy = np.floor(x).astype(np.int64),np.floor(y).astype(np.int64)
    fx,fy = (x-ix)[...,None],(y-iy)[...,None]
    return ((1-fy)*((1-fx)*texture[iy%h,ix%w]+fx*texture[iy%h,(ix+1)%w])+
            fy*((1-fx)*texture[(iy+1)%h,ix%w]+fx*texture[(iy+1)%h,(ix+1)%w]))


def albedo(directions: np.ndarray, spec: dict, texture: np.ndarray | None = None) -> tuple[np.ndarray,np.ndarray]:
    u,v,valid = world_uv(directions,spec)
    if texture is None:
        colors = validate_spec(spec)["colors"]
        # Period describes one tile for the procedural checker, one complete
        # repeated image for --texture. Floor-space tile phase is shared globally.
        parity = np.mod(np.floor(u)+np.floor(v),2).astype(np.int8)
        rgb = colors[parity]
    else:
        rgb = periodic_sample(texture,u,v)
    rgb = np.where(valid[...,None],rgb,0)
    return rgb,valid


def render(width: int, spec: dict, samples_side: int = 2,
           texture: np.ndarray | None = None) -> tuple[np.ndarray,np.ndarray]:
    validate_spec(spec)
    if width < 32 or width > 8192 or width%2 or not 1 <= samples_side <= 4:
        raise ValueError("width must be even in [32,8192]; samples-side in [1,4]")
    h = width//2
    result = np.zeros((h,width,3),np.float32)
    coverage = np.zeros((h,width),np.float32)
    # Row chunks limit temporary memory; stratification is diagnostic AA, not EWA.
    for y0 in range(0,h,32):
        y1=min(h,y0+32)
        for sy in range(samples_side):
            pitch=np.pi*(0.5-(np.arange(y0,y1)+(sy+0.5)/samples_side)/h)
            for sx in range(samples_side):
                yaw=2*np.pi*((np.arange(width)+(sx+0.5)/samples_side)/width-0.5)
                cp=np.cos(pitch)[:,None]
                d=np.stack([cp*np.sin(yaw)[None,:],cp*np.cos(yaw)[None,:],
                            np.broadcast_to(np.sin(pitch)[:,None],(y1-y0,width))],axis=-1)
                rgb,valid=albedo(d,spec,texture)
                result[y0:y1]+=rgb/(samples_side*samples_side)
                coverage[y0:y1]+=valid/(samples_side*samples_side)
    return result,coverage


def mask_review_errors(base:Path, mask:Path, spec:Path, review:Path) -> list[str]:
    data=json.loads(review.read_text())
    if not isinstance(data,dict):
        raise ValueError("Mask review must be a JSON object")
    errors=[]
    for key,path in [("candidate_sha256",base),("mask_sha256",mask),("floor_spec_sha256",spec)]:
        if data.get(key)!=digest(path):
            errors.append(f"Mask review {key} does not match current bytes")
    if data.get("status")!="passed" or not data.get("reviewer") or not str(data.get("evidence","")).strip():
        errors.append("Mask review must have passed with reviewer and specific evidence")
    if data.get("camera_and_layout_aligned") is not True:
        errors.append("Candidate camera and layout correspondence must be reviewed")
    if data.get("occlusions_and_contacts_checked") is not True:
        errors.append("Visible floor mask must exclude objects/walls and preserve contact boundaries")
    return errors


def composite(base:np.ndarray, floor:np.ndarray, mask:np.ndarray,
              coverage:np.ndarray) -> np.ndarray:
    if base.shape!=floor.shape or mask.shape!=base.shape[:2]:
        raise ValueError("Base, projected floor, and mask must have exactly matching dimensions")
    if not np.all(np.isfinite(mask)) or np.any((mask<0)|(mask>1)):
        raise ValueError("Mask values must be finite in [0,1]")
    if np.any((mask>0)&(coverage<0.999)):
        raise ValueError("Mask includes rays that do not hit the floor plane")
    if not np.any(mask>0):
        raise ValueError("Visible floor mask is empty")
    def linear(x):
        x=x/255.0
        return np.where(x<=0.04045,x/12.92,((x+0.055)/1.055)**2.4)
    mix=linear(base)*(1-mask[...,None])+linear(floor)*mask[...,None]
    srgb=np.where(mix<=0.0031308,12.92*mix,1.055*np.maximum(mix,0)**(1/2.4)-0.055)
    result=np.clip(np.rint(srgb*255),0,255).astype(np.uint8)
    result[mask==0]=base[mask==0].astype(np.uint8)  # Exact decoded-pixel preservation.
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--width",type=int,default=1536)
    parser.add_argument("--samples-side",type=int,default=2)
    parser.add_argument("--texture",type=Path,help="Orthographic, repeatable albedo patch; not a perspective photograph")
    parser.add_argument("--base",type=Path)
    parser.add_argument("--mask",type=Path,help="Opaque grayscale PNG, white=visible floor, black=protected")
    parser.add_argument("--mask-review",type=Path)
    args=parser.parse_args()
    try:
        if args.output.suffix.lower()!=".png":
            raise ValueError("Output must be PNG")
        inputs=[args.spec,args.texture,args.base,args.mask,args.mask_review]
        if any(p is not None and p.resolve()==args.output.resolve() for p in inputs):
            raise ValueError("Output must not overwrite any input")
        spec=json.loads(args.spec.read_text())
        validate_spec(spec)
        texture=None
        if args.texture:
            with Image.open(args.texture) as im:
                if im.width>8192 or im.height>8192:
                    raise ValueError("Texture exceeds maximum supported dimensions")
                if np.any(np.asarray(im.convert("RGBA"))[...,3]!=255):
                    raise ValueError("Albedo texture must be opaque")
                texture=np.asarray(im.convert("RGB"),dtype=np.float32)
        width=args.width
        info=None
        if args.base:
            if not args.mask or not args.mask_review:
                raise ValueError("Compositing requires --mask and --mask-review")
            errors=mask_review_errors(args.base,args.mask,args.spec,args.mask_review)
            if errors:
                raise ValueError("; ".join(errors))
            base,info=read_rgb(args.base)
            if info["format"]!="PNG" or info["width"]!=2*info["height"] or info["transparent_pixel_count"]:
                raise ValueError("Base must be an opaque exact 2:1 PNG")
            width=info["width"]
        elif args.mask or args.mask_review:
            raise ValueError("Mask options require --base; no implicit floor visibility is inferred")
        floor,coverage=render(width,spec,args.samples_side,texture)
        if args.base:
            with Image.open(args.mask) as im:
                if im.format!="PNG" or im.mode not in ("L","1"):
                    raise ValueError("Mask must be an opaque grayscale PNG (mode L or 1)")
                mask=np.asarray(im.convert("L"),dtype=np.float32)/255
            pixels=composite(base,floor,mask,coverage)
            mode="masked_planar_albedo_composite_not_pbr"
        else:
            # Constant upper hemisphere is deliberate for calibration, never a repair.
            pixels=np.clip(np.rint(floor+np.array([95,111,130])*(1-coverage[...,None])),0,255).astype(np.uint8)
            mode="infinite_plane_calibration_not_final_art"
        args.output.parent.mkdir(parents=True,exist_ok=True)
        Image.fromarray(pixels).save(args.output)
        manifest={"mode":mode,"projection":"equirectangular","angular_coverage_degrees":[360,180],
                  "camera":spec["camera"],"width":width,"height":width//2,
                  "floor_spec_sha256":digest(args.spec),"output_sha256":digest(args.output),
                  "texture_sha256":digest(args.texture) if args.texture else None,
                  "base_sha256":info["sha256"] if info else None,
                  "mask_sha256":digest(args.mask) if args.mask else None,
                  "limitations":["Horizontal infinite plane; no automatic visibility inference.",
                                  "Albedo only: no shadows, glossy reflections, relighting, or PBR.",
                                  "Limited supersampling; grazing-angle aliasing may require a texture-filtered renderer.",
                                  "Mask judgments are recorded, not automatically proven. Re-run final-file QA."]}
        args.output.with_suffix(".manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
        print(json.dumps(manifest,indent=2))
        return 0
    except (OSError,ValueError,TypeError,KeyError,Image.DecompressionBombError) as exc:
        print(f"planar_floor: {exc}",file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
