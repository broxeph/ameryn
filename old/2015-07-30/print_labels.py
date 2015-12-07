"""
Prints CD, front and back labels for a set of wave files and cover images.
(c) Ameryn Media LLC, 2015. All rights reserved.
"""

import math
import os
import datetime
import csv
import sys
import string
import logging
import multiprocessing
import shutil
from copy import deepcopy

from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics  
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch, mm
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from pydub import AudioSegment
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TOA, TP1, TP2, TP4, TAL, APIC, error
from mutagen import File
from mutagen.flac import FLAC, Picture

import dbox
import utils
import config


def make_thumb(item):
    if not item.image or item.thumb in os.listdir(config.thumbs_folder):
        return
    im = Image.open(item.image_path)
    im.thumbnail((600, 600))
    im.save(item.thumb_path, 'JPEG')

def export_digital(item):
    """ Export and/or split digital files for an item (parallelized) """
    logging.info('{0} -> {1}'.format(item.name, digital_folder))
    if 'std' in item.option:        
        if just_add_tags:
            if item.digital_ext == 'mp3':
                mutagen_audio = ID3(item.digital_file_path)
                mutagen_audio.add(TIT2(encoding=3, text=item.album))
                mutagen_audio.add(TOA(encoding=3, text=item.artist))
                mutagen_audio.add(TP1(encoding=3, text=item.artist))
                mutagen_audio.add(TP2(encoding=3, text=item.artist))
                mutagen_audio.add(TP4(encoding=3, text=item.artist))
                mutagen_audio.add(TAL(encoding=3, text=item.album))
                mutagen_audio.save(v2_version=3)
            elif item.digital_ext == 'flac':
                mutagen_audio = FLAC(item.digital_file_path)
                mutagen_audio['title'] = item.album
                mutagen_audio['artist'] = item.artist
                mutagen_audio['albumartist'] = item.artist
                mutagen_audio['album'] = item.album
                mutagen_audio.save()
            else:
                raise Exception('Format {0} not recognized for item {1} tags.'.format(item.digital_ext, item.name))
        else:
            # Export audio file
            digital_file = AudioSegment.from_wav(item.path)
            digital_file.export(out_f=item.digital_file_path, format=item.digital_ext, bitrate=item.bitrate, tags={
                'title':(item.album or item.artist), 'artist':item.artist, 'albumartist':item.artist, 'album':(item.album or item.artist)},
                id3v2_version='3')
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
            mutagen_audio.save(v2_version=3)
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
        elif item.image:
            logging.warning('No cover found for item {0}'.format(item.name))
        if just_add_tags:
            os.rename(item.digital_file_path, item.digital_rename_path)
    # Deluxe / 45
    else:        
        split.split_item(item, digital_folder, dropbox_move)

