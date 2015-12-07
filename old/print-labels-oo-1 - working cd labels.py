"""
Prints CD, front and back labels for a set of wave files and cover images.
(c) Ameryn Media, 2015. All rights reserved.
"""

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
import logging

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


class Item(object):
    class Track(object):
        def __init__(self, track_num, track_name):
            self.num = track_num
            self.title = track_name
            self.duration = '3:00'

    def __init__(self, input_name):
        self.filename = input_name
        self.name = input_name.split('_clean')[0]
        self.path = os.path.join(AUDIO_FOLDER, input_name)
        self.serial = self.name.split('_')[0]
        self.order = input_name[:5]
        self.copies = 1
        self.get_metadata()
        self.read_tracks()

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
                    if 'del' in self.option:
                        for track_num in range(30):
                            if row[11 + track_num]:
                                self.tracks.append(self.Track(track_num + 1, row[11 + track_num]))
                            else:
                                break
                        else:
                            logging.warning('No tracks found in db for Deluxe item {0}.'.format(self.name))
                    break                     
            else:
                 logging.warning('Row {0} not found in {1}.'.format(self.serial, DB_PATH))

    def print_tracks(self):
        print '{0} tracks:'.format(self.name)
        for track in self.tracks:
            print '{0} - {1} - {2}'.format(track.num, track.title, track.duration)

    def read_tracks(self):
        """ Read track times from audio file """
        pass

def add_compilation_counters(item_list):
    """ Add a counter to singles (45s) to be combined on a CD. """
    orders = set([item.order for item in item_list])
    for order in orders:
        order_items = [item for item in item_list if order in item.order]
        order_singles = [item for item in order_items if '45' in item.media_type]
        if len(order_singles) > 1:
            for compilation_counter, item in enumerate(order_singles):
                item.compilation_counter = compilation_counter + 1
                logging.info('Woohoo! {0} is single #{1}!'.format(item.name, item.compilation_counter))
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
    cd_label_list = []
    for item in item_list:
        if 'cd' in item.format and not item.compilation_counter > 1:
            cd_label_list.extend([item] * item.copies)
    print 'cd_label_list: ({0}): {1}'.format(len(cd_label_list), [item.image for item in cd_label_list])
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

    print 'Compilation items:', [item.name for item in item_list if item.compilation_counter]
    print 'Unique images:', len(set([item.image for item in item_list]))
    print 'item_list ({0}): {1}'.format(len(item_list), [item.name for item in item_list])
    print
    print '{0} artist: {1}'.format(item_list[0].name, item_list[0].artist)
    item_list[0].print_tracks()

    make_cd_pdf(item_list)
    #make_front_pdf(item_list)
    #make_back_pdf(item_list)