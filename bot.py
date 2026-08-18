import os
import smtplib
from email.message import EmailMessage
import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

def send_email_alert(client_name, message_content):
    sender_email = os.getenv('EMAIL_ADDRESS') # Yeh mananop302@gmail.com uthayega
    app_password = os.getenv('EMAIL_PASSWORD') # mananop302 ka app password
    
    msg = EmailMessage()
    msg.set_content(f"Client: {client_name}\nMessage: {message_content}")
    msg['Subject'] = "New Client Found via Discord Bot!"
    msg['From'] = sender_email
    msg['To'] = "manexstore0@gmail.com" # Alerts is email par aayenge

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)
        print("Email alert sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    
    if 'seo' in message.content.lower() or 'web dev' in message.content.lower():
        print(f"Potential Client Found: {message.author} said: {message.content}")
        send_email_alert(str(message.author), message.content)

token = os.getenv('DISCORD_TOKEN')
client.run(token)
