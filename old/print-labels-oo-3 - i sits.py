"""
Prints CD, front and back labels for a set of wave files and cover images.
(c) Ameryn Media, 2015. All rights reserved.
"""

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
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
import logging
from collections import namedtuple

WHOLE_FOLDER = True
SOME_ORDERS = False
SOME_ITEMS = False
DIGITAL_ENABLED = False
ORDERS_INPUT = ['02000']
ITEMS_INPUT = ['02000-00001']
AUDIO_FOLDER = 'D:/00 Recorded/trackt'
IMAGES_FOLDER = 'Q:/Cover pictures/'
THUMBS_FOLDER = 'Q:/Cover pictures/CURRENT thumbs/'
MP3_FOLDER = 'D:/00 Recorded/mp3'
PDF_FOLDER = 'C:/Sextus share/'
DB_PATH = 'C:/Sextus share/items.csv'
LOG_LEVEL = logging.WARNING
DIGITAL_FORMATS = ['mp3', 'flac']
FONT_LOCATION = 'C:/Users/Alex/Google Drive/Ameryn/Automation/Scripts/garamond8.ttf'
WATERMARK_LOCATION = 'Q:/Images/ameryn-logo-watermark-2.jpg'


class Item(object):
    def __init__(self, input_name):
        self.filename = input_name
        self.name = input_name.split('_clean')[0]
        self.path = os.path.join(AUDIO_FOLDER, input_name)
        self.serial = self.name.split('_')[0]
        self.order = input_name[:5]
        self.copies = 1
        self.get_metadata()

    def get_metadata(self):
        """ Read metadata from csv db """
        with open(DB_PATH, 'r') as items:
            rows = csv.reader(items)
            for row in rows:
                if row[0] == self.serial:
                    logging.debug('Item {0} found in {1}.'.format(self.serial, DB_PATH))
                    self.artist = row[1]
                    self.album = row[2]
                    self.media_type = row[3].lower()
                    self.option = row[4].lower()
                    self.format = row[5].lower()
                    self.image = row[6] if row[6] else self.serial
                    self.image_path = os.path.join(IMAGES_FOLDER, self.image) + '.jpg'
                    self.copies = int(row[7]) if row[7] else 1
                    self.date_received = row[8]
                    self.customer_notes = row[9]
                    self.private_notes = row[10]                    
                    self.split_point = int(self.private_notes[1:3]) if self.private_notes and self.private_notes[0] == '_' else None
                    if self.split_point:
                        if self.name[-2] is not '_':
                            raise Exception('Error! Split file expected for {0}'.format(self.name))
                        self.side = self.name[-1]
                    else:
                        self.side = None
                    self.tracks = []
                    if 'std' not in self.option:
                        tracks = []
                        for track_num in range(1, 31):
                            if row[10 + track_num]:
                                tracks.append(row[10 + track_num])
                            else:
                                break
                        else:
                            logging.warning('No tracks found in db for Deluxe item {0}.'.format(self.name))
                        # Read track times from audio file
                        cues = split.read_markers(self.path)
                        if not cues:
                            raise Exception('Error! No markers found in audio for Deluxe item {0}'.format(self.name))
                        if not tracks:
                            for cue_num in range(1, len(cues)):
                                tracks.append('Track {0}'.format(cue_num))                        
                        if self.side is '1':
                            tracks = tracks[:self.split_point]
                        elif self.side is '2':
                            tracks = tracks[self.split_point:]                        
                        if len(tracks) is not len(cues) - 1:
                            raise Exception('Error! Item {0} expected {1} tracks, found {2} in audio file.'.format(self.name, len(tracks), len(cues) - 1))
                        Track = namedtuple('Track', ['num', 'title', 'duration'])
                        for i in range(1, len(cues)):
                            duration = cues[i] - cues[i - 1]
                            m, s = divmod(duration / 44100, 60)
                            duration = '{0}:{1}'.format(str(m), str(s).zfill(2))
                            self.tracks.append(Track(num=i, title=tracks[i - 1], duration=duration))
                    return                     
            else:
                 logging.warning('Row {0} not found in {1}.'.format(self.serial, DB_PATH))

    def print_tracks(self):
        print '{0} tracks:'.format(self.name)
        for track in self.tracks:
            print '{0} - {1} - {2}'.format(track.num, track.title, track.duration)      

