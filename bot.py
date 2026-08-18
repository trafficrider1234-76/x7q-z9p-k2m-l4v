import os
import requests
import smtplib
import time
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import xml.etree.ElementTree as ET
import re

SUBREDDITS = [
    "forhire", "freelance_forhire", "Hiring", "jobbit",
    "freelance", "digital_marketing", "SEO", "wordpress", "webdev",
    "DesignJobs", "Shopify", "ecommerce", "remotework", "smallbusiness",
    "startups", "ClientsForHire", "ProgrammingJobs", "WebDesign",
    "LocalSEO", "WebDevelopment", "FullStack", "WordPressHelp"
]

EMAIL_SENDER = "mananop302@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = "manexstore0@gmail.com"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

def log(message):
    print(message, flush=True)

def analyze_with_groq(title, body_text):
    prompt = f"""
    You are an expert SEO, WordPress, and Web Development client filter. 
    Analyze the following Reddit post to determine if the poster is a CLIENT looking to hire someone for SEO, WordPress, or Web Development services.
    
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
        log(f"Groq API Error: {e}")
    
    return False

def send_email(title, link, created_date, subreddit):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"Client Found in r/{subreddit}: {title}"
        
        body = f"Groq AI verified a matching client post!\n\nSubreddit: r/{subreddit}\nTitle: {title}\nDate: {created_date}\nLink: {link}"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        log(f"Email sent successfully for: {title}")
    except Exception as e:
        log(f"Error sending email: {e}")

def check_reddit():
    total_checked = 0
    match_found_count = 0
    
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/new.rss"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0"}
        
        log(f"\nScanning r/{sub}...")
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                namespace = {'atom': 'http://www.w3.org/2005/Atom'}
                entries = root.findall('atom:entry', namespace)
                log(f"Fetched {len(entries)} posts from r/{sub}.")
                
                for entry in entries:
                    total_checked += 1
                    title = entry.find('atom:title', namespace).text
                    link = entry.find('atom:link', namespace).attrib['href']
                    updated = entry.find('atom:updated', namespace).text
                    
                    content_elem = entry.find('atom:content', namespace)
                    body_text = content_elem.text if content_elem is not None and content_elem.text else ''
                    clean_body = re.sub('<[^<]+?>', '', body_text)
                    
                    log(f"[{total_checked}] Checking r/{sub}: '{title[:40]}...'")
                    
                    is_client = analyze_with_groq(title, clean_body)
                    
                    if is_client:
                        log(f"-> MATCH FOUND! Client in r/{sub}.")
                        send_email(title, link, updated, sub)
                        match_found_count += 1
                    else:
                        log("-> Ignored.")
                    
                    time.sleep(2)
            else:
                log(f"Failed or restricted r/{sub} (Status: {response.status_code})")
        except Exception as e:
            log(f"Error checking r/{sub}: {e}")
        
        time.sleep(3)
            
    log(f"\nFinished run. Total posts checked: {total_checked}, Total clients found & emailed: {match_found_count}")

if __name__ == "__main__":
    log("Optimized Multi-Subreddit Groq Client Finder started...")
    check_reddit()
    log("Script finished execution.")
