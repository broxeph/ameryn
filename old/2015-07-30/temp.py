from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, error

audio = MP3('D:/00 Recorded/mp3/02037-00003_clean.mp3', ID3=ID3)

# add ID3 tag if it doesn't exist
try:
    audio.add_tags()
except error:
    pass

audio.tags.add(
    APIC(
        encoding=3, # 3 is for utf-8
        mime='image/jpg', # image/jpeg or image/png
        type=3, # 3 is for the cover image
        desc=u'Cover1',
        data=open('C:/Sextus share/02037-00001_600x600.jpg', 'rb').read()
    )
)
audio.save()