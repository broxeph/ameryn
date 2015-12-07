import os
import multiprocessing
from PIL import Image, ImageOps

CASSETTES_FOLDER = 'D:/temp dev/Cassettes'
LPS_FOLDER = 'D:/temp dev/LPs'
SINGLES_FOLDER = 'D:/temp dev/45s'
OUTPUT_FOLDER = 'D:/temp dev/done'
CROP_SIZE = {
    'lp_tall': (0, 832, 3264, 4096),
    'lp_wide': (832, 0, 4096, 3264),
    '7_tall': (0, 832, 1900, 2732),
    '7_wide': (832, 1364, 2732, 3264),
    'cass_tall': (0, 832, 1150, 1982),
    'cass_wide': (832, 2114, 1982, 3264),
}

def crop_autocontrast_rotate180_cassettes(img_input):
    if img_input.lower().endswith('.jpg'):
        im = Image.open(os.path.join(CASSETTES_FOLDER, img_input))
        if im.size == (3264, 3264) or im.size == (1900, 1900):
            print 'Already cropped:', img_input
            return
        if im.size == (3264, 4928):
            box = CROP_SIZE['cass_tall']
        elif im.size == (4928, 3264):
            box = CROP_SIZE['cass_wide']
        else:
            print 'Nonstandard image size:', img_input
            return
        print img_input
        region = im.crop(box)
        region = ImageOps.autocontrast(region, 1)
        region = region.rotate(180)
        region.save(os.path.join(OUTPUT_FOLDER, img_input))

def crop_autocontrast_rotate180_lps(img_input):
    if img_input.lower().endswith('.jpg'):
        im = Image.open(os.path.join(LPS_FOLDER, img_input))
        if im.size == (3264, 3264) or im.size == (1900, 1900):
            print 'Already cropped:', img_input
            return
        if im.size == (3264, 4928):
            box = CROP_SIZE['lp_tall']
        elif im.size == (4928, 3264):
            box = CROP_SIZE['lp_wide']
        else:
            print 'Nonstandard image size:', img_input
            return
        print img_input
        region = im.crop(box)
        region = ImageOps.autocontrast(region, 1)
        region = region.rotate(180)
        region.save(os.path.join(OUTPUT_FOLDER, img_input))

def crop_autocontrast_rotate180_singles(img_input):
    if img_input.lower().endswith('.jpg'):
        im = Image.open(os.path.join(SINGLES_FOLDER, img_input))
        if im.size == (3264, 3264) or im.size == (1900, 1900):
            print 'Already cropped:', img_input
            return
        if im.size == (3264, 4928):
            box = CROP_SIZE['7_tall']
        elif im.size == (4928, 3264):
            box = CROP_SIZE['7_wide']
        else:
            print 'Nonstandard image size:', img_input
            return
        print img_input
        region = im.crop(box)
        region = ImageOps.autocontrast(region, 1)
        region = region.rotate(180)
        region.save(os.path.join(OUTPUT_FOLDER, img_input))

if __name__ == '__main__':
    pool = multiprocessing.Pool()
    pool.map(crop_autocontrast_rotate180_cassettes, os.listdir(CASSETTES_FOLDER))
    pool.map(crop_autocontrast_rotate180_lps, os.listdir(LPS_FOLDER))
    pool.map(crop_autocontrast_rotate180_singles, os.listdir(SINGLES_FOLDER))