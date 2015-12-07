"""
Prints CD, front and back labels for a set of wave files and cover images.
(c) Ameryn Media LLC, 2015. All rights reserved.
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
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.easyid3 import EasyID3
import logging
from collections import namedtuple
import multiprocessing
import shutil

WHOLE_FOLDER = True
SOME_ORDERS = False
SOME_ITEMS = False
ORDERS_INPUT = ['02000']
ITEMS_INPUT = ['02000-00001']
AUDIO_FOLDER = 'D:/00 Recorded/trackt/'
IMAGES_FOLDER = 'Q:/Cover pictures/'
THUMBS_FOLDER = 'Q:/Cover pictures/CURRENT thumbs/'
DIGITAL_FOLDER = 'D:/00 Recorded/mp3/'
PDF_FOLDER = 'C:/Sextus share/'
DB_PATH = 'C:/Sextus share/items.csv'
LOG_LEVEL = logging.INFO
DIGITAL_FORMATS = ['mp3', 'flac']
FONT_LOCATION = 'C:/Users/Alex/Google Drive/Ameryn/Automation/Scripts/garamond8.ttf'
WATERMARK_LOCATION = 'Q:/Images/ameryn-logo-watermark-2.jpg'
LAYOUT_DEBUG = False
DROPBOX_FOLDER = 'C:/Users/Alex/Dropbox/'
DROPBOX_MOVE = True
JUST_ADD_TAGS = False # Only std supported atm
POOL_PROCESSING = True
INCLUDE_SERIAL_IN_DIGITAL_FILENAME = False

Track = namedtuple('Track', ['num', 'title', 'duration'])

class Item(object):
    def __init__(self, input_name):
        self.filename = input_name
        self.name = os.path.splitext(input_name)[0].split('_clean')[0].split('_tracked')[0]
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
                    for digital_format in DIGITAL_FORMATS:
                        if digital_format in self.format:
                            self.digital_ext = digital_format
                            break
                    else:
                        self.digital_ext = None
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
                    self.compilation_counter = None
                    self.compilation_cd_counter = None
                    self.compilation_cds = 0
                    self.image_counter = 0
                    # Deluxe / 45 stuff
                    if 'std' not in self.option:
                        tracks = []
                        for track_num in range(1, 36):
                            if row[10 + track_num]:
                                tracks.append(row[10 + track_num])
                            else:
                                break
                        else:
                            if not self.side: logging.warning('Careful! 30+ tracks for Deluxe item {0}.'.format(self.name))
                        # Read track times from audio file
                        self.cues = split.read_markers(self.path)
                        if not self.cues:
                            raise Exception('Error! No markers found in audio for Deluxe item {0}'.format(self.name))
                        if not tracks:
                            logging.info('No tracks found in db for Deluxe item {0}.'.format(self.name))
                            for cue_num in range(1, len(self.cues)):
                                tracks.append('Track {0}'.format(cue_num))                        
                        if self.side is '1':
                            tracks = tracks[:self.split_point]
                        elif self.side is '2':
                            tracks = tracks[self.split_point:]                        
                        if len(tracks) is not len(self.cues) - 1:
                            raise Exception('Error! Item {0} expected {1} tracks, found {2} in audio file.'.format(
                                self.name, len(tracks), len(self.cues) - 1))
                        # Set file, track durations
                        self.duration = self.cues[-1] / 44100 # seconds
                        for i in range(1, len(self.cues)):
                            duration = self.cues[i] - self.cues[i - 1]
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
    for order in set([item.order for item in item_list]):
        order_items = [item for item in item_list if order in item.order]
        compilation_counter = 0
        compilation_duration = 0
        compilation_cd_duration = 0
        compilation_cd_counter = 0
        compilation_image = None
        for item in [item for item in order_items if '45' in item.media_type]:
            if not compilation_image:
                compilation_image = item.image
            else:
                item.image = compilation_image
                item.image_path = os.path.join(IMAGES_FOLDER, item.image) + '.jpg'
            compilation_cd_counter = 1
            compilation_counter += 1
            m, s = divmod(item.duration, 60)
            logging.info('Woohoo! {0} is single #{1} for order {2}! (Length: {3}:{4})'.format(item.name, compilation_counter, item.order, str(m), str(s).zfill(2)))
            compilation_cd_duration += item.duration
            compilation_duration += item.duration
            if compilation_cd_duration > 4700:
                compilation_cd_duration = item.duration
                compilation_cd_counter += 1
            item.compilation_cd_counter = compilation_cd_counter
            m, s = divmod(compilation_cd_duration, 60)
            logging.info('Current compilation duration: {0}:{1} (CD #{2}!)'.format(str(m), str(s).zfill(2), item.compilation_cd_counter))
            item.compilation_counter = compilation_counter
            item.image_counter = item.compilation_cd_counter
        for item in [item for item in order_items if '45' in item.media_type]:
            item.compilation_cds = compilation_duration/4700 + 1


def add_image_counters(item_list):
    """ Add a counter to items using the same image on a CD. """
    for image in set([item.image for item in item_list]):
        image_items = [item for item in item_list if image in item.image]
        image_items_nocomps = [item for item in image_items if not item.compilation_counter]
        if len(image_items_nocomps) > 1:
            for image_counter, item in enumerate(image_items_nocomps):
                item.image_counter = image_counter + item.compilation_cds + 1
                logging.info('Yay! {0} is image #{1}!'.format(item.name, item.image_counter))

def make_thumb(item):
    if item.thumb in os.listdir(THUMBS_FOLDER): return
    im = Image.open(item.image_path)
    im.thumbnail((600, 600))
    im.save(item.thumb_path, 'JPEG')

def export_digital(item):
    """ Export and/or split digital files for an item (parallelized) """
    logging.info('{0} -> {1}'.format(item.name, DIGITAL_FOLDER))
    if 'std' in item.option:        
        if JUST_ADD_TAGS:
            if item.digital_ext == 'mp3':
                mutagen_audio = EasyID3(item.digital_file_path)    
            elif item.digital_ext == 'flac':
                mutagen_audio = FLAC(item.digital_file_path)
            else:
                raise Exception('Format {0} not recognized for item {1}.'.format(item.digital_ext, item.name))
            mutagen_audio['title'] = item.album
            mutagen_audio['artist'] = item.artist
            mutagen_audio['albumartist'] = item.artist
            mutagen_audio['album'] = item.album
            mutagen_audio.save()
        else:
            # Export audio file
            digital_file = AudioSegment.from_wav(item.path)
            digital_file.export(out_f=item.digital_file_path, format=item.digital_ext, bitrate='192k', tags={
                'title':(item.album or item.artist), 'artist':item.artist, 'albumartist':item.artist, 'album':(item.album or item.artist)})
        # Add cover art
        if item.thumb and (item.digital_ext == 'mp3'):
            mutagen_audio = MP3(item.digital_file_path, ID3=ID3)
            try:
                # Add ID3 tag if it doesn't exist
                mutagen_audio.add_tags()
            except error:
                pass
            mutagen_audio.tags.add(
                APIC(
                    encoding=3, # 3 is for utf-8
                    mime='image/jpeg', # image/jpeg or image/png
                    type=3, # 3 is for the cover image
                    desc=u'Cover',
                    data=open(item.thumb_path, 'rb').read()
                )
            )            
            mutagen_audio.save()
        elif item.thumb and (item.digital_ext == 'flac'):
            mutagen_audio = File(item.digital_file_path)
            flac_image = Picture()
            flac_image.type = 3
            mime = 'image/jpeg'
            flac_image.desc = 'Cover'
            with open(item.thumb_path, 'rb') as f:
                flac_image.data = f.read()
            mutagen_audio.add_picture(flac_image)
            mutagen_audio.save()
        else:
            logging.warning('No cover found for item {0}'.format(item.name))
        if JUST_ADD_TAGS:
            os.rename(item.digital_file_path, item.digital_rename_path)
    # Deluxe / 45
    else:        
        split.split_item(item, DIGITAL_FOLDER, DROPBOX_MOVE)
    # Move original wave to mp3 folder, so we don't see it in the to-burn list
    shutil.move(item.path, os.path.join(DIGITAL_FOLDER, item.filename))

def make_digital_files(item_list):    
    # Create digital file list
    digital_file_list = [item for item in item_list if item.digital_ext]
    if not digital_file_list:
        logging.info('No digital files to make.')
        return
    for item in digital_file_list:
        item.thumb = item.image + '_600x600.jpg'
        item.thumb_path = os.path.join(THUMBS_FOLDER, item.thumb)
        # Build track filename
        if item.artist and item.album:
            item.digital_file_name = '{0} - {1}'.format(item.artist, item.album)
        elif item.artist or item.album:
            item.digital_file_name = item.artist or item.album
        else:
            item.digital_file_name = 'Untitled - {0}'.format(item.name)
        item.digital_file_name = ''.join([c for c in item.digital_file_name if c.isalpha() or c.isdigit() or c in "'- ._()!@#$%^&*"]).rstrip('. ')
        if INCLUDE_SERIAL_IN_DIGITAL_FILENAME:
            item.digital_file_name = '{0} - {1}'.format(item.serial, item.digital_file_name)
        if JUST_ADD_TAGS:
            item.digital_rename_path = os.path.join(DIGITAL_FOLDER, item.digital_file_name) + '.' + item.digital_ext
            item.digital_file_path = item.path
        else:
            if DROPBOX_MOVE:
                item.dropbox_order_folder = os.path.join(DROPBOX_FOLDER, item.order.lstrip('0'))
                if not os.path.exists(item.dropbox_order_folder): os.makedirs(item.dropbox_order_folder)
                item.digital_file_path = os.path.join(item.dropbox_order_folder, item.digital_file_name) + '.' + item.digital_ext
            else:
                item.digital_file_path = os.path.join(DIGITAL_FOLDER, item.digital_file_name) + '.' + item.digital_ext
    # Add suffixes for identically-named audio files
    if not JUST_ADD_TAGS:
        for i, item in enumerate([item for item in digital_file_list if sum(1 for each_item in digital_file_list if each_item.digital_file_name == item.digital_file_name) > 1]):
            item.digital_file_name += ' - {0}'.format(str(i + 1))
            if DROPBOX_MOVE:
                item.digital_file_path = os.path.join(item.dropbox_order_folder, item.digital_file_name) + '.' + item.digital_ext
            else:
                item.digital_file_path = os.path.join(DIGITAL_FOLDER, item.digital_file_name) + '.' + item.digital_ext
    logging.info('digital_file_list: ({0}): {1}'.format(len(digital_file_list), [item.name for item in digital_file_list]))
    if POOL_PROCESSING:
        pool = multiprocessing.Pool(multiprocessing.cpu_count() - 1)
        pool.map(make_thumb, digital_file_list)
        pool.map(export_digital, digital_file_list)
    else:
        for each_file in digital_file_list:
            make_thumb(each_file)
            export_digital(each_file)

def make_cd_pdf(item_list):
    # Create CD label list
    cd_label_list = []
    for item in item_list:
        if item.compilation_counter:
            # Compilation CDs: Add one cover for the first item of each CD
            for each_item in cd_label_list:
                if each_item.order == item.order and each_item.compilation_cd_counter == item.compilation_cd_counter:
                    break
            else:
                cd_label_list.extend([item] * item.copies)
        if 'cd' in item.format and not item.compilation_counter:
            cd_label_list.extend([item] * item.copies)
    if not cd_label_list:
        logging.warning('No CD labels to print.')
        return
    logging.info('cd_label_list: ({0}): {1}'.format(len(cd_label_list), [item.name for item in cd_label_list]))

    # Draw CD labels
    c = canvas.Canvas(os.path.join(PDF_FOLDER, 'cd-labels.pdf'), pagesize=(130 * mm, 225 * mm))
    width, height = (130 * mm, 225 * mm)
    pdfmetrics.registerFont(TTFont('Garamond', FONT_LOCATION))
    for item in cd_label_list:
        # Clipping
        path = c.beginPath()
        path.circle(65 * mm, 105 * mm, 60 * mm)
        path.circle(65 * mm, 105 * mm, 11 * mm)
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
        # Draw label label
        c.setFont('Helvetica', 11)
        if item.copies > 1:
            label1 = '{0} - Copies: {1}'.format(item.name, item.copies)
        else:
            label1 = item.name
        if 'std' in item.option:
            label2 = 'Standard transfer'
        elif item.compilation_counter:
            label2 = 'Singles compilation'
        else:
            if item.artist and item.album:
                label2 = item.artist + ' - ' + item.album
            elif item.artist or item.album:
                label2 = item.artist or item.album
            else:
                label2 = 'Untitled'
        if item.image_counter:
            label2 += ' (Disc {0})'.format(item.image_counter)
        c.drawCentredString(width / 2.0, 0.45*inch + label_adjustment, label1)
        c.drawCentredString(width / 2.0, 0.25*inch + label_adjustment, label2)

    # Create front cover list
    front_cover_list = []
    for item in item_list:
        if item.compilation_counter:
            # Compilation CDs: Add one cover for the first item of each CD
            for each_item in front_cover_list:
                if each_item.order == item.order and each_item.compilation_cd_counter == item.compilation_cd_counter:
                    break
            else:
                front_cover_list.extend([item] * item.copies)
        elif 'cd' in item.format and not item.compilation_counter > 1:
            front_cover_list.extend([item] * item.copies)
    if not front_cover_list:
        logging.warning('No front covers to print.')
        return
    logging.info('front_cover_list: ({0}): {1}'.format(len(front_cover_list), [item.image for item in front_cover_list]))
    logging.info('Front cover pages: {0}'.format(int(math.ceil(float(len(front_cover_list)) / 2))))

    # Reorder front cover list for better arrangement (1/5, 2/6, 3/7, 4/), etc.
    front_cover_list_reordered = []
    for i in range(len(front_cover_list) - len(front_cover_list)/2):
        try:
            front_cover_list_reordered.extend([front_cover_list[i], front_cover_list[i + len(front_cover_list) - len(front_cover_list)/2]])
        except IndexError:
            front_cover_list_reordered.append(front_cover_list[i])
    front_cover_iter = iter(front_cover_list_reordered)

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
        logging.info('Processing back cover for item {0}'.format(item.name))
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
        if item.compilation_counter:
            line1 = 'Singles Compilation'
            spine = line1
        else:
            if item.artist and item.album:
                line1 = item.artist
                line2 = item.album
                spine = line1 + ' - ' + line2
            elif item.artist or item.album:
                line1 = item.artist or item.album
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
            styles.add(ParagraphStyle(name='track_title', fontName='Garamond', fontSize=size, leading=max(size + padding, 10)))
            # Compile track info for 45 compilations
            if item.compilation_cd_counter:
                compilation_tracks = []
                for each_item in [each_item for each_item in item_list if each_item.compilation_cd_counter == item.compilation_cd_counter and each_item.order == item.order]:
                    for track in each_item.tracks:
                        track = track._replace(title = '{0} - {1}'.format(each_item.artist, track.title))
                        compilation_tracks.append(track)
                for track_num, track in enumerate(compilation_tracks):
                    table_data.append((str(track_num + 1) + '.', Paragraph(track.title, styles['track_title']), track.duration))
            else:                
                for track in item.tracks:
                    table_data.append((str(track.num) + '.', Paragraph(track.title, styles['track_title']), track.duration))
            # Draw track listing
            table = Table(table_data, colWidths=[6 * mm, 100 * mm, 10 * mm])
            table.setStyle(TableStyle([
                                    ('FONT', (0,0), (-1,-1), 'Garamond', size),
                                    ('TEXTCOLOR', (0,0), (0,-1), colors.gray),
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
        # Draw label label
        c.setFont('Helvetica', 11)
        if LAYOUT_DEBUG:
            label1 = '{0} - font_size: {1} | padding: {2}'.format(item.name, size, padding)
        elif item.copies > 1:
            label1 = '{0} - Copies: {1}'.format(item.name, item.copies)
        else:
            label1 = item.name
        c.drawCentredString(width / 2.0, 0.55*inch + max(0, label_adjustment - 0.2*inch), label1)
        c.drawCentredString(width / 2.0, 0.35*inch + max(0, label_adjustment - 0.2*inch), spine)

    # Create back cover list
    back_cover_list = []
    for item in item_list:        
        if item.compilation_counter:
            # Compilation CDs: Add one cover for the first item of each CD
            for each_item in back_cover_list:
                if each_item.order == item.order and each_item.compilation_cd_counter == item.compilation_cd_counter:
                    break
            else:
                back_cover_list.extend([item] * item.copies)
        elif 'cd' in item.format and 'std' not in item.option:
            back_cover_list.extend([item] * item.copies)
    if not back_cover_list:
        logging.warning('No back covers to print.')
        return
    logging.info('back_cover_list: ({0}): {1}'.format(len(back_cover_list), [item.image for item in back_cover_list]))
    logging.info('Back cover pages: {0}'.format(int(math.ceil(float(len(back_cover_list)) / 2))))

    # Reorder back cover list for better arrangement (1/5, 2/6, 3/7, 4/), etc.
    back_cover_list_reordered = []
    for i in range(len(back_cover_list) - len(back_cover_list)/2):
        try:
            back_cover_list_reordered.extend([back_cover_list[i], back_cover_list[i + len(back_cover_list) - len(back_cover_list)/2]])
        except IndexError:
            back_cover_list_reordered.append(back_cover_list[i])
    back_cover_iter = iter(back_cover_list_reordered)

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
    if JUST_ADD_TAGS:
        item_list = [Item(each_file) for each_file in os.listdir(AUDIO_FOLDER) if os.path.splitext(each_file.lower())[1][1:] in DIGITAL_FORMATS]
    elif WHOLE_FOLDER:
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

    #make_digital_files(item_list)
    make_cd_pdf(item_list)
    make_front_pdf(item_list)
    make_back_pdf(item_list)