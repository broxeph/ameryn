import discogs_client
import webbrowser

d = discogs_client.Client('AmerynTest/0.1')
d.set_consumer_key('lysCMszUmXHGNcFDVmbH', 'njuRMMqVtcCkojDvRtGhOFqstZfHBFrf')
auth_url = d.get_authorize_url()
webbrowser.open(auth_url[2])

token = raw_input('Enter authorize token: ')

print d.get_access_token(token)

me = d.identity()
print 'I\'m {0} ({1}) from {2}.'.format(me.name, me.username, me.location)
print 'len(wantlist:', len(me.wantlist)

results = d.search('Stockholm By Night', type='release')
print 'results.pages:', results.pages
artist = results[0].artists[0]
print 'artist[0].name:', artist.name

results = d.search('random album title', type='release')
print 'results.pages:', results.pages
artist = results[0].artists[0]
print 'artist[0].name:', artist.name