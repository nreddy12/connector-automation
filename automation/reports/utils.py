from __builtin__ import isinstance
from datetime import datetime
from email import Encoders, encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
from smtplib import SMTPException
import smtplib
import socket
import struct
import sys

from django.core.mail.message import EmailMessage
from django.template.context import Context
from django.template.loader import render_to_string

from automation import settings


# Listed internal ips are converted into long
valid_ip_ranges = [[0, 16777215],
                   [167772160, 184549375],
                   [1681915904, 1686110207],
                   [2130706432, 2147483647],
                   [2886729728, 2887778303],
                   [3221225472, 3221225727],
                   [3232235520, 3232301055],
                   [3323068416, 3323199487]]


def is_valid_ip(ip_address):
    colon_count = ip_address.count(':')
    period_count = ip_address.count('.')

    if not(colon_count > 1 or period_count == 3):
        return False

    if colon_count > 1:
        if (ip_address == '::1') or (ip_address == '0:0:0:0:0:0:0:0') or \
           (ip_address == '::') or (ip_address == '::/128') or \
           (ip_address == '0:0:0:0:0:0:0:1') or (ip_address == '::1/128'):
            return False
        elif ip_address.startswith('fd'):
            return False
    elif period_count == 3:
        if colon_count == 1:
            ip_address = ip_address.split(':')[0]
        if check_ip_ranges(ip_address):
            return False
    return True


def check_ip_ranges(ip_address):
    ip2long = struct.unpack("!L", socket.inet_aton(ip_address))[0]
    for i in range(len(valid_ip_ranges)):
        if ip2long >= valid_ip_ranges[i][0] and ip2long <= valid_ip_ranges[i][1]:
            return True
    return False

mail_list = {
             'test_report': {'from': 'narasimha.nitk@gmail.com',
                             'to': 'narasimha.m@shieldsquare.com',
                             'cc': []
                             }}

def get_mail_from(category):
    try:
        mail_from = mail_list[category]['from']
    except KeyError:
        mail_from = 'ss-admin@shieldsquare.com'
    return mail_from


def get_to_list(category):
    try:
        to = mail_list[category]['to']
    except KeyError:
        to = None
    return to


def get_cc_list(category):
    try:
        cc = mail_list[category]['cc']
    except KeyError:
        cc = None
    return cc


# sender = "narasimha.m@shieldsquare.com" 
# rcvr = "pradeep.k@shieldsquare.com" 

def CSVCreation(object):
    def __init__(self, ):
        super(CSVCreation, self).__init__()
    
    def write_data(self):
        pass
    
def custom_email(label, to, cc=None, attachments=None, context=None):
    if not isinstance(to, (list, tuple)):
        to = [to]

    if not isinstance(cc, (list, tuple)):
        cc = [cc]
    
    full_context = dict()
    full_context.update({} or context)
    mail_obj = EmailMessage()
    mail_obj.to = to
    mail_obj.cc = cc
    mail_obj.subject = render_to_string('email/{}/subject.txt'.format(label), context=full_context)
    mail_obj.from_email = settings.EMAIL_HOST_USER
    mail_obj.body = render_to_string('email/{}/message.html'.format(label),
                                     context=full_context)
    if attachments:
        for file_name in attachments:
            if os.path.exists(file_name):
                mail_obj.attach_file(file_name)
            else:
                logging.debug("file is not available in specified location: {}".format(file_name))
    mail_obj.content_subtype = "html"

    try:
        return mail_obj.send()
    except Exception as e:
        msg = u"sending email failed\n"
        msg += unicode(e)
        print >> sys.stderr, e


def send_test_report():
    from django.core.mail import EmailMessage
    email = EmailMessage('Subject', 'Body', to=['narasimha.m@shieldsquare.com'])
    email.send()
#     fromaddr = "narasimha.nitk@gmail.com"
#     toaddr = "narasimha.m@shieldsquare.com"
#      
#     msg = MIMEMultipart()
#      
#     msg['From'] = fromaddr
#     msg['To'] = toaddr
#     msg['Subject'] = "PI | Automation Framework Test Report"
#      
#     body = "TEXT YOU WANT TO SEND"
#      
#     msg.attach(MIMEText(body, 'plain'))
#      
#     filename = 'dict_output.csv'
#     attachment = open(filename, "rb")
#      
#     part = MIMEBase('application', 'octet-stream')
#     part.set_payload((attachment).read())
#     encoders.encode_base64(part)
#     part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
#      
#     msg.attach(part)
#      
#     server = smtplib.SMTP('smtp.gmail.com', 587)
#     server.starttls()
#     server.login(fromaddr, "NarasimhaNITK")
#     text = msg.as_string()
#     server.sendmail(fromaddr, toaddr, text)
#     server.quit()

# def send_test_report():
#     filename = 'dict_output.csv'
#     send_email_attachment(filename)
# 
# 
# def send_email_attachment(filename):
#     msg = MIMEMultipart()
#     file_content = open(filename, "rb").read()
# 
#     part = MIMEBase("application", "octet-stream")
#     part.set_payload(file_content)
#     Encoders.encode_base64(part)
#     today = datetime.now().strftime('%Y-%m-%d')
#     part.add_header("Content-Disposition", "attachment; filename=content-%s.csv" % today)
# 
#     msg.attach(part)
#     msg['Subject'] = "PI | Automation Framework - [%s]" % today
#     msg['From'] = sender
#     msg['To'] = rcvr
#     try:
#         smtpObj = smtplib.SMTP('localhost')
#         smtpObj.sendmail(sender, rcvr, msg.as_string())
#         smtpObj.close()
#     except smtplib.SMTPException:
#         print "Failed to send email"
