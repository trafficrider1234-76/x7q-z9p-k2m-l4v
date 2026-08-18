import os
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import xml.etree.ElementTree as ET

SUBREDDIT = "forhire"
EMAIL_SENDER = "manexstore0@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = "manexstore0@gmail.com"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def analyze_with_groq(title, body_text):
    prompt = f"""
    You are an expert SEO and Web Development client filter. 
    Analyze the following Reddit post to determine if the poster is a CLIENT looking to hire someone for SEO, Web Development, or WordPress services.
    
    Post Title: {title}
    Post Body: {body_text}
    
    Respond ONLY with "YES" if they are looking to hire a freelancer/agency for these services, or "NO" if they are offering services, looking for a job themselves, or unrelated.
    """
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            answer = result['choices'][0]['message']['content'].strip().upper()
            return "YES" in answer
    except Exception as e:
        print(f"Groq API Error: {e}")
    
    return False

def send_email(title, link, created_date):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"Groq Verified Client Post: {title}"
        
        body = f"Groq AI verified a matching client post!\n\nTitle: {title}\nDate: {created_date}\nLink: {link}"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        print(f"Email sent successfully for: {title}")
    except Exception as e:
        print(f"Error sending email: {e}")

def check_reddit():
    url = f"https://www.reddit.com/r/{SUBREDDIT}/new.rss"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) RSSReader/1.0"}
    
    print(f"Fetching RSS feed from r/{SUBREDDIT}...")
    try:
        response = requests.get(url, headers=headers)
        print(f"Reddit RSS Response Status Code: {response.status_code}")
        
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            namespace = {'atom': 'http://www.w3.org/2005/Atom'}
            entries = root.findall('atom:entry', namespace)
            print(f"Successfully fetched {len(entries)} posts. Analyzing with Groq...")
            
            match_found = False
            for entry in entries:
                title = entry.find('atom:title', namespace).text
                link = entry.find('atom:link', namespace).attrib['href']
                updated = entry.find('atom:updated', namespace).text
                
                content_elem = entry.find('atom:content', namespace)
                body_text = content_elem.text if content_elem is not None and content_elem.text else ''
                
                # HTML tags clean karne ke liye (agar RSS mein hon)
                import re
                clean_body = re.sub('<[^<]+?>', '', body_text)
                
                print(f"Checking post: '{title}'")
                
                is_client = analyze_with_groq(title, clean_body)
                
                if is_client:
                    print(f"-> Groq Match Found! Valid client post.")
                    send_email(title, link, updated)
                    match_found = True
                    break
                else:
                    print("-> Ignored by Groq (Not a matching client).")
            
            if not match_found:
                print("No matching client posts found in this run.")
        else:
            print(f"Failed to fetch data, status code: {response.status_code}")
    except Exception as e:
        print(f"Error checking Reddit RSS/Groq: {e}")

if __name__ == "__main__":
    print("Groq Reddit RSS Client Finder started...")
    check_reddit()
    print("Script finished execution.")
