#!/usr/bin/env python3
"""Losslessly roll PNG pixels in longitude. Positive columns roll right; invert with -N."""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--columns", type=int, required=True)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error("Use a new output file; do not overwrite the source.")
    with Image.open(args.input) as image:
        if image.width != 2*image.height:
            parser.error("Input must be a 2:1 panorama.")
        if image.mode not in ("RGB", "RGBA"):
            parser.error("Input must be RGB or RGBA; convert explicitly first.")
        result = Image.fromarray(np.roll(np.asarray(image), args.columns, axis=1))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        options = {"icc_profile": image.info["icc_profile"]} if image.info.get("icc_profile") else {}
        result.save(args.output, format="PNG", **options)
    print(f"Saved {args.output.resolve()}; undo using --columns {-args.columns}.")


if __name__ == "__main__":
    main()
