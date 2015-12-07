'''
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error
from mutagen import File
from mutagen.flac import FLAC, Picture
from mutagen.easyid3 import EasyID3
'''

from mutagen.id3 import ID3, TIT2, TOA, TP1, TP2, TP4, TAL

muta = ID3('stened.mp3')

muta.add(TIT2(encoding=3, text=u'title'))
muta.add(TOA(encoding=3, text=u'artist (toa)'))
muta.add(TP1(encoding=3, text=u'artist (tpe1)'))
muta.add(TP2(encoding=3, text=u'artist (tpe2)'))
muta.add(TP4(encoding=3, text=u'artist (tpe4)'))
muta.add(TAL(encoding=3, text=u'yoaoeu'))

muta.save(v2_version=3)