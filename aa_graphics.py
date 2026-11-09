"""Small cached supersampling renderer; no platform-specific imaging dependency."""
import math
import struct
import zlib
from functools import lru_cache


def rgb(value):
    if value == "white":
        return (255, 255, 255)
    if value == "black":
        return (0, 0, 0)
    return tuple(int(value[i:i+2], 16) for i in (1, 3, 5))


def png(width, height, pixels):
    def chunk(name, data):
        return struct.pack(">I", len(data)) + name + data + struct.pack(">I", zlib.crc32(name+data) & 0xffffffff)
    rows = b"".join(b"\0"+bytes(pixels[y*width*4:(y+1)*width*4]) for y in range(height))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">2I5B", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 6)) + chunk(b"IEND", b""))


def rounded_pixels(width, height, fill, border, parent, radius=5, inset=.5):
    """Analytic coverage of a rounded rectangle and its one-pixel inner border."""
    fill, border, parent = rgb(fill), rgb(border), rgb(parent)
    result = bytearray(width*height*4)
    hw, hh = width/2-inset, height/2-inset
    radius = min(radius, hw, hh)
    for y in range(height):
        for x in range(width):
            qx = abs(x+.5-width/2) - (hw-radius)
            qy = abs(y+.5-height/2) - (hh-radius)
            distance = math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius
            outer = max(0, min(1, .5-distance))
            inner = max(0, min(1, -.5-distance))
            offset = (y*width+x)*4
            result[offset:offset+4] = bytes([round(parent[i]*(1-outer)+border[i]*(outer-inner)+fill[i]*inner)
                                            for i in range(3)] + [255])
    return result


@lru_cache(maxsize=256)
def rounded_png(width, height, fill, border, parent, radius=5):
    return png(width, height, rounded_pixels(width, height, fill, border, parent, radius))


def stroke_mask(size, shapes, stroke=1.8, samples=4):
    """Rasterize round-capped strokes at 4x resolution, then average coverage."""
    edge = size*samples
    mask = bytearray(edge*edge)
    scale = size/24*samples
    radius = stroke*scale/2

    def line(a, b):
        ax, ay = a[0]*scale, a[1]*scale
        bx, by = b[0]*scale, b[1]*scale
        dx, dy = bx-ax, by-ay
        denom = dx*dx+dy*dy
        for y in range(max(0, math.floor(min(ay, by)-radius)), min(edge, math.ceil(max(ay, by)+radius))):
            for x in range(max(0, math.floor(min(ax, bx)-radius)), min(edge, math.ceil(max(ax, bx)+radius))):
                px, py = x+.5-ax, y+.5-ay
                t = max(0, min(1, (px*dx+py*dy)/denom)) if denom else 0
                if (px-t*dx)**2+(py-t*dy)**2 <= radius*radius:
                    mask[y*edge+x] = 1

    for shape in shapes:
        points = shape["points"]
        if shape["kind"] == "circle":
            cx, cy, r = points
            points = [(cx+r*math.cos(i*math.tau/96), cy+r*math.sin(i*math.tau/96)) for i in range(97)]
        for a, b in zip(points, points[1:]):
            line(a, b)
    coverage = bytearray(size*size)
    for y in range(size):
        for x in range(size):
            total = sum(mask[(y*samples+dy)*edge+x*samples+dx]
                        for dy in range(samples) for dx in range(samples))
            coverage[y*size+x] = round(255*total/(samples*samples))
    return coverage


def icon_png(size, shapes, color):
    coverage = stroke_mask(size, shapes)
    color = rgb(color)
    result = bytearray(size*size*4)
    for i, alpha in enumerate(coverage):
        result[i*4:i*4+4] = bytes((*color, alpha))
    return png(size, size, result)


@lru_cache(maxsize=128)
def checkbox_png(size, color, background, checked):
    pixels = rounded_pixels(size, size, color if checked else "#1e2d47", color, background, radius=2.5, inset=1)
    if checked:
        # Normalized to Lucide's 24-unit coordinate system.
        shapes = [{"kind": "path", "points": [(5.3, 12), (10, 17), (19, 6.7)]}]
        coverage = stroke_mask(size, shapes, stroke=2.8, samples=8)
        for i, alpha in enumerate(coverage):
            for channel in range(3):
                offset = i*4+channel
                pixels[offset] = round(pixels[offset]*(1-alpha/255)+alpha)
    return png(size, size, pixels)
