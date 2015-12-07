from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import math
import os
import wave
import contextlib
import datetime
import csv
from PIL import Image
import sys

whole_folder = True
some_orders = False
some_items = False
orders = ['02000']
items = ['02000-00001']
folder = 'C:/00 Recordings/trackt'
images_folder = 'Q:/Cover pictures/'
thumbs_folder = 'Q:/Cover pictures/CURRENT thumbs/'
db_path = 'C:/Sextus share/items.csv'
images = []
comp_orders = []

def add_file(audio_file):
    audio_path = os.path.join(folder, audio_file)
    audio_serial = os.path.splitext(audio_file)[0].rsplit('_clean')[0]
    img_counter = 0

    # Check db for mp3, copies
    with open(db_path, 'r') as items:
        rows = csv.reader(items)
        for row in rows:
            if row[0] == audio_serial:
                # Only use the first cover of a 45 to CD/mp3 order
                if '45' in row[3]:
                    if audio_serial[5] in comp_orders:
                        return
                    else:
                        comp_orders.append(audio_serial[5])
                # mp3: Make thumbnail
                if 'mp3' in row[5].lower():
                    mp3_thumbnail(audio_serial)
                    return
                # Using other image serial
                if row[6]:
                    img_counter = 1
                    while True:
                        if not row[6] + '_' + str(img_counter) in images:
                            audio_serial = row[6] + '_' + str(img_counter)
                        img_counter += 1
                if row[7]:
                    copies = int(row[7])
                    break
                else:
                    copies = 1
                    break
        else:
            print 'Row', audio_serial, 'not found in', db_path + '.'

    # Get, print audio file length
    with contextlib.closing(wave.open(audio_path, 'r')) as f:
        duration = f.getnframes() / float(f.getframerate())
    audio_duration = str(datetime.timedelta(seconds=int(duration)))
    print audio_file, '| Length:', audio_duration,

    # Double: increment img counter
    if int(duration) > 4700:
        print '(Double!)'
        if not img_counter:
            img_counter = 1
        for i in range(2):
            images.extend([(audio_serial + '_' + str(img_counter))] * copies)
            img_counter += 1

    else:
        print
        if img_counter:
            images.extend([(audio_serial + '_' + str(img_counter))] * copies)
        else:
            images.extend([audio_serial] * copies)

def mp3_thumbnail(audio_serial):
    img_path = os.path.join(images_folder, audio_serial) + '.jpg'
    thumb_path = os.path.join(thumbs_folder, audio_serial) + '_600x600.jpg'
    print 'Thumbnail:', thumb_path
    im = Image.open(img_path)
    im.thumbnail((600, 600))
    im.save(thumb_path, 'JPEG')

def make_front_pdf(images):
    def add_image(position):
        img = images_iter.next()
        img_path = os.path.join(images_folder,img).rsplit('_')[0] + '.jpg'
        if position == 'top':
            img_adjustment = 4.8 * inch
            label_adjustment = 10.2 * inch
        elif position == 'bottom':
            img_adjustment = 0
            label_adjustment = 0
        # Draw cover image
        c.drawImage(img_path, 1.85 * inch, 0.7*inch + img_adjustment, width=4.8 * inch, height=4.8 * inch)
        c.rect(1.85 * inch, 0.7*inch + img_adjustment, 4.8 * inch , 4.8 * inch, fill=0)
        # Draw image counter on label (1, 2, etc.)
        if img[-2] == '_':
            c.setFont('Garamond', 24)
            c.drawString(4.3 * inch, 1*inch + img_adjustment, img[-1])
        # Draw image label
        c.setFont('Helvetica', 12)
        c.drawString(3.8 * inch, 0.3*inch + label_adjustment, img)

    if not images:
        msg = 'No images found in folder: ' + folder
        raise SystemError(msg)
    print 'Images:', images
    images_iter = iter(images)
    c = canvas.Canvas('covers-front.pdf', pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', 'c:/sextus share/garamond8.ttf'))
    c.setLineWidth(0.5)
    print 'Front cover pages:', int(math.ceil(float(len(images)) / 2))

    for pair in range(int(math.ceil(float(len(images)) / 2))):   
        add_image('top')
        try: # Second (lower) image
            add_image('bottom')
        except StopIteration:
            pass
        c.showPage()
    c.save()

def make_cd_pdf(images):
    if not images:
        msg = 'No images found in folder: ' + folder
        raise SystemError(msg)
    images_iter = iter(images)
    c = canvas.Canvas('cd-labels.pdf', pagesize=(130 * mm, 225 * mm))
    width, height = (130 * mm, 225 * mm)
    pdfmetrics.registerFont(TTFont('Garamond', 'c:/sextus share/garamond8.ttf'))
    print 'CD pages:', len(images)

    for image in images:
        # Clipping
        path = c.beginPath()
        path.circle(65 * mm, 105 * mm, 60 * mm)
        path.circle(65 * mm, 105 * mm, 10 * mm)
        c.clipPath(path, stroke = 1, fill = 0)
        img = images_iter.next()
        img_path = os.path.join(images_folder,img).rsplit('_')[0] + '.jpg'
        # Draw CD image
        c.drawImage(img_path, 5 * mm, 45 * mm, width=120 * mm, height=120 * mm)
        # Draw image counter on label (1, 2, etc.)
        if img[-2] == '_':
            c.setFont('Garamond', 24)
            c.drawString(62.5 * mm, 50 * mm, img[-1])
        c.showPage()
    c.save()

def make_back_pdf(images):
    def check_std(image):
        audio_serial = image.rsplit('_')[0]
        with open(db_path, 'r') as items:
            rows = csv.reader(items)   
            for row in rows:
                if row[0] == audio_serial:
                    if 'std' in row[4].lower():
                        print image, 'skipped: std'
                    else:
                        deluxe_list.append(image)
                    return

    def add_image(position):
        try:
            img = images_iter.next()
        except StopIteration:
            return
        audio_serial = img.rsplit('_')[0]
        audio_path = os.path.join(folder, img).rsplit('_')[0]

        with open(db_path, 'r') as items:
            rows = csv.reader(items)
            for row in rows:
                if row[0] == audio_serial:                    
                    if '45' in row[3]:
                        # DO THE 45 THANG
                        break
                    else:
                        break
            else:
                print 'Row', audio_serial, 'not found in', db_path + '.'
            img_path = os.path.join(images_folder,img).rsplit('_')[0] + '.jpg'
            if position == 'top':
                img_adjustment = 118 * mm
                label_adjustment = 10.2 * inch
            elif position == 'bottom':
                img_adjustment = 0
                label_adjustment = 0
            # Draw Ameryn logo watermark
            c.drawImage('Q:/Images/ameryn-logo-watermark-2.jpg', 157 * mm, 25*mm + img_adjustment, width=16 * mm, height=11 * mm)
            # Draw artist/album titles
            line2 = ''
            if row[1] and row[2]:
                line1 = row[1]
                line2 = row[2]
                spine = line1 + ' - ' + line2
            elif row[1]:
                line1 = row[1]
                spine = line1
            elif row[2]:
                line1 = row[2]
                spine = line1
            else:
                line1 = 'Untitled'
            # Add disc # for multi-disc sets
            if img[-2] == '_':
                spine += '(Disc ' + img[-1] + ')'
                if line2:
                    line2 += '(Disc ' + img[-1] + ')'
                else: