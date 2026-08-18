import time
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configurations
SUBREDDIT = "forhire"
KEYWORDS = ["web developer", "seo", "wordpress"]
EMAIL_SENDER = "manexstore0@gmail.com"
EMAIL_PASSWORD = "Aapka_Email_App_Password"
EMAIL_RECEIVER = "manexstore0@gmail.com"

seen_posts = set()

def send_email(title, link):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"New Client Post: {title}"
        
        body = f"A new matching post was found on Reddit!\n\nTitle: {title}\nLink: {link}"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def check_reddit():
    url = f"https://www.reddit.com/r/{SUBREDDIT}/new.json?limit=10"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            posts = data['data']['children']
            
            for post in posts:
                post_data = post['data']
                post_id = post_data['id']
                title = post_data['title']
                permalink = post_data['permalink']
                post_url = f"https://www.reddit.com{permalink}"
                
                if post_id not in seen_posts:
                    seen_posts.add(post_id)
                    
                    for keyword in KEYWORDS:
                        if keyword.lower() in title.lower():
                            print(f"Match found: {title}")
                            send_email(title, post_url)
                            break
        else:
            print(f"Failed to fetch data, status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching Reddit data: {e}")

if __name__ == "__main__":
    print("Reddit Client Finder script started...")
    while True:
        check_reddit()
        time.sleep(300)