def make_digital_files(item_list):    
    """Create digital file list"""

    # Filter CD items, copied items, split items
    digital_file_list = [each_item for each_item in item_list if each_item.digital_ext and not each_item.copy_counter and not each_item.side]

    if not digital_file_list:
        logging.info('No digital files to make.')
        return
    '''
    for item in digital_file_list:
        # Move original wave to mp3 folder, so we don't see it in the to-burn list
        if not 'cd' in item.format:
            try:
                shutil.move(item.path, os.path.join(digital_folder, item.filename))
                try:
                    shutil.move(os.path.splitext(item.path)[0] + '.pkf', os.path.join(
                        digital_folder, os.path.splitext(item.filename)[0] + '.pkf'))
                except IOError:
                    pass
                item.path = os.path.join(digital_folder, item.filename)
            except IOError:                
                logging.warning('IOError while moving digital file {0}. Close all open instances and try again.'.format(item.name))
                pass
    '''
    for item in digital_file_list:
        if item.image:
            item.thumb = item.image + '_600x600.jpg'
            item.thumb_path = os.path.join(thumbs_folder, item.thumb)
        # Build track filename
        if item.artist and item.album:
            item.digital_file_name = '{0} - {1}'.format(item.artist, item.album)
        elif item.artist or item.album:
            item.digital_file_name = item.artist or item.album
        else:
            item.digital_file_name = 'Untitled - {0}'.format(item.name)
        item.digital_file_name = item.digital_file_name.replace(':', ' -')
        item.digital_file_name = item.digital_file_name.translate(None, '<>:|?*') # Windows allowed filename chars
        item.digital_file_name = item.digital_file_name.translate(string.maketrans('"/\\', '\'--'))
        if include_serial_in_digital_filename:
            item.digital_file_name = '{0} - {1}'.format(item.serial, item.digital_file_name)
        if just_add_tags:
            item.digital_rename_path = os.path.join(digital_folder, item.digital_file_name) + '.' + item.digital_ext
            item.digital_file_path = item.path
        else:
            if dropbox_move:
                item.dropbox_order_folder = os.path.join(dropbox_folder, item.order.lstrip('0'))
                if not os.path.exists(item.dropbox_order_folder): os.makedirs(item.dropbox_order_folder)
                item.digital_file_path = os.path.join(item.dropbox_order_folder, item.digital_file_name) + '.' + item.digital_ext
            else:
                item.digital_file_path = os.path.join(digital_folder, item.digital_file_name) + '.' + item.digital_ext
    # Add suffixes for identically-named audio files
    if not just_add_tags:
        for i, item in enumerate([item for item in digital_file_list if sum( \
            1 for each_item in digital_file_list if each_item.digital_file_name == item.digital_file_name) > 1]):
            item.digital_file_name += ' - {0}'.format(str(i + 1))
            if dropbox_move:
                item.digital_file_path = os.path.join(item.dropbox_order_folder, item.digital_file_name) + '.' + item.digital_ext
            else:
                item.digital_file_path = os.path.join(digital_folder, item.digital_file_name) + '.' + item.digital_ext
    logging.info('digital_file_list: ({0}): {1}'.format(len(digital_file_list), [item.name for item in digital_file_list]))

    # Loop/multiprocess each file
    if pool_processing:
        pool = multiprocessing.Pool(min(multiprocessing.cpu_count() - 1, 5))
        pool.map(make_thumb, digital_file_list)
        pool.map(export_digital, digital_file_list)
    else:
        for each_file in digital_file_list:
            make_thumb(each_file)
            export_digital(each_file)

    # Send Dropbox emails
    digital_orders = set([item.order.lstrip('0') for item in digital_file_list])
    logging.info(' - Digital orders:')
    for each_order in digital_orders:
        logging.info('   - {0}'.format(each_order))
    dbox.send_all(digital_orders)

def make_cd_pdf(item_list):
    """Create CD label pdf"""

    # Filter non-CD items, copied items, split item bases, compilation items after the first for each CD
    cd_label_list = [each_item for each_item in item_list if \
        each_item.compilation_cd_item_counter <= 1 and 'cd' in each_item.format and \
        not (each_item.copies > 1 and not each_item.copy_counter) and \
        not (each_item.long and not each_item.side)]

    if not cd_label_list:
        logging.warning('No CD labels to print.')
        return
    logging.info('cd_label_list: ({0}): {1}'.format(len(cd_label_list), [item.name for item in cd_label_list]))

    # Draw CD labels
    c = canvas.Canvas(os.path.join(pdf_folder, 'cd-labels.pdf'), pagesize=(150 * mm, 320 * mm))
    width, height = (150 * mm, 320 * mm)
    pdfmetrics.registerFont(TTFont('Garamond', font_location))
    for item in cd_label_list:
        # Clipping
        path = c.beginPath()
        path.circle(81 * mm, 113 * mm, 60 * mm)
        path.circle(81 * mm, 113 * mm, 11 * mm)
        c.clipPath(path, stroke = 1, fill = 0)
        # Draw CD image
        if not item.counter_image_path:
            item.counter_image_path = make_cover_image(item)
        c.drawImage(item.counter_image_path, 20 * mm, 52 * mm, width=120 * mm, height=120 * mm)
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
        if not item.counter_image_path:
            item.counter_image_path = make_cover_image(item)
        c.drawImage(item.counter_image_path, 1.85 * inch, 0.7*inch + image_adjustment, width=4.8 * inch, height=4.8 * inch)
        c.rect(1.85 * inch, 0.7*inch + image_adjustment, 4.8 * inch , 4.8 * inch, fill=0)

        # Draw label label
        c.setFont('Helvetica', 11)
        if item.copies > 1:
            label1 = '{0} - Copy {1}/{2}'.format(item.name, item.copy_counter, item.copies)
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
        if item.image_counter and item.compilation_cds != 1:
            label2 += ' (Disc {0})'.format(item.image_counter)
        c.drawCentredString(width / 2.0, 0.45*inch + label_adjustment, label1)
        c.drawCentredString(width / 2.0, 0.25*inch + label_adjustment, label2)

    # Filter non-CD items, copied item bases, split item bases, compilation items after the first for each CD
    front_cover_list = [each_item for each_item in item_list if \
        each_item.compilation_cd_item_counter <= 1 and 'cd' in each_item.format and \
        not (each_item.copies > 1 and not each_item.copy_counter) and \
        not (each_item.long and not each_item.side)]

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
    c = canvas.Canvas(os.path.join(config.pdf_folder, 'covers-front.pdf'), pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', config.font_location))
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
        c.drawImage(config.watermark_location, 157 * mm, 25*mm + image_adjustment, width=16 * mm, height=11 * mm)
        # Add artist/album titles
        line2 = ''
        if item.compilation_counter and item.compilation_items > 1:
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
        if item.image_counter and item.compilation_cds != 1:
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
                # Filter compilation track listing: compilation, same order, not copied
                for each_item in [each_item for each_item in item_list if each_item.compilation_cd_counter == item.compilation_cd_counter and \
                    each_item.order == item.order and not each_item.copy_counter]:        
                    for track in each_item.tracks:
                        if each_item.artist and each_item.album:
                            compilation_track_title = '{0} - {1}'.format(each_item.artist, each_item.album)
                        elif each_item.artist or each_item.album:
                            compilation_track_title = each_item.artist or each_item.album
                        if track.title and each_item.artist or each_item.album:
                            compilation_track_title += ' - {0}'.format(track.title)
                        elif track.title:
                            compilation_track_title = track.title
                        else:
                            compilation_track_title = 'Untitled'
                        track = track._replace(title=compilation_track_title)
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
        if config.layout_debug:
            label1 = '{0} - font_size: {1} | padding: {2}'.format(item.name, size, padding)
        elif item.copies > 1:
            label1 = '{0} - Copy {1}/{2}'.format(item.name, item.copy_counter, item.copies)
        else:
            label1 = item.name
        c.drawCentredString(width / 2.0, 0.55*inch + max(0, label_adjustment - 0.2*inch), label1)
        c.drawCentredString(width / 2.0, 0.35*inch + max(0, label_adjustment - 0.2*inch), spine)

    # Filter non-CD items, std items, copied item bases, split item bases, compilation items after the first for each CD
    back_cover_list = [each_item for each_item in item_list if \
        each_item.compilation_cd_item_counter <= 1 and 'cd' in each_item.format and 'std' not in each_item.option and \
        not (each_item.copies > 1 and not each_item.copy_counter) and \
        not (each_item.long and not each_item.side)]

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
    c = canvas.Canvas(os.path.join(config.pdf_folder, 'covers-back.pdf'), pagesize=letter)
    width, height = letter
    pdfmetrics.registerFont(TTFont('Garamond', config.font_location))
    for pair in range(int(math.ceil(float(len(back_cover_list)) / 2))):
        add_back_cover('top')
        try:
            add_back_cover('bottom')
        except StopIteration:
            break
        c.showPage()
    c.save()

def format_list(item_list):
    """ Tweak the item list to include: split CDs, compilation counters, image counters, copies """

    def list_item_stats():
        print '- - - - - '
        for item in item_list:
            print item.name
            print ' .long:', item.long
            print ' .side:', item.side
            print ' .copies:', item.copies
            print ' .copy_counter:', item.copy_counter
            print ' .image_counter:', item.image_counter
            print ' .compilation_counter:', item.compilation_counter
            print ' .compilation_cds:', item.compilation_cds
            print ' .compilation_cd_counter:', item.compilation_cd_counter
            print ' .compilation_cd_item_counter:', item.compilation_cd_item_counter

    # Split >78m (long) std/trk CDs
    new_items = []
    for item in item_list:
        if item.long:
            item1 = deepcopy(item)
            item2 = deepcopy(item)
            item1.side = 1
            item1.tracks = item.tracks[:item.split_point]
            item2.side = 2
            item2.tracks = item2.tracks[item.split_point:]
            new_items.extend([item1, item2])            
    item_list.extend(new_items)

     # Add a counter to singles (45s) to be combined on a CD.
    for order in set([item.order for item in item_list]):
        order_items = [item for item in item_list if order in item.order and not (item.long and not item.side)]
        compilation_counter = 0
        compilation_cd_item_counter = 0
        compilation_duration = 0
        compilation_cd_duration = 0
        compilation_cd_counter = 0
        compilation_image = None
        compilation_cd_counter = 1
        order_compilation_items = [item for item in order_items if '45' in item.media_type and 'cd' in item.format]
        for item in order_compilation_items:
            if not compilation_image:
                compilation_image = item.image
            else:
                item.image = compilation_image
                item.image_path = os.path.join(images_folder, item.image) + '.jpg'
            compilation_counter += 1
            compilation_cd_item_counter += 1
            m, s = divmod(item.duration, 60)
            logging.info('Woohoo! {0} is single #{1} for order {2}! (Length: {3}:{4})'.format(
                item.name, compilation_counter, item.order, str(m), str(s).zfill(2)))
            compilation_cd_duration += item.duration
            compilation_duration += item.duration
            if compilation_cd_duration > 4700:
                compilation_cd_duration = item.duration
                compilation_cd_counter += 1
                compilation_cd_item_counter = 1
            item.compilation_cd_counter = compilation_cd_counter
            m, s = divmod(compilation_cd_duration, 60)
            logging.info('Current compilation duration: {0}:{1} (CD #{2}!)'.format(str(m), str(s).zfill(2), item.compilation_cd_counter))
            item.compilation_counter = compilation_counter
            item.compilation_cd_item_counter = compilation_cd_item_counter
            item.image_counter = item.compilation_cd_counter
        for item in order_compilation_items:
            item.compilation_cds = compilation_duration/4700 + 1
            item.compilation_items = compilation_counter

    # Add a counter to items using the same image on a CD.
    for image in set([item.image for item in item_list if item.image]):
        image_items = [item for item in item_list if item.image and image == item.image and item.compilation_cd_item_counter <= 1 and \
            not (item.long and not item.side) and not (item.copies > 1 and item.copy_counter)]
        if len(image_items) > 1:
            for image_counter, item in enumerate(image_items, 1):
                item.image_counter = image_counter
                if item.side:
                    logging.info('Yay! {0} is image #{1}! (Split {2} {3})'.format(item.name, item.image_counter, item.option, item.media_type))
                else:
                    logging.info('Yay! {0} is image #{1}!'.format(item.name, item.image_counter))

    # Add copies to list
    new_items = []
    for item in [each_item for each_item in item_list if each_item.copies > 1]:
        for i in range(1, item.copies + 1):
            new_item = deepcopy(item)
            new_item.copy_counter = i
            new_items.append(new_item)
    item_list.extend(new_items)

    item_list.sort(key=lambda x: (x.name, x.side))
    #list_item_stats()

    return item_list

def make_cover_image(item):
    if item.image_counter and item.compilation_cds != 1:
        base = Image.open(item.image_path).convert('RGBA')
        overlay = Image.new('RGBA', base.size, (255,255,255,0))
        fnt = ImageFont.truetype('garamond8.ttf', base.size[0] // 15)
        d = ImageDraw.Draw(overlay)
        counter = str(item.image_counter)

        textsize = d.textsize(counter, font=fnt)
        draw_position = (base.size[0] / 2, int(base.size[1] * 0.9))
        circle_radius = max(textsize) // 2
        circle_bounds = [(draw_position[0] - circle_radius, draw_position[1] - circle_radius),
            (draw_position[0] + circle_radius, draw_position[1] + circle_radius)]
        text_position = (draw_position[0] - textsize[0]/2, draw_position[1] - textsize[1]//1.5)

        d.ellipse(circle_bounds, fill=(255,255,255,64))
        #d.ellipse([(draw_position[0] - 5, draw_position[1] - 5), (draw_position[0] + 5, draw_position[1] + 5)], fill=(255,0,0,128))
        #d.ellipse([(text_position[0] - 5, text_position[1] - 5), (text_position[0] + 5, text_position[1] + 5)], fill=(0,255,0,128))
        d.text(text_position, counter, font=fnt, fill=(64,64,64,255))
        '''
        print 'draw_position;', draw_position
        print 'text_position:', text_position
        print 'fontsize:', base.size[0] // 10
        print 'base.size:', base.size
        print 'textsize:', textsize
        print 'circle_radius:', circle_radius
        '''
        out = Image.alpha_composite(base, overlay)

        label_path = os.path.join(cd_tracks_folder, item.name) + '_' + counter + '.jpg'
        out.save(label_path, 'jpeg')
    else:
        label_path = os.path.join(config.cd_tracks_folder, item.name) + '.jpg'
        shutil.copy(item.image_path, label_path)
    return label_path

def burn_cds(item_list):
    """ Create .JRQ files for CD burning/printing via Primera Bravo CD publisher """
    """ NYI: 1/4s; delete working folder when .DON; move done files to Julius """

    # Filter non-CD items, copied items, split item bases, compilation items after the first for each CD
    burn_cd_list = [each_item for each_item in item_list if \
        each_item.compilation_cd_item_counter <= 1 and 'cd' in each_item.format and not each_item.copy_counter and \
        not (each_item.long and not each_item.side)]

    logging.info('CDs: ({0}): {1}'.format(sum([item.copies for item in burn_cd_list]), [item.name for item in burn_cd_list]))
    for item in burn_cd_list:
        job_name = item.name + '-' + str(item.side) if item.side else item.name
        with open(os.path.normpath(ptburn_folder + '/' + job_name + '.JRQ'), 'w') as f:
            lines = []
            lines.append('JobID = ' + job_name)
            lines.append('ClientID = ' + os.environ['COMPUTERNAME'])
            lines.append('DeleteFiles = YES')
            if 'std' not in item.option or item.album or item.artist or item.long:
                # Write disc CD text
                if item.compilation_items > 1 and item.compilation_cds == 1:
                    lines.append('CDTextDiscTitle = Singles Compilation')
                elif item.compilation_items > 1 and item.compilation_cds > 1:
                    lines.append('CDTextDiscTitle = Singles Compilation (Disc {0})'.format(item.image_counter))
                elif item.image_counter:
                    lines.append('CDTextDiscTitle = {0} (Disc {1})'.format((item.album if item.album else 'Untitled'), item.image_counter))
                else:
                    lines.append('CDTextDiscTitle = ' + (item.album if item.album else 'Untitled'))
                if item.compilation_items > 1:
                    lines.append('CDTextDiscPerformer = Various')
                else:
                    lines.append('CDTextDiscPerformer = ' + (item.artist if item.artist else ''))
                lines.append('CDTextDiscComposer = ')
            if 'std' in item.option and not item.long:
                lines.append('AudioFile = ' + item.path + ', Pregap0')
                if item.album or item.artist:
                    # Write track CD text
                    lines.append('CDTextTrackTitle = ' + item.album)
                    lines.append('CDTextTrackPerformer = ' + item.artist)
                    lines.append('CDTextTrackComposer = ')
            else:
                # Split file into .wav tracks
                if item.compilation_counter:
                    # Add items to CD list for compilations
                    cd_items = [each_item for each_item in item_list if each_item.order == item.order and \
                        each_item.compilation_cd_counter == item.compilation_cd_counter and not item.copy_counter]
                else:
                    cd_items = [item]
                print 'cd_items:', [each_item.name for each_item in cd_items]
                for cd_item in cd_items:
                    audio = wave.open(cd_item.path)
                    audio.params = audio.getparams()
                    # Seek to beginning of item (relevant for split CDs)
                    audio.setpos(cd_item.tracks[0].start)
                    for i, track in enumerate(cd_item.tracks, 1):
                        # Build track filename
                        if cd_item.side:
                            digital_track_name = '{0}_{1}_{2}'.format(cd_item.name, str(cd_item.side), str(i).zfill(2))
                        else:
                            digital_track_name = '{0}_{1}'.format(cd_item.name, str(i).zfill(2))
                        digital_track_path = os.path.join(cd_tracks_folder, digital_track_name) + '.wav'
                        logging.info('Track {0} | {1} -> {2}'.format(i, track.duration, digital_track_name))
                        # Split, export track
                        digital_track = wave.open(digital_track_path, 'w')
                        digital_track.setparams(audio.params)
                        digital_track.writeframes(audio.readframes(track.stop - track.start))
                        digital_track.close()
                        # Add track info to PTBurn JRQ
                        lines.append('AudioFile = ' + digital_track_path + ', Pregap0')
                        lines.append('CDTextTrackTitle = ' + track.title.strip('.wav'))
                        lines.append('CDTextTrackPerformer = ' + cd_item.artist)
                        lines.append('CDTextTrackComposer = ')
                    audio.close()
            lines.append('CloseDisc = YES')
            lines.append('Copies = ' + str(item.copies))
            lines.append('RejectIfNotBlank = YES')
            #lines.append('TestRecord = YES')
            if not item.counter_image_path:
                item.counter_image_path = make_cover_image(item)
            lines.append('PrintLabel = ' + item.counter_image_path)
            for line in lines:
                f.write(line + '\n')

def main():
    logging.basicConfig(level=config.log_level)
    metadata_errors = []
    #utils.export_csv('Items') # Grab spreadsheet from Google Drive

    if config.just_add_tags:
        input_list = [each_file for each_file in os.listdir(config.audio_folder) if os.path.splitext(each_file.lower())[1][1:] in digital_formats]
    elif config.whole_folder:
        input_list = [each_file for each_file in os.listdir(config.audio_folder) if each_file.lower().endswith('.wav')]
    elif config.some_orders:
        input_list = [each_file for each_file in os.listdir(config.audio_folder) if (each_file.lower().endswith('.wav') and 
            each_file[:5] in orders_input)]
    elif config.some_items:
        input_list = [each_file for each_file in os.listdir(config.audio_folder) if (each_file.lower().endswith('.wav') and \
            any(each_item_input in each_file for each_item_input in items_input))]

    # Class-ify item input list
    item_list = [utils.Item(each_file) for item in input_list]

    # Halt program on metadata errors
    metadata_errors = [error for item in item_list for error in item.metadata_errors]
    if metadata_errors:
        for error in metadata_errors:
            print error
        print '{0} Metadata errors found! See above.'.format(len(metadata_errors))
        sys.exit()

    logging.info('item_list ({0}): {1}'.format(len(item_list), [item.name for item in item_list]))

    item_list = format_list(item_list)

    #if config.cd_pdf_toggle: make_cd_pdf(item_list)
    if config.front_pdf_toggle: make_front_pdf(item_list)
    if config.back_pdf_toggle: make_back_pdf(item_list)
    #if config.burn_cds_toggle: burn_cds(item_list)
    #if config.digital_files_toggle: make_digital_files(item_list)

    # Print order notes
    utils.print_order_notes(item_list)

if __name__ == '__main__':
    main()