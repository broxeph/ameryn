# Ameryn Media metadata processor
# Alex Ball, 2015

import discogs_client
from mutagen.flac import FLAC
import csv, os, time, math, logging
import webbrowser
import time
from ConfigParser import ConfigParser
import sys

CONFIG_LOCATION = 'ameryn.ini'
CLIENT_NAME = 'AmerynDiscogsBot/0.1'
CONSUMER_KEY = 'lysCMszUmXHGNcFDVmbH'
CONSUMER_SECRET = 'njuRMMqVtcCkojDvRtGhOFqstZfHBFrf'
TOKEN = u'DpladtVtvbpotOOuCMsqlPemAwdFSZgERbDFFYUI'
SECRET = u'ZFryZTlEeqoqQdwTUhQLaViZGUPPOnsKCmLvXPpe'

def main():
    def discogs_auth():
        authorize_token = None
        while not authorize_token:
            discogs = discogs_client.Client(CLIENT_NAME)
            discogs.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
            authorize_url = discogs.get_authorize_url()
            webbrowser.open(authorize_url[2])
            authorize_token = raw_input('Enter authorize token (Or q to quit): ')
        if authorize_token.lower() == 'q': return 'q'
        access_token = discogs.get_access_token(authorize_token)
        print 'access_token: {0}'.format(access_token)
        return discogs

    def discogs_quick():
        discogs = discogs_client.Client(CLIENT_NAME, CONSUMER_KEY, CONSUMER_SECRET, TOKEN, SECRET)
        #discogs.set_consumer_key(CONSUMER_KEY, CONSUMER_SECRET)
        #authorize_url = discogs.get_authorize_url()
        #authorize_token = 'MJXBCHohmC'
        #access_token = discogs.get_access_token(authorize_token)
        #access_token = (u'DpladtVtvbpotOOuCMsqlPemAwdFSZgERbDFFYUI', u'ZFryZTlEeqoqQdwTUhQLaViZGUPPOnsKCmLvXPpe')
        #print 'access_token: {0}'.format(access_token)
        return discogs

    def add_serial_metadata(input_filename):
        filename_matches = []
        log_comment = ''
        artist = ''
        album = ''
        track_lengths_correlation = 0
        discogs_match = False
        resplit_serial = False

    input_filename_list = []
    matches_count = 0
    start_time = time.time()
    discogs_logged_in = False

    # try Discogs - debug
    #discogs = discogs_auth()
    discogs = discogs_quick()

    print discogs.search('led zeppelin', type='release')[0]

    print 'Awesome.'
    sys.exit()


    # Log into Discogs
    while not discogs_logged_in:
        try:
            discogs = discogs_auth()
            if discogs == 'q': sys.exit()
            discogs_logged_in = True
        except:
            print 'Nope! Try again.'

# RUN THE TRAP
if __name__ == '__main__':
    main()