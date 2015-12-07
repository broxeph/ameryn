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
import split
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

whole_folder = True
some_orders = False
some_items = False
orders = ['02000']
items = ['02000-00001']
folder = 'D:/00 Recorded/trackt'
images_folder = 'Q:/Cover pictures/'
thumbs_folder = 'Q:/Cover pictures/CURRENT thumbs/'
mp3_folder = 'D:/00 Recorded/mp3'
db_path = 'C:/Sextus share/items.csv'
images = []
comp_orders = []

def add_file(audio_file):
    audio_path = os.path.join(folder, audio_file)
    audio_serial = os.path.splitext(audio_file)[0].rsplit('_clean')[0]
    img_counter = 0
    copies = 1

    # Check db for mp3, copies
    with open(db_path, 'r') as items:
        rows = csv.reader(items)
        for row in rows:
            if row[0] == audio_serial:
                # Only use the first cover of a 45 to CD/mp3 order
                if '45' in row[3]:
                    if audio_serial[:5] in comp_orders:
                        return
                    else:
                        comp_orders.append(audio_serial[:5])
                        print comp_orders
                # mp3: Make thumbnail
                if 'mp3' in row[5].lower():
                    mp3_thumbnail(audio_serial)
                    make_mp3s(audio_serial)
                    return
                # Using other image serial
                if row[6]:
                    # Check to ensure used image serial is in this batch; otherwise, don't use underscore/counter.
                    for each in os.listdir(folder):
                        if each.startswith(row[6]):
                            img_counter = 1
                            while True:
                                if not row[6] + '_' + str(img_counter) in images:
                                    audio_serial = row[6] + '_' + str(img_counter)
                                img_counter += 1
                            break
                    else:
                        audio_serial = row[6]         
                if row[7]:
                    copies = int(row[7])
                    break
                else:
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

