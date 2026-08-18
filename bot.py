import os
import time
import smtplib
import requests
import praw
import prawcore
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SUBREDDITS = [
    "forhire", "freelance_forhire", "jobbit",
    "freelance", "digital_marketing", "SEO", "wordpress", "webdev",
    "DesignJobs", "Shopify", "ecommerce", "smallbusiness",
    "startups", "ClientsForHire", "ProgrammingJobs", "WebDesign",
    "LocalSEO", "WebDevelopment", "FullStack", "WordPressHelp",
]

EMAIL_SENDER = "mananop302@gmail.com"
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = "manexstore0@gmail.com"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = "ClientFinderBot/1.0 (by u/your_username)"

MAX_RETRIES = 3
BASE_BACKOFF = 5  # seconds, doubles each retry


def log(message):
    print(message, flush=True)


def get_reddit():
    """Single authenticated Reddit client, reused across the run."""
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
    )


def with_retries(fn, *args, what="operation", **kwargs):
    """
    Run fn(*args, **kwargs). On failure, retry with exponential backoff.
    Never raises — returns None on final failure so the run continues
    instead of crashing.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn(*args, **kwargs)
        except prawcore.exceptions.TooManyRequests as e:
            wait = BASE_BACKOFF * (2 ** (attempt - 1))
            log(f"[{what}] rate-limited, waiting {wait}s (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(wait)
        except prawcore.exceptions.ServerError as e:
            wait = BASE_BACKOFF * (2 ** (attempt - 1))
            log(f"[{what}] server error: {e}, retrying in {wait}s")
            time.sleep(wait)
        except prawcore.exceptions.Forbidden:
            log(f"[{what}] forbidden (private/banned subreddit?) - skipping")
            return None
        except prawcore.exceptions.NotFound:
            log(f"[{what}] not found - skipping")
            return None
        except Exception as e:
            log(f"[{what}] unexpected error: {e} (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(BASE_BACKOFF)
    log(f"[{what}] giving up after {MAX_RETRIES} attempts")
    return None


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
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload, headers=headers, timeout=20,
            )
            if response.status_code == 200:
                result = response.json()
                answer = result["choices"][0]["message"]["content"].strip().upper()
                return "YES" in answer
            elif response.status_code == 429:
                wait = BASE_BACKOFF * (2 ** (attempt - 1))
                log(f"[groq] rate-limited, waiting {wait}s")
                time.sleep(wait)
            else:
                log(f"[groq] status {response.status_code}, skipping this post")
                return False
        except requests.exceptions.RequestException as e:
            log(f"[groq] request error: {e} (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(BASE_BACKOFF)

    log("[groq] giving up on this post, defaulting to NO")
    return False


def check_reddit():
    total_checked = 0
    found_clients = []

    reddit = with_retries(get_reddit, what="reddit-auth")
    if reddit is None:
        log("Could not authenticate with Reddit this run - skipping Reddit entirely.")
        return total_checked, found_clients

    for sub in SUBREDDITS:
        log(f"\nScanning r/{sub}...")

        posts = with_retries(
            lambda: list(reddit.subreddit(sub).new(limit=15)),
            what=f"r/{sub}",
        )
        if posts is None:
            continue  # this subreddit failed after retries - move on, don't crash

        log(f"Fetched {len(posts)} posts from r/{sub}.")

        for post in posts:
            total_checked += 1
            title = post.title
            body_text = post.selftext or ""
            link = f"https://www.reddit.com{post.permalink}"
            created_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(post.created_utc))

            log(f"[{total_checked}] Checking r/{sub}: '{title[:40]}...'")

            is_client = analyze_with_groq(title, body_text)

            if is_client:
                log(f"-> MATCH FOUND! Client in r/{sub}.")
                found_clients.append({
                    "platform": "Reddit",
                    "source": f"r/{sub}",
                    "title": title,
                    "link": link,
                    "date": created_date,
                })
            else:
                log("-> Ignored.")

            time.sleep(1)  # gentle pacing, well within OAuth rate limits

        time.sleep(1)

    return total_checked, found_clients


def check_hackernews():
    log("\nScanning Hacker News...")
    url = "https://hn.algolia.com/api/v1/search_by_date?tags=story&hitsPerPage=50"

    total_checked = 0
    found_clients = []

    data = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=20)
            if response.status_code == 200:
                data = response.json()
                break
            else:
                wait = BASE_BACKOFF * (2 ** (attempt - 1))
                log(f"[HN] status {response.status_code}, retrying in {wait}s")
                time.sleep(wait)
        except requests.exceptions.RequestException as e:
            log(f"[HN] request error: {e}, attempt {attempt}/{MAX_RETRIES}")
            time.sleep(BASE_BACKOFF)

    if data is None:
        log("Could not reach Hacker News this run - skipping.")
        return total_checked, found_clients

    hits = data.get("hits", [])
    log(f"Fetched {len(hits)} stories from Hacker News.")

    for hit in hits:
        total_checked += 1
        title = hit.get("title", "")
        object_id = hit.get("objectID", "")
        link = f"https://news.ycombinator.com/item?id={object_id}"
        created_at = hit.get("created_at", "")
        body_text = hit.get("story_text", "") or ""

        log(f"[HN {total_checked}] Checking HN: '{title[:40]}...'")

        is_client = analyze_with_groq(title, body_text)

        if is_client:
            log("-> MATCH FOUND! Client on Hacker News.")
            found_clients.append({
                "platform": "Hacker News",
                "source": "HN API",
                "title": title,
                "link": link,
                "date": created_at,
            })
        else:
            log("-> Ignored.")

        time.sleep(1)

    return total_checked, found_clients


def send_run_report(total_checked, found_clients):
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        if found_clients:
            msg["Subject"] = f"{len(found_clients)} Client(s) Found! - Bot Report"
            body = f"Bot run completed.\n\nTotal Posts Checked: {total_checked}\nClients Found: {len(found_clients)}\n\n--- MATCHED CLIENT POSTS ---\n\n"
            for client in found_clients:
                body += f"Platform: {client['platform']} ({client['source']})\nTitle: {client['title']}\nDate: {client['date']}\nDirect URL: {client['link']}\n\n"
        else:
            msg["Subject"] = f"Bot Run Report: No Clients Found ({total_checked} posts)"
            body = f"Bot run completed.\n\nTotal Posts Checked: {total_checked}\nClients Found: 0\n\nNo matching clients this run."

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=20)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        log("Run report email sent successfully.")
    except Exception as e:
        log(f"Error sending email report: {e}")


if __name__ == "__main__":
    log("Client Finder Bot started...")

    reddit_checked, reddit_clients = check_reddit()
    hn_checked, hn_clients = check_hackernews()

    total_checked = reddit_checked + hn_checked
    all_clients = reddit_clients + hn_clients

    log(f"\nFinished run. Total posts checked: {total_checked}, Total clients found: {len(all_clients)}")
    send_run_report(total_checked, all_clients)
    log("Script finished execution.")
