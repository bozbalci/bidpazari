EMAIL_SENDER = 'admin@bidpazari.org'


def send_mail(recipient, subject, message, sender=EMAIL_SENDER):
    print(f'''\
From: {sender}
To: {recipient}
Subject: {subject}

{message}''')
