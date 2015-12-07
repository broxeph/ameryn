import discogs_client as discogs
discogs.user_agent = 'CrystalDiscogsBot/0.1 +http://www.crystal-lp.com'
release = discogs.Release(3839764)
print release.data['id']
print release.artists
print release.title
print release.artists[0].name.encode('utf-8')