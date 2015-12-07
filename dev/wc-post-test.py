from WooCommerceClient import WooCommerceClient
import pprint
import sys
import dropbox

ck = 'ck_bc1ac58b5dc9099c8df1789f811afa2d'
cs = 'cs_7199c23290742677aed84294861ed73b'
base_url = 'https://www.ameryn.com/'
wc_client = WooCommerceClient(ck, cs, base_url, oauth_enabled=False)
requested_order_id = 2572
dbox_token = 'asEt1sv4B_0AAAAAAAAFC7AWI6KFNqvxFx2o73NUOLERBg8VxVfsRGSHzqfOqCtL'
data = '{"order": {"status": "completed"}}'

#pprint.pprint(wc_client.get_order(requested_order_id))
wc_client.update_order(requested_order_id, data)
order = wc_client.get_order(requested_order_id)['order']

# Get variables
print 'cust_email:', order['customer']['billing_address']['email']
print 'status:', order['status']
print 'notes:', wc_client.get_order_notes(requested_order_id)