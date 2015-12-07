# HTTP Basic Auth example

import urllib2
import base64

theurl = 'https://www.ameryn.com/wp-api/v2'
username = 'ck_bc1ac58b5dc9099c8df1789f811afa2d'
password = 'cs_7199c23290742677aed84294861ed73b'
# a great password

# https://www.ameryn.com/wp-api/v2/orders/
# ck_bc1ac58b5dc9099c8df1789f811afa2d
# cs_7199c23290742677aed84294861ed73b

request = urllib2.Request(theurl)
base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
request.add_header("Authorization", "Basic %s" % base64string)   
result = urllib2.urlopen(request)

'''
passman = urllib2.HTTPPasswordMgrWithDefaultRealm()
# this creates a password manager
passman.add_password(None, theurl, username, password)
# because we have put None at the start it will always
# use this username/password combination for  urls
# for which `theurl` is a super-url

authhandler = urllib2.HTTPBasicAuthHandler(passman)
# create the AuthHandler

opener = urllib2.build_opener(authhandler)

urllib2.install_opener(opener)
# All calls to urllib2.urlopen will now use our handler
# Make sure not to include the protocol in with the URL, or
# HTTPPasswordMgrWithDefaultRealm will be very confused.
# You must (of course) use it when fetching the page though.

pagehandle = urllib2.urlopen(theurl)
# authentication is now handled automatically for us

print pagehandle
'''