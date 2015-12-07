'''
Item (LP/cassette) class
(C) 2015 Ameryn Media, LLC
'''

from collections import namedtuple
from contextlib import closing
import wave
import logging
import split
import os
import csv

import config

Track = namedtuple('Track', ['num', 'title', 'duration', 'start', 'stop'])

class Item(object):    
    def __init__(self, input_name, tracks_added=False):
        self.metadata_errors = []
        self.filename = input_name
        self.name = os.path.splitext(input_name)[0].split('_clean')[0].split('_tracked')[0]
        self.path = os.path.join(config.tracked_folder, input_name)
        self.serial = self.name.split('_')[0]
        self.order = input_name[:5]
        self.tracks_added = tracks_added
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
                    self.side = None
                    self.tracks = []
                    self.compilation_counter = None
                    self.compilation_cd_item_counter = None
                    self.compilation_cd_counter = None
                    self.compilation_cds = 0
                    self.compilation_items = 0
                    self.image_counter = 0
                    # Tracks stuff
                    if self.tracks_added:
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
                        if 'std' not in self.option or self.long:
                            tracks = [track for track in row[12:59] if track]
                            if not self.long and 'cd' in self.format and len(tracks) > 30:
                                logging.warning('Careful! >30 tracks for Tracked {0} {1}.'.format(self.media_type, self.name))
                            # Read track times from audio file
                            self.cues = split.read_markers(self.path)
                            if len(self.cues) < 2 and 'std' not in self.option:
                                self.metadata_errors.append('Error! No markers found in audio for Tracked {0} {1}'.format(
                                    self.media_type, self.name))
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
                 logging.warning('Row {0} not found in {1}.'.format(self.serial, config.db_path))
                 self.metadata_errors.append('Row {0} not found in {1}.'.format(self.serial, config.db_path))

    def print_tracks(self):
        print '{0} tracks:'.format(self.name)
        for track in self.tracks:
            print '{0} - {1} - {2}'.format(track.num, track.title, track.duration)