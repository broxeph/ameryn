from WooCommerceClient import WooCommerceClient
import pprint
import sys

ck = 'ck_bc1ac58b5dc9099c8df1789f811afa2d'
cs = 'cs_7199c23290742677aed84294861ed73b'
base_url = 'https://www.ameryn.com/'
wc_client = WooCommerceClient(ck, cs, base_url, oauth_enabled=False)
requested_order_id = 3050
data = '{"order": {"status": "completed"}}'

#pprint.pprint(wc_client.get_order(requested_order_id))
#wc_client.update_order(requested_order_id, data)
order = wc_client.get_order(requested_order_id)['order']

# Get variables
print 'cust_email:', order['customer']['billing_address']['email']
print 'status:', order['status']
print 'notes:', order['note']

orders = wc_client.get_orders()['orders']
print 'orders:'
#pprint.pprint(orders[0])
for order in orders:
    print '{0} - {1}'.format(order['id'], order['status'])