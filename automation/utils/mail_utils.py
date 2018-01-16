from datetime import datetime
from email import MIMEMultipart, MIMEBase, Encoders
import smtplib


sender = "pradeep.k@shieldsquare.com"
rcvr = "narasimha.m@shieldsquare.com"

def send_test_report():
    filename = 'dict_output.csv'
    send_email_attachment(filename)


def send_email_attachment(filename):
    msg = MIMEMultipart()
    file_content = open(filename, "rb").read()

    part = MIMEBase("application", "octet-stream")
    part.set_payload(file_content)
    Encoders.encode_base64(part)
    today = datetime.now().strftime('%Y-%m-%d')
    part.add_header("Content-Disposition", "attachment; filename=content-%s.csv" % today)

    msg.attach(part)
    msg['Subject'] = "PI | Automation Framework - [%s]" % today
    msg['From'] = sender
    msg['To'] = rcvr
    try:
        smtpObj = smtplib.SMTP('localhost')
        smtpObj.sendmail(sender, rcvr, msg.as_string())
        smtpObj.close()
    except smtplib.SMTPException:
        print "Failed to send email"