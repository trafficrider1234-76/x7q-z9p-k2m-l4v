import os
import requests
import smtplib
import time
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random

SUBREDDITS = [
    "forhire", "freelance_forhire", "jobbit",
    "freelance", "digital_marketing", "SEO", "wordpress", "webdev",
    "DesignJobs", "Shopify", "ecommerce", "smallbusiness",
    "startups", "ClientsForHire", "ProgrammingJobs", "WebDesign",
    "LocalSEO", "WebDevelopment", "FullStack", "WordPressHelp"
]

EMAIL_SENDER = "mananop302@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = "manexstore0@gmail.com"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0"
]

def log(message):
    print(message, flush=True)

def analyze_with_groq(title, body_text):
    prompt = f"""
    You are an expert SEO, WordPress, and Web Development client filter. 
    Analyze the following post to determine if the poster is a CLIENT looking to hire someone for SEO, WordPress, or Web Development services.
    
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

def send_run_report(total_checked, found_clients):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        
        if found_clients:
            msg['Subject'] = f"🔥 {len(found_clients)} Client(s) Found! - Multi-Platform Bot Report"
            body = f"Bot run completed successfully!\n\nTotal Posts Checked: {total_checked}\nClients Found: {len(found_clients)}\n\n--- MATCHED CLIENT POSTS ---\n\n"
            for client in found_clients:
                body += f"Platform: {client['platform']} ({client['source']})\nTitle: {client['title']}\nDate: {client['date']}\nDirect URL: {client['link']}\n\n"
        else:
            msg['Subject'] = f"ℹ️ Bot Run Report: No Clients Found ({total_checked} posts)"
            body = f"Bot run completed successfully!\n\nTotal Posts Checked: {total_checked}\nClients Found: 0\n\nNo matching SEO/WordPress clients found in this run. Bot will check again next hour."
            
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        log("Run report email sent successfully.")
    except Exception as e:
        log(f"Error sending email report: {e}")

def check_reddit():
    total_checked = 0
    found_clients = []
    
    for sub in SUBREDDITS:
        url = f"https://www.reddit.com/r/{sub}/new.json?limit=15"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        log(f"\nScanning r/{sub}...")
        try:
            response = requests.get(url, headers=headers)
            log(f"r/{sub} Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                posts = data.get('data', {}).get('children', [])
                log(f"Fetched {len(posts)} posts from r/{sub}.")
                
                for post in posts:
                    total_checked += 1
                    post_data = post['data']
                    title = post_data.get('title', '')
                    permalink = post_data.get('permalink', '')
                    link = f"https://www.reddit.com{permalink}"
                    created_utc = post_data.get('created_utc', time.time())
                    created_date = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(created_utc))
                    body_text = post_data.get('selftext', '')
                    
                    log(f"[{total_checked}] Checking r/{sub}: '{title[:40]}...'")
                    
                    is_client = analyze_with_groq(title, body_text)
                    
                    if is_client:
                        log(f"-> MATCH FOUND! Client in r/{sub}.")
                        found_clients.append({
                            "platform": "Reddit",
                            "source": f"r/{sub}",
                            "title": title,
                            "link": link,
                            "date": created_date
                        })
                    else:
                        log("-> Ignored.")
                    
                    time.sleep(2)
            else:
                log(f"Skipping r/{sub} due to restriction (Status: {response.status_code})")
        except Exception as e:
            log(f"Error checking r/{sub}: {e}")
        
        time.sleep(3)
        
    return total_checked, found_clients

def check_hackernews():
    log("\nScanning Hacker News...")
    url = "https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=50"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    total_checked = 0
    found_clients = []
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', [])
            log(f"Fetched {len(hits)} stories from Hacker News.")
            
            for hit in hits:
                total_checked += 1
                title = hit.get('title', '')
                object_id = hit.get('objectID', '')
                link = f"https://news.ycombinator.com/item?id={object_id}"
                created_at = hit.get('created_at', '')
                body_text = hit.get('story_text', '') or ''
                
                log(f"[HN {total_checked}] Checking HN: '{title[:40]}...'")
                
                is_client = analyze_with_groq(title, body_text)
                
                if is_client:
                    log(f"-> MATCH FOUND! Client on Hacker News.")
                    found_clients.append({
                        "platform": "Hacker News",
                        "source": "HN API",
                        "title": title,
                        "link": link,
                        "date": created_at
                    })
                else:
                    log("-> Ignored.")
                
                time.sleep(1)
    except Exception as e:
        log(f"Error checking Hacker News: {e}")
        
    return total_checked, found_clients

if __name__ == "__main__":
    log("Multi-Platform Client Finder started...")
    
    reddit_checked, reddit_clients = check_reddit()
    hn_checked, hn_clients = check_hackernews()
    
    total_checked = reddit_checked + hn_checked
    all_clients = reddit_clients + hn_clients
    
    log(f"\nFinished full run. Total posts checked: {total_checked}, Total clients found: {len(all_clients)}")
    send_run_report(total_checked, all_clients)
    log("Script finished execution.")
