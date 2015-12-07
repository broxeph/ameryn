from PIL import Image, ImageOps

im = Image.open('ski.jpg')
print im.format, im.size, im.mode
h = im.histogram()
print 'layers:', len(h) / 256
n = 0
for ix in range(256):
    n += h[ix]
print 'n:', n
print 'l x w:', im.size[0] * im.size[1]

new = ImageOps.autocontrast_preserve(im, cutoff=1)
new.save('ski_new.jpg')