#!/usr/bin/env python
"""
Make a colour clock/story wheel of the five most dominant colours
on each page of a book (or jpg).
"""
from __future__ import print_function
from PIL import Image, ImageDraw, ImageChops
from collections import namedtuple
from math import sqrt
import argparse
import glob
import os
import random
import sys

WHITE = (255, 255, 255)


def arc(draw, x_y, r, a_b, colour):
    """ Draw arc between two angles a and b, from, where 0 is 12 o'clock """
    x, y = x_y
    a, b = a_b
    bbox = (int(x-r), int(y-r), int(x+r), int(y+r))
    draw.pieslice(bbox, int(a-90), int(b-90), fill=colour)
    return draw


def circle(draw, x_y, r, colour):
    """ Draw a circle """
    x, y = x_y
    bbox = (x-r, y-r, x+r, y+r)
    draw.ellipse(bbox, fill=colour)
    return draw

# Testing:
# stuff = [
#     (18, (255,0,255)),
#     (9, (255,0,0)),
#     (9.2, "#d1b67b"),
# ]


def colour_clock(filename, outfile):
    """ Make and save the colour clock """
    size = (180, 180)

    im = Image.open(filename)
    im.thumbnail(size, Image.ANTIALIAS)
    im_size = im.size
    thumb = im.crop( (0, 0, size[0], size[1]) )
    offset_x = int(max( (size[0] - im_size[0]) / 2, 0 ))
    offset_y = int(max( (size[1] - im_size[1]) / 2, 0 ))
    thumb = ImageChops.offset(thumb, offset_x, offset_y)

    new_image = Image.new( 'RGB' , (256,180) , (255,255,255) )
    # paste it at an offset. if you put no offset or a box, i3 must match i2s dimensions
    new_image.paste( thumb, (40, 0) )

    print("Saving to:", outfile)
    new_image.save(outfile)


#########################################################

# Adapted from:
# http://charlesleifer.com/blog/using-python-and-k-means-to-find-the-dominant-colors-in-images/
Point = namedtuple('Point', ('coords', 'n', 'ct'))
Cluster = namedtuple('Cluster', ('points', 'center', 'n'))


def get_points(img):
    points = []
    w, h = img.size
    for count, color in img.getcolors(w * h):

        # For an "L" greyscale image we need a 3-coordinate RGB value
        if img.mode == "L":
            color = (color, color, color)

        points.append(Point(color, 3, count))
    return points


def rtoh(rgb):
    return '#%s' % ''.join(('%02x' % p for p in rgb))


def colorz(filename, n=3):
    img = Image.open(filename)  # .crop((120,140, 260, 340))
    img.thumbnail((200, 200))
    w, h = img.size

    points = get_points(img)
    clusters = kmeans(points, n, 1)
#     rgbs = [map(int, c.center.coords) for c in clusters]
#     return map(rtoh, rgbs)

    # clusters[i][0] contains all the points in a cluster,
    # so its size is a rough measure of it's dominance.
    # Let's use it but scale weights to equal 100%.
    total_weights = 0
    for c in clusters:
        total_weights += len(c[0])
    total_weights = float(total_weights)

    rgbs = []
    for c in clusters:
        rgb = map(int, c.center.coords)
        rgb = '#%s' % ''.join(('%02x' % p for p in rgb))
        rgbs.append((100 * len(c[0]) / total_weights, rgb))
    return rgbs


def euclidean(p1, p2):
    return sqrt(sum(
        (p1.coords[i] - p2.coords[i]) ** 2 for i in range(p1.n)
    ))


def calculate_center(points, n):
    vals = [0.0 for i in range(n)]
    plen = 0
    for p in points:
        plen += p.ct
        for i in range(n):
            vals[i] += (p.coords[i] * p.ct)
    return Point([(v / plen) for v in vals], n, 1)


def kmeans(points, k, min_diff):
    if k > len(points):
        k = len(points)

    clusters = [Cluster([p], p, p.n) for p in random.sample(points, k)]

    while 1:
        plists = [[] for i in range(k)]

        for p in points:
            smallest_distance = float('Inf')
            for i in range(k):
                distance = euclidean(p, clusters[i].center)
                if distance < smallest_distance:
                    smallest_distance = distance
                    idx = i
            plists[idx].append(p)

        diff = 0
        for i in range(k):
            old = clusters[i]
            center = calculate_center(plists[i], old.n)
            new = Cluster(plists[i], center, old.n)
            clusters[i] = new
            diff = max(diff, euclidean(old.center, new.center))

        if diff < min_diff:
            break

    return clusters

#########################################################


def create_dir(directory):
    if not os.path.isdir(directory):
        os.mkdir(directory)


def create_dirs(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Make a colour clock of the five most "
        "dominant colours on each page of a book",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        'input',
        help='An input PDF, or file spec of images (eg *.jpg)')
    parser.add_argument(
        '-o', '--outfile',
        help='Output filename')
    args = parser.parse_args()
    print(args)

    # Optional, http://stackoverflow.com/a/1557906/724176
    try:
        import timing
        assert timing  # silence warnings
    except ImportError:
        pass

    # Testing
#     colour_clock(stuff, args.outfile)
#     sys.exit()

    if not args.outfile:
        head, tail = os.path.split(args.input)
        args.outfile = os.path.splitext(tail)[0] + ".png"
        print("Outfile:", args.outfile)

    if args.input.lower().endswith(".pdf"):
        print("Convert PDF:", args.input)
        basename = os.path.splitext(args.input)[0]
        outdir = os.path.join("cache", basename)
        create_dirs(outdir)

        print("Converting, this is a bit slow...")
        cmd = 'convert -verbose -colorspace RGB -resize 800 -interlace none '
        '-density 300 -quality 80 "' + args.input + '" "' + \
            os.path.join(outdir, basename+'-%03d.jpg') + '"'
        print(cmd)
        os.system(cmd)

        args.input = os.path.join(outdir, basename + "*.jpg")

    else:
        # If input is dir, append *.jpg
        if os.path.isdir(args.input):
            args.input = os.path.join(args.input, "*.png")

    weighted_colours = []

    files = glob.glob(args.input)
    if len(files) == 0:
        sys.exit("No image files found")

    for f in files:
        print(f)
        try:
            weighted_colours = []
            new_weighted_colours = colorz(f, 10)
            weighted_colours.extend(sorted(new_weighted_colours, reverse=True))
            weighted_colours.append((10, WHITE))  # spacer

            basename = os.path.basename(f)
            colour_clock(f, os.path.splitext(basename)[0] + ".jpg")

        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            print("Ignoring problem file:", f)
            print(str(e))
            print(repr(e))
            continue

    print(weighted_colours)
    colour_clock(weighted_colours, args.outfile)
    #
    # dir = os.chdir("../Autoencoder/dataset/train/gt/" )
    # i = 0
    # for file in os.listdir(dir):
    #
    #     colour_clock(weighted_colours, str(i) + ".png")
    #    i = i + 1;

# End of file