def add_compilation_counters(item_list):
    """ Add a counter to singles (45s) to be combined on a CD. """
    orders = set([item.order for item in item_list])
    for order in orders:
        order_items = [item for item in item_list if order in item.order]
        order_singles = [item for item in order_items if '45' in item.media_type]
        if len(order_singles) > 1:
            for compilation_counter, item in enumerate(order_singles):
                item.compilation_counter = compilation_counter + 1
                logging.info('Woohoo! {0} is single #{1} for order {2}!'.format(item.name, item.compilation_counter, item.order))
        else:
            for item in order_items:
                item.compilation_counter = None

def add_image_counters(item_list):
    """ Add a counter to items using the same image on a CD. """
    images = set([item.image for item in item_list])
    for image in images:
        image_items = [item for item in item_list if image in item.image]
        image_items_nocomps = [item for item in image_items if not item.compilation_counter > 1]
        if len(image_items_nocomps) > 1:
            for image_counter, item in enumerate(image_items_nocomps):
                item.image_counter = image_counter + 1
                logging.info('Yay! {0} is image #{1}!'.format(item.name, item.image_counter))
        else:
            for item in image_items:
                item.image_counter = None

def make_cd_pdf(item_list):
    # Create CD label list
    cd_label_list = []
    for item in item_list:
        if 'cd' in item.format and not item.compilation_counter > 1:
            cd_label_list.extend([item] * item.copies)
    if not front_cover_list:
        logging.warning('No CD labels to print.')
        return
    print 'cd_label_list: ({0}): {1}'.format(len(cd_label_list), [item.image for item in cd_label_list])

    # Draw CD labels
    c = canvas.Canvas(os.path.join(PDF_FOLDER, 'cd-labels.pdf'), pagesize=(130 * mm, 225 * mm))
    width, height = (130 * mm, 225 * mm)
    pdfmetrics.registerFont(TTFont('Garamond', FONT_LOCATION))
    for item in cd_label_list:
        # Clipping
        path = c.beginPath()
        path.circle(65 * mm, 105 * mm, 60 * mm)
        path.circle(65 * mm, 105 * mm, 10 * mm)
        c.clipPath(path, stroke = 1, fill = 0)
        # Draw CD image
        c.drawImage(item.image_path, 5 * mm, 45 * mm, width=120 * mm, height=120 * mm)
        # Draw image counter on label (1, 2, etc.)
        if item.image_counter:
            c.setFont('Garamond', 24)
            c.drawString(62.5 * mm, 50 * mm, str(item.image_counter))
        c.showPage()
    c.save()

