import smtplib

#SERVER = "localhost"
SERVER = 'smtp-relay.gmail.com'
#PORT = 1025
PORT = 587

FROM = "orders@ameryn.com"
TO = ["test@ameryn.com"] # must be a list

SUBJECT = "Hello!"

TEXT = "This message was sent with Python's smtplib. Test 3."

user = 'alex@ameryn.com'
pw = 'calselptbnympllf'

# Prepare actual message

message = '''\
From: {0}
To: {1}
Subject: {2}

{3}
'''.format(FROM, ', '.join(TO), SUBJECT, TEXT)

# Send the mail

server = smtplib.SMTP(SERVER, PORT)
server.starttls()
server.login(user, pw)
server.sendmail(FROM, TO, message)
server.quit()