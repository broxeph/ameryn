'''
Various utilities for metadata processing
(C) 2015 Ameryn Media, LLC
'''

import csv
import os

from oauth2client.client import SignedJwtAssertionCredentials
import gspread

CLIENT_EMAIL = '837577673408-4ptmkqkrgu6f7us0en6sc1r1l8u94pia@developer.gserviceaccount.com'
PRIVATE_KEY = u'-----BEGIN PRIVATE KEY-----\nMIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBANOPthJtvH0+cWRp\no0gPIAunpum231rJqOnLumZ3sHnEg4Tu3CzgMWBBvVF75MhY44ZvH25ORMxj7hYB\nIz5bZ7DGG24t5/Tj1nRsKgf4yLxt+q336xpms4uhNdK7Ux1mSIryy/M/gttcmT8v\nFQFVXsLzHPEAQJYV5fOqr91OeCt9AgMBAAECgYEA0TH189sW2zF3prbegk6SfXPW\nFJyD1544rJaLRu9rTb0H39bhWG6H5IqczYoY/BMJSNFw3v3+Aa1+q7uMQgjYSaL6\nz3j0y8T+ugtRhVn/azpsqxn6rlbJtCFM/xwx/f1x8sc/NIL/wsyqk6X+cIFNDZCT\nL5yIBCo36m8v4tyCq4ECQQD5npOUgzsfaslXfxAly180jLndUOz7yCe4P/Fr7K/f\n6OpQ/ShtM0U7qx+dnkxZQzaqf7Pybt5fzLm+T5RQ5GblAkEA2PgYir6R8L/s9wKZ\numpTj/V6FxJMkoieka8yyzNRMe48LV/h7i8DMFjUXd0TMb9d1i1Es/kv33NjEvA6\nh9WQuQJAORY3EiPhBZJacZQxkTMtlssIRsEXMY3Y555YDCKZJlASJmt/L1omXzsH\ng/iL5W4ltmB2Ot94I9iiMg/pD4bssQJAMfUeIYQzsk1e0JlGsEefKfyJuho6i1rt\nt/mxJlyQi4ChVolHSkKE53LsoxguPTwk7RXLRe1QepDk9Q1fTLt98QJALuaPvZ4C\nJWK9vihK39X3ESsw8wAfct5mzjFuorCp4076sqOJO2SY6BNAD9TriYYG1bZOj0Qv\najT0yn6YXctdtg\u003d\u003d\n-----END PRIVATE KEY-----\n'
SCOPE = ['https://spreadsheets.google.com/feeds']
#output_dir = CONFIG.GET BLAH
output_dir = ''

def export_csv(input_fname):
	credentials = SignedJwtAssertionCredentials(CLIENT_EMAIL, PRIVATE_KEY, SCOPE)
	gc = gspread.authorize(credentials)
	sheet = gc.open(input_fname).sheet1
	output_fname = os.path.join(output_dir, input_fname.lower()) + '.csv'

	#print sheet.acell('A2').value
	everything = sheet.get_all_values()
	everything = [[col.encode('utf-8') for col in row] for row in everything]

	with open(output_fname, "wb") as f:
	    writer = csv.writer(f)
	    writer.writerows(everything)

if __name__ == '__main__':
	export_csv('Items')