def make_front_pdf(item_list):
    def add_front_cover(position):
        item = front_cover_iter.next()
        # Image positioning
        if position == 'top':
            image_adjustment = 4.8 * inch
            label_adjustment = 10.2 * inch
        elif position == 'bottom':
            image_adjustment = 0
            label_adjustment = 0
        # Draw front cover image
        c.drawImage(item.image_path, 1.85 * inch, 0.7*inch + image_adjustment, width=4.8 * inch, height=4.8 * inch)
        c.rect(1.85 * inch, 0.7*inch + image_adjustment, 4.8 * inch , 4.8 * inch, fill=0)
        # Draw image counter on label (1, 2, etc.)
        if item.image_counter:
            c.setFont('Garamond', 24)
            c.drawString(4.3 * inch, 1*inch + image_adjustment, str(item.image_counter))
        # Draw image label
        c.setFont('Helvetica', 12)
        c.drawString(3.8 * inch, 0.3*inch + label_adjustment, item.name)

    # Create front cover list
    front_cover_list = []
    for item in item_list:
        if 'cd' in item.format and not item.compilation_counter > 1:
            front_cover_list.extend([item] * item.copies)
    if not front_cover_list:
        logging.warning('No front covers to print.')
        return
    logging.info('front_cover_list: ({0}): {1}'.format(len(front_cover_list), [item.image for item in front_cover_list]))
    logging.info('Front cover pages:', int(math.ceil(float(len(front_cover_list)) / 2)))
    front_cover_iter = iter(front_cover_list)

    # Draw front covers
    c = canvas.Canvas(os.path.join(PDF_FOLDER, 'covers-front.pdf'), pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', FONT_LOCATION))
    c.setLineWidth(0.5)
    for pair in range(int(math.ceil(float(len(front_cover_list)) / 2))):
        add_front_cover('top')
        try:
            add_front_cover('bottom')
        except StopIteration:
            pass
        c.showPage()
    c.save()

def make_back_pdf(item_list):
    def add_back_cover(position):
        item = back_cover_iter.next()
        # Image positioning
        if position == 'top':
            image_adjustment = 118 * mm
            label_adjustment = 10.2 * inch
        elif position == 'bottom':
            image_adjustment = 0
            label_adjustment = 0
        # Draw Ameryn logo watermark
        c.drawImage(WATERMARK_LOCATION, 157 * mm, 25*mm + image_adjustment, width=16 * mm, height=11 * mm)
        # Add artist/album titles
        line2 = ''
        if item.artist and item.album:
            line1 = item.artist
            line2 = item.album
            spine = line1 + ' - ' + line2
        elif item.artist:
            line1 = item.artist
            spine = line1
        elif item.album:
            line1 = item.album
            spine = line1
        else:
            line1 = 'Untitled'
            spine = line1
        # Add disc # for multi-disc sets
        if item.image_counter:
            spine += ' (Disc {0})'.format(item.image_counter)
            if line2:
                line2 += ' (Disc {0})'.format(item.image_counter)
            else:
                line2 = 'Disc {0}'.format(item.image_counter)
        # Line 1
        for size in [18, 16, 14, 12, 11, 10]:
            if pdfmetrics.stringWidth(line1, 'Garamond', size) < 125 * mm:
                break
        else:
            logging.warning('Line 1 overflow for item {0}!'.format(item.name))
            line1 = line1[:70] + '...'
        c.setFont('Garamond', size)
        c.drawString(48 * mm, 125*mm + image_adjustment, line1)
        # Line 2
        if line2:
            for size in [14, 12, 11, 10, 9]:
                if pdfmetrics.stringWidth(line2, 'Garamond', size) < 125 * mm:
                    break
            else:
                logging.warning('Line 2 overflow for item {0}!'.format(item.name))
                line2 = line2[:85] + '...'
            c.setFont('Garamond', size)
            c.drawString(48 * mm, 118*mm + image_adjustment, line2)
        # Horizontal divider
        c.setLineWidth(2)
        c.line(48 * mm, 112*mm + image_adjustment, 168 * mm, 112*mm + image_adjustment)
        # Set spine label font size
        c.saveState()
        c.rotate(90)
        for size in [9, 8, 7]:
            if pdfmetrics.stringWidth(spine, 'Garamond', size) < 116 * mm:
                break
        else:
            logging.warning('Spine label overflow for item {0}!'.format(item.name))
            spine = spine[:100] + '...'
        c.setFont('Garamond', size)
        # Left spine label
        x = (118*mm - pdfmetrics.stringWidth(spine, 'Garamond', size))/2 + 21.7*mm + image_adjustment
        y = -37.3 * mm
        c.drawString(x, y, spine)
        # Right spine label
        c.rotate(180)
        x = (118*mm - pdfmetrics.stringWidth(spine, 'Garamond', size))/2 - 139.7*mm - image_adjustment
        y = 178.7 * mm
        c.drawString(x, y, spine)
        c.restoreState()
        # Try to fit various table font sizes and paddings
        for size, padding in [(11,2), (11,1), (10,2), (10,1), (9,1), (9,0), (8,0), (8,-1), (7,-1), (7,-2), (6, -1), (6,-2)]:
            # Add table data
            table_data = []
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(name='track_title', fontName='Garamond', fontSize=size))
            for track in item.tracks:
                table_data.append((track.num, Paragraph(track.title, styles['track_title']), track.duration))
            # Draw track listing
            table = Table(table_data, colWidths=[6 * mm, 100 * mm, 10 * mm])
            table.setStyle(TableStyle([
                                    ('FONT', (0,0), (-1,-1), 'Garamond', size),
                                    ('TOPPADDING', (0,0), (-1,-1), padding),
                                    ('BOTTOMPADDING', (0,0), (-1,-1), padding),
                                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                                    ]))
            w, h = table.wrap(width, height)
            if h < 83 * mm:
                break
        else:
            logging.warning('Tracks overflow for item {0}!'.format(item.name))
        #table.wrapOn(c, width, height)
        table.drawOn(c, 49 * mm, 108*mm - h + image_adjustment)
        # Draw crop lines
        c.setLineWidth(0.5)
        c.rect(33 * mm, 21.7*mm + image_adjustment, 150 * mm , 118 * mm, fill=0) 
        c.line(39 * mm, 21.7*mm + image_adjustment, 39 * mm, 139.7*mm + image_adjustment)
        c.line(177 * mm, 21.7*mm + image_adjustment, 177 * mm, 139.7*mm + image_adjustment)
        # Draw image label
        c.setFont('Helvetica', 12)
        label = '{0} | font_size: {1} | padding: {2}'.format(item.name, size, padding)
        c.drawString(3.8 * inch, 0.3*inch + label_adjustment, label)

    # Create back cover list
    back_cover_list = []
    for item in item_list:
        if 'cd' in item.format and 'std' not in item.option and not item.compilation_counter > 1:
            back_cover_list.extend([item] * item.copies)
    if not back_cover_list:
        logging.warning('No back covers to print.')
        return
    logging.info('back_cover_list: ({0}): {1}'.format(len(back_cover_list), [item.image for item in back_cover_list]))
    logging.info('Back cover pages: {0}'.format(int(math.ceil(float(len(back_cover_list)) / 2))))
    back_cover_iter = iter(back_cover_list)

    # Draw back covers
    c = canvas.Canvas(os.path.join(PDF_FOLDER, 'covers-back.pdf'), pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', FONT_LOCATION))
    for pair in range(int(math.ceil(float(len(back_cover_list)) / 2))):
        add_back_cover('top')
        try:
            add_back_cover('bottom')
        except StopIteration:
            break
        c.showPage()
    c.save()

if __name__ == '__main__':
    logging.basicConfig(level=LOG_LEVEL)
    input_list = []
    if WHOLE_FOLDER:
        item_list = [Item(each_file) for each_file in os.listdir(AUDIO_FOLDER) if each_file.lower().endswith('.wav')]
    elif SOME_ORDERS:
        item_list = [Item(each_file) for each_file in os.listdir(AUDIO_FOLDER) if (each_file.lower().endswith('.wav') and 
                each_file[:5] in os.listdir(AUDIO_FOLDER))]
    elif SOME_ITEMS:
        item_list = [Item(each_file) for each_file in os.listdir(AUDIO_FOLDER) if (each_file.lower().endswith('.wav') and 
                each_file[:11] in ITEMS_INPUT)]
    add_compilation_counters(item_list)
    add_image_counters(item_list)

    logging.info('Compilation items: {0}'.format([item.name for item in item_list if item.compilation_counter]))
    logging.info('Unique images: {0}'.format(len(set([item.image for item in item_list]))))
    logging.info('item_list ({0}): {1}'.format(len(item_list), [item.name for item in item_list]))
    
    '''
    print
    print '{0} artist: {1}'.format(item_list[0].name, item_list[0].artist)
    item_list[0].print_tracks()
    print
    '''

    #make_cd_pdf(item_list)
    #make_front_pdf(item_list)
    make_back_pdf(item_list)

    #print [item.compilation_counter for item in item_list if '02063' in item.order][0]