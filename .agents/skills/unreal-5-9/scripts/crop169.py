"""Crop a viewport capture to its centred 16:9 region and report mean luminance. Usage: crop169.py in.png out.png [width]"""
import sys
from PIL import Image, ImageStat

src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src).convert("RGB")
w, h = im.size
if w * 9 >= h * 16:          # too wide: bars left and right
    cw, ch = h * 16 // 9, h
else:                        # too tall: bars top and bottom
    cw, ch = w, w * 9 // 16
left, top = (w - cw) // 2, (h - ch) // 2
im = im.crop((left, top, left + cw, top + ch))
if len(sys.argv) > 3:
    width = int(sys.argv[3])
    im = im.resize((width, width * 9 // 16), Image.LANCZOS)
im.save(dst)
r, g, b = ImageStat.Stat(im).mean
print(f"{dst}: {im.size[0]}x{im.size[1]} mean rgb=({r:.0f},{g:.0f},{b:.0f}) luma={(0.2126*r+0.7152*g+0.0722*b)/255:.3f}")
