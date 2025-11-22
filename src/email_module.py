import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# SENDER EMAIL HAS TO BE GMAIL
def send_email(sender_email_address, target_email_address, gmail_app_password, subject, body, image_path):
    msg = MIMEMultipart() 
    msg["Subject"] = subject
    msg["From"] = sender_email_address
    msg["To"] = target_email_address

    msg.attach(MIMEText(body, "plain"))
    with open(image_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read()) 

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        f"attachment; filename= {image_path}",
    )
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email_address, gmail_app_password)
        server.sendmail(sender_email_address, target_email_address, msg.as_string())
    println(f"Sent email to: {target_email_address}")
