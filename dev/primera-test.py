"""
Control CD printing, burning via Primera Bravo 4102 CD/DVD publisher.
(c) Ameryn Media LLC, 2015. All rights reserved.
"""

from ConfigParser import ConfigParser
import os
import sys


CONFIG_LOCATION = 'ameryn.ini'

config = ConfigParser()
config.read(CONFIG_LOCATION)

# Input file parameters (name & location)
ptburn_folder = config.get('general', 'ptburn_folder')
ptburn_audio_folder = config.get('general', 'ptburn_audio_folder')
artist = 'Artist1'


def main(items_list):
    print ptburn_folder
    for item in items_list:
        with open(os.path.normpath(ptburn_folder + '/' + item + '.xxx'), 'w') as f:
            lines = []
            lines.append('JobID = ' + item)
            lines.append('ClientID = ' + os.environ['COMPUTERNAME'])
            lines.append('DeleteFiles = NO')
            lines.append('CDTextDiscTitle = ' + item)
            lines.append('CDTextDiscPerformer = ' + artist)
            lines.append('CDTextDiscComposer = ')
            for track in [fname for fname in os.listdir(ptburn_audio_folder) if fname.startswith(item) and \
                    os.path.splitext(fname)[-1].lower() == '.wav']:
                lines.append('AudioFile = ' + os.path.join(ptburn_audio_folder, track) + ', Pregap0')
                lines.append('CDTextTrackTitle = ' + track.strip('.wav'))
                lines.append('CDTextTrackPerformer = ' + artist)
                lines.append('CDTextTrackComposer = ')
            lines.append('CloseDisc = YES')
            lines.append('Copies = 1')
            lines.append('RejectIfNotBlank = YES')
            lines.append('TestRecord = NO')
            lines.append('PrintLabel = D:/03 tracks/02537-00001.jpg')

            for line in lines:
                f.write((line + '\n').encode('utf8'))

if __name__=="__main__":
    main(['02537-00001'])