from item import Item

a = Item('03350-00005.wav', tracks_added=True)

print a.cues
print a.name
print a.option
for track in a.tracks:
	print track.num, track.title, track.duration