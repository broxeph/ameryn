'''
Various utilities for metadata processing
(C) 2015 Ameryn Media, LLC
'''

import csv
import os
from collections import namedtuple
import logging
from contextlib import closing
import wave
import HTMLParser

from oauth2client.client import SignedJwtAssertionCredentials
import gspread
from WooCommerceClient import WooCommerceClient

import config
import split

def export_csv(input_sheets):
    output_dir = config.get('general', 'csv_path')
    drive_client_email = config.get('general', 'drive_client_email')
    drive_private_key = config.get('general', 'drive_private_key').replace('\\n', '\n')
    credentials = SignedJwtAssertionCredentials(drive_client_email, drive_private_key, ['https://spreadsheets.google.com/feeds'])
    gc = gspread.authorize(credentials)

    if not isinstance(input_sheets, list): input_sheets = [input_sheets]        
    for each_sheet in input_sheets:
        sheet = gc.open(each_sheet).sheet1
        output_fname = os.path.join(output_dir, each_sheet.lower()).translate(None, '!') + '.csv'
        everything = [[col.encode('utf-8') for col in row] for row in sheet.get_all_values()]

        with open(output_fname, 'wb') as f:
            writer = csv.writer(f)
            writer.writerows(everything)

def print_order_notes(item_list):
    # items.csv item notes
    notes_lines = [' - items.csv -']
    for item in [item for item in item_list if not item.copy_counter and not item.side]:
        if item.customer_notes:
            notes_lines.append('{0} - Customer notes: {1}'.format(item.name, item.customer_notes))

    # WooCommerce order notes
    notes_lines.append(' - WC notes -')
    wc_client = WooCommerceClient(config.wc_ck, config.wc_cs, config.base_url, oauth_enabled=False)
    for order_id in set([item.order.lstrip('0') for item in item_list]):
        order = wc_client.get_order(order_id)['order']
        html_parser = HTMLParser.HTMLParser()
        notes_lines.append('{0} - {1}'.format(order_id, html_parser.unescape(order['note'])))

    # Print notes; write to text file
    for notes_line in notes_lines:
        print notes_line
    order_notes_file = os.path.join(config.order_notes_path, 'order_notes.txt')
    with open(order_notes_file, 'w') as notes:
        for notes_line in notes_lines:
            notes.write(notes_line + '\n')

    # Open notes in default text editor
    os.startfile(order_notes_file)

Track = namedtuple('Track', ['num', 'title', 'duration', 'start', 'stop'])

class Item(object):
    def __init__(self, input_name):
        self.metadata_errors = []
        self.filename = input_name
        self.name = os.path.splitext(input_name)[0].split('_clean')[0].split('_tracked')[0]
        self.path = os.path.join(config.audio_folder, input_name)
        self.serial = self.name.split('_')[0]
        self.order = input_name[:5]
        self.copies = 1
        self.get_metadata()

    def get_metadata(self):
        """ Read metadata from csv db """
        with open(config.db_path, 'r') as items:
            rows = csv.reader(items)
            for row in rows:
                if row[0] == self.serial:
                    logging.debug('Item {0} found in {1}.'.format(self.serial, config.db_path))
                    self.artist = row[1]
                    self.album = row[2]
                    self.media_type = row[3].lower()
                    self.option = row[4].lower()
                    self.format = row[5].lower()
                    for digital_format in config.digital_formats:
                        if digital_format in self.format:
                            self.digital_ext = digital_format
                            break
                    else:
                        self.digital_ext = None                    
                    self.bitrate = '320k' if '320' in self.format else config.mp3_bitrate
                    if row[6].lower() == 'none' and 'cd' not in self.format:
                        self.image = None
                        self.image_path = None
                        self.thumb = None
                        self.thumb_path = None
                    else:
                        if row[6]:
                            self.image = row[6]
                        else:
                            self.image = self.serial
                        if os.path.isfile(os.path.join(config.images_folder, self.image) + '.jpg'):
                            self.image_path = os.path.join(config.images_folder, self.image) + '.jpg'
                        elif os.path.isfile(os.path.join(config.images_folder, 'Archived cover pictures/', self.image) + '.jpg'):
                            self.image_path = os.path.join(config.images_folder, 'Archived cover pictures/', self.image) + '.jpg'
                        else:
                            self.metadata_errors.append('Error! No image found for {0}'.format(self.name))
                    self.counter_image_path = None
                    self.copies = int(row[7]) if row[7] else 1
                    self.copy_counter = None
                    self.date_received = row[8]
                    self.customer_notes = row[9]
                    self.private_notes = row[10]
                    self.split_point = int(self.private_notes[1:3]) if self.private_notes and self.private_notes[0] == '_' else None
                    # Check if long (>78m)
                    with closing(wave.open(self.path, 'r')) as audio:
                        self.duration = audio.getnframes() / audio.getframerate()
                        if self.duration > 4680 and 'cd' in self.format:
                            self.long = True
                            if 'std' not in self.option and not self.split_point and 'cd' in self.format:
                                self.metadata_errors.append('Error! Split point needed for Tracked long item {0}'.format(self.name))
                                return
                            elif 'std' in self.option:
                                self.split_point = 1
                        else:
                            self.long = False
                    self.side = None
                    self.tracks = []
                    self.compilation_counter = None
                    self.compilation_cd_item_counter = None
                    self.compilation_cd_counter = None
                    self.compilation_cds = 0
                    self.compilation_items = 0
                    self.image_counter = 0
                    # Tracks stuff
                    if 'std' not in self.option or self.long:
                        tracks = [track for track in row[12:59] if track]
                        if not self.long and 'cd' in self.format and len(tracks) > 30:
                            logging.warning('Careful! >30 tracks for Tracked {0} {1}.'.format(self.media_type, self.name))
                        # Read track times from audio file
                        self.cues = split.read_markers(self.path)
                        if len(self.cues) < 2 and 'std' not in self.option:
                            self.metadata_errors.append('Error! No markers found in audio for Tracked {0} {1}'.format(self.media_type, self.name))
                            return
                        elif len(self.cues) < 3 and self.long:
                            self.metadata_errors.append('Error! No markers found in audio for long (>78m) {0} {1}'.format(
                                self.media_type, self.name))
                            return
                        if not tracks:
                            if 'std' in self.option and len(self.cues) == 3:
                                tracks = ['Side A', 'Side B']
                            else:
                                logging.info('No tracks found in db for Tracked {0} {1}.'.format(self.media_type, self.name))
                                for cue_num in range(1, len(self.cues)):
                                    tracks.append('Track {0}'.format(cue_num))
                        if len(tracks) is not len(self.cues) - 1:
                            self.metadata_errors.append('Error! Item {0} expected {1} tracks, found {2} in audio file.'.format(
                                self.name, len(tracks), len(self.cues) - 1))
                            return
                        # Set file, track durations
                        for i in range(1, len(self.cues)):
                            duration = self.cues[i] - self.cues[i - 1]
                            m, s = divmod(duration / 44100, 60)
                            duration = '{0}:{1}'.format(str(m), str(s).zfill(2))
                            self.tracks.append(Track(num=i, title=tracks[i - 1][:200], \
                                duration=duration, start=self.cues[i - 1], stop=self.cues[i]))
                    return
            else:
                 logging.warning('Row {0} not found in {1}.'.format(self.serial, db_path))
                 self.metadata_errors.append('Row {0} not found in {1}.'.format(self.serial, db_path))

    def print_tracks(self):
        print '{0} tracks:'.format(self.name)
        for track in self.tracks:
            print '{0} - {1} - {2}'.format(track.num, track.title, track.duration)