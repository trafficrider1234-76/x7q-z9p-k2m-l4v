import os
import smtplib
from email.message import EmailMessage
import discord
from groq import Groq

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Groq client initialize karein
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def analyze_with_groq(message_content):
    prompt = f"""
    Aap ek expert sales assistant hain. Niche diye gaye Discord message ko analyze karein aur batayein ke kya yeh banda SEO, Web Development, ya Digital Marketing ki koi service khareedna chahta hai, ya kisi madad ki talash mein hai?
    
    Message: "{message_content}"
    
    Sirf "YES" ya "NO" mein jawab dein. Agar wo service ya help mang raha hai toh YES likhein, warna NO likhein.
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=5
        )
        result = completion.choices[0].message.content.strip().upper()
        return "YES" in result
    except Exception as e:
        print(f"Groq API Error: {e}")
        return False

def send_email_alert(client_name, message_content):
    sender_email = os.getenv('EMAIL_ADDRESS')
    app_password = os.getenv('EMAIL_PASSWORD')
    
    msg = EmailMessage()
    msg.set_content(f"Verified Client Found!\n\nUser: {client_name}\nMessage: {message_content}")
    msg['Subject'] = "New Qualified Client via Groq & Discord!"
    msg['From'] = sender_email
    msg['To'] = "manexstore0@gmail.com"

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
    
    # Message lamba ya meaningful ho tabhi check karein
    if len(message.content.strip()) > 10:
        print(f"Analyzing message from {message.author}: {message.content}")
        
        # Groq se poochwayein ke yeh client hai ya nahi
        is_client = analyze_with_groq(message.content)
        
        if is_client:
            print(f"--> Valid client detected! Sending email...")
            send_email_alert(str(message.author), message.content)
        else:
            print(f"--> Ignored: Not a service request.")

token = os.getenv('DISCORD_TOKEN')
client.run(token)