def make_mp3s(audio_serial):
    audio_path_full = audio_path + '_clean.wav'
    mp3_img = os.path.join(images_folder, audio_serial).rsplit('_')[0] + '.jpg'
    print 'mp3:', audio_serial
    # Standard
    if 'std' in row[4].lower():
        mp3_track = AudioSegment.from_wav(audio_path_full)
        mp3_track.export(mp3track, format='mp3', bitrate='192', tags={title:row[2], artist:row[1], album:row[2]})
        # Add cover art
        audio = MP3((os.splitext(audio_path_full)[0] + '.mp3'), ID3=ID3)
        # Add ID3 tag if it doesn't exist
        try:
            audio.add_tags()
        except error:
            pass
        audio.tags.add(
            APIC(
                encoding=3, # 3 is for utf-8
                mime='image/jpg', # image/jpeg or image/png
                type=3, # 3 is for the cover image
                desc=u'Cover',
                data=open(mp3_img).read()
            )
        )
        audio.save()
    # Deluxe/45
    else:        
        # Get track listing
        tracks = []
        for i in range(30):
            if row[11 + i]:
                tracks.append(row[11 + i])
            else:
                break
        split.split_file(audio_path_full, format='mp3', bitrate='192', tracks=tracks, artist=row[1], album=row[2], cover=mp3_img)
    # Embed cover thumbnails
    for each_mp3 in os.listdir(mp3_folder):
        if each_mp3.startswith(audio_serial):
            pass # do the thing

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
            # Read spreadsheet
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
            # Image positioning
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
                spine += ' (Disc ' + img[-1] + ')'
                if line2:
                    line2 += ' (Disc ' + img[-1] + ')'
                else:
                    line2 = 'Disc ' + img[-1]
            # Line 1
            c.setFont('Garamond', 18)
            if pdfmetrics.stringWidth(line1, 'Garamond', 18) > 125 * mm:
                c.setFont('Garamond', 16)
            if pdfmetrics.stringWidth(line1, 'Garamond', 16) > 125 * mm:
                c.setFont('Garamond', 14)
            if pdfmetrics.stringWidth(line1, 'Garamond', 14) > 125 * mm:
                c.setFont('Garamond', 12)
            if pdfmetrics.stringWidth(line1, 'Garamond', 12) > 125 * mm:
                c.setFont('Garamond', 11)
            if pdfmetrics.stringWidth(line1, 'Garamond', 11) > 125 * mm:
                c.setFont('Garamond', 10)
            c.drawString(48 * mm, 125*mm + img_adjustment, line1)
            # Line 2
            if line2:
                c.setFont('Garamond', 14)
                if pdfmetrics.stringWidth(line2, 'Garamond', 14) > 125 * mm:
                    c.setFont('Garamond', 12)
                if pdfmetrics.stringWidth(line2, 'Garamond', 12) > 125 * mm:
                    c.setFont('Garamond', 11)
                if pdfmetrics.stringWidth(line2, 'Garamond', 11) > 125 * mm:
                    c.setFont('Garamond', 10)
                c.drawString(48 * mm, 118*mm + img_adjustment, line2)
            # Horizontal divider
            c.setLineWidth(2)
            c.line(48 * mm, 112*mm + img_adjustment, 168 * mm, 112*mm + img_adjustment)
            # Set spine label font size
            c.saveState()
            c.rotate(90)
            fontsize = 9
            if pdfmetrics.stringWidth(spine, 'Garamond', 9) > 116 * mm:
                fontsize = 8
            if pdfmetrics.stringWidth(spine, 'Garamond', 8) > 116 * mm:
                fontsize = 7
            c.setFont('Garamond', fontsize)
            # Left spine label
            x = (118*mm - pdfmetrics.stringWidth(spine, 'Garamond', fontsize))/2 + 21.7*mm + img_adjustment
            y = -37.3 * mm
            c.drawString(x, y, spine)
            # Right spine label
            c.rotate(180)
            x = (118*mm - pdfmetrics.stringWidth(spine, 'Garamond', fontsize))/2 - 139.7*mm - img_adjustment
            y = 178.7 * mm
            c.drawString(x, y, spine)
            c.restoreState()
            # Get track durations
            print audio_path
            cues = split.read_markers(audio_path + '_clean.wav')
            durations = []
            for i in range(1, len(cues)):
                duration = cues[i] - cues[i - 1]
                m, s = divmod(duration / 44100, 60)
                durations.append(str(m) + ':' + str(s).zfill(2))
            print durations
            # Get track listing
            tracks = []
            # No track names
            if not row[11]:
                for i in range(len(durations)):
                    tracks.append('Track ' + str(i + 1))
            else:
                for i in range(30):
                	if row[11 + i]:
                		tracks.append(row[11 + i])
                	else:
                		break
            # Compile track data
            if len(tracks) != len(durations):
                err = 'Track/marker mismatch for ' + audio_serial + ': ' + str(len(tracks)) + ' on spreadsheet; ' + str(len(durations)) + ' on file.'
            	raise SystemError(err)            
            track_data = []
            for i in range(len(durations)):
            	track_data.append([(str(i + 1) + '.'), tracks[i], durations[i]])
            # Draw track listing
            table = Table(track_data, colWidths=[6 * mm, 100 * mm, 10 * mm])
            fontsize = 11
            padding = 2
            if len(tracks) > 14:
            	fontsize = 10
            if len(tracks) > 16:
                fontsize = 9
                padding = 1
            table.setStyle(TableStyle([
                                    ('FONT', (0,0), (-1,-1), 'Garamond', fontsize),
                                    ('TOPPADDING', (0,0), (-1,-1), padding),
                                    ('BOTTOMPADDING', (0,0), (-1,-1), padding),
                                    ]))
            w, h = table.wrap(width, height)
            table.wrapOn(c, width, height)
            table.drawOn(c, 49 * mm, 108*mm - h + img_adjustment)

        # Draw crop lines
        c.setLineWidth(0.5)
        c.rect(33 * mm, 21.7*mm + img_adjustment, 150 * mm , 118 * mm, fill=0) 
        c.line(39 * mm, 21.7*mm + img_adjustment, 39 * mm, 139.7*mm + img_adjustment)
        c.line(177 * mm, 21.7*mm + img_adjustment, 177 * mm, 139.7*mm + img_adjustment)
        # Draw image label
        c.setFont('Helvetica', 12)
        c.drawString(3.8 * inch, 0.3*inch + label_adjustment, img)

    # Skip images if Standard transfer
    deluxe_list = [] 
    for image in images:
        check_std(image)        

    if not deluxe_list:
        print 'No Deluxe CDs found in folder: ' + folder
        sys.exit()
        
    print 'Images:', deluxe_list
    images_iter = iter(deluxe_list)
    c = canvas.Canvas('covers-back.pdf', pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', 'c:/sextus share/garamond8.ttf'))

    for pair in range(int(math.ceil(float(len(deluxe_list)) / 2))):
        add_image('top')
        try: # Second (lower) image
            add_image('bottom')
        except StopIteration:
            break
        c.showPage()
    c.save()

if whole_folder:
    for each_file in os.listdir(folder):
        if each_file.lower().endswith('.wav'):
            add_file(each_file)    
elif some_orders:
    for each_file in os.listdir(folder):
        if each_file.lower().endswith('.wav') and each_file[5] in orders:
            add_file(each_file)
elif some_items:
    for each_file in os.listdir(folder):
        if each_file.lower().endswith('.wav') and each_file[11] in items:
            add_file(each_file)

make_cd_pdf(images)
make_front_pdf(images)
make_back_pdf(images)