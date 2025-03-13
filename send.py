import smtplib
import ssl
from email.message import EmailMessage
from random import randint
import keyring

service = "MyApp"
username = "myuser"

retrieved_password = keyring.get_password(service, username)
# Email configuration
SMTP_SERVER = "smtp.gmail.com"  # Change for different providers
SMTP_PORT = 465  # Use 587 for TLS, 465 for SSL

def send_email(RECEIVER_EMAIL):
    SENDER_EMAIL = "shreshtmit09@gmail.com"
    SENDER_PASSWORD = retrieved_password  # Use an App Password for security

    # Create email message
    msg = EmailMessage()
    msg["Subject"] = "Confirmation"
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    code=778462
    msg.set_content(f'HI For confirmation click link https://forms.gle/pHzsYtWAGuYpLnjn6.conformation number {code}')

    # Send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context) as server:
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)

    print("Email sent successfully!")
def send_all_emails(ar):
    for i in ar:
        send_email(i)
#send_all_emails(ar=["supreetarag@gmail.com","supreetamn@gmail.com","naikrag@gmail.com"])