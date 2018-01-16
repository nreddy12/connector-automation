import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.text import MIMEText


def send_custom_mail(details):
    ctype, encoding = mimetypes.guess_type(details['fileToSend'])
    if ctype is None or encoding is not None:
        ctype = "application/octet-stream"

    maintype, subtype = ctype.split("/", 1)

    if maintype == "text":
        fp = open(details['fileToSend'])
        # Note: we should handle calculating the charset
        attachment = MIMEText(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "image":
        fp = open(details['fileToSend'], "rb")
        attachment = MIMEImage(fp.read(), _subtype=subtype)
        fp.close()
    elif maintype == "audio":
        fp = open(details['fileToSend'], "rb")
        attachment = MIMEAudio(fp.read(), _subtype=subtype)
        fp.close()
    else:
        fp = open(details['fileToSend'], "rb")
        attachment = MIMEBase(maintype, subtype)
        attachment.set_payload(fp.read())
        fp.close()
        encoders.encode_base64(attachment)

    attachment.add_header("Content-Disposition", "attachment",
                          filename=details['fileToSend'])

    msg = MIMEMultipart()
    msg["From"] = details['emailfrom']
    msg["To"] = details['emailto']
    msg["Subject"] = "PI | Automation Test Report(24-09-2017)"
    msg.preamble = "help I cannot send an attachment to save my life"
    msg.attach(attachment)

    # server connection
    server = smtplib.SMTP("smtp.gmail.com:587")
    server.starttls()
    server.login(details['username'], details['password'])
    server.sendmail(details['emailfrom'], details['emailto'], msg.as_string())
    server.quit()


if __name__ == '__main__':
    mail_details = {'emailfrom': 'narasimha.nitk@gmail.com',
                    'emailto': 'chak10.nag3@gmail.com',
                    'fileToSend': 'test_report.csv',
                    'username': 'narasimha.nitk@gmail.com',
                    'password': 'NarasimhaNITK'
                    }

    send_custom_mail()

