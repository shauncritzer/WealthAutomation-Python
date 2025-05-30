import os
import json
import datetime
from pathlib import Path
import re
import requests
import time
import random

# Import the main system module
from wealthautomation_full_system import run_wealthautomation_cycle, log_message, send_discord_notification

# --- Configuration & Setup ---
# Use relative paths for Railway compatibility
LOG_DIR = "drop_reports"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
BLOG_POST_LOG_FILE = Path(LOG_DIR) / "blog_post_log.txt"
CTA_LOG_FILE = Path(LOG_DIR) / "cta_log.txt"
LOG_VERIFICATION_FILE = Path(LOG_DIR) / "log_verification_status.txt"

# Google Sheets fallback for log verification (if local logs are unavailable)
GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_UTM_TRACKER_ID")
GOOGLE_SHEETS_API_KEY = os.getenv("GOOGLE_SHEETS_API_KEY")

# Define a list of rotating topics to prevent repetition
ROTATING_TOPICS = [
    "Advanced AI Monetization Techniques",
    "Passive Income Strategies for Digital Entrepreneurs",
    "Scaling Your Online Business with Automation",
    "AI Tools for Business Growth and Efficiency",
    "Wealth Building Through Digital Assets",
    "Affiliate Marketing Optimization Strategies",
    "Content Monetization in the AI Era",
    "Automated Sales Funnels That Convert",
    "Digital Product Creation and Scaling",
    "Leveraging AI for Passive Revenue Streams"
]

def load_recent_blog_posts():
    """
    Load recent blog posts from the log file to prevent duplicates.
    Returns a list of recent blog post titles and timestamps.
    """
    recent_posts = []
    
    # Try to read from local log file first
    if BLOG_POST_LOG_FILE.exists():
        try:
            with open(BLOG_POST_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Extract title and timestamp from log entry
                        # Expected format: [YYYY-MM-DD HH:MM:SS] Blog Title
                        match = re.match(r'\[(.*?)\] (.*)', line)
                        if match:
                            timestamp_str, title = match.groups()
                            try:
                                timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                recent_posts.append({"title": title, "timestamp": timestamp})
                            except ValueError:
                                log_message(f"Invalid timestamp format in blog log: {timestamp_str}", "WARNING")
            
            log_message(f"Loaded {len(recent_posts)} recent blog posts from local log file.")
            log_verification_status("SUCCESS: Loaded blog posts from local log file.")
            return recent_posts
        except Exception as e:
            log_message(f"Error reading blog post log file: {e}", "ERROR")
    
    # If local log file doesn't exist or had errors, try Google Sheets fallback
    if GOOGLE_SHEETS_ID and GOOGLE_SHEETS_API_KEY:
        try:
            log_message("Attempting to fetch recent blog posts from Google Sheets fallback...")
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEETS_ID}/values/Blog_Posts!A:B?key={GOOGLE_SHEETS_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "values" in data and len(data["values"]) > 1:  # Skip header row
                for row in data["values"][1:]:  # Skip header row
                    if len(row) >= 2:
                        timestamp_str, title = row[0], row[1]
                        try:
                            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            recent_posts.append({"title": title, "timestamp": timestamp})
                        except ValueError:
                            continue  # Skip invalid timestamps
            
            log_message(f"Loaded {len(recent_posts)} recent blog posts from Google Sheets fallback.")
            log_verification_status("SUCCESS: Loaded blog posts from Google Sheets fallback.")
            return recent_posts
        except Exception as e:
            log_message(f"Error fetching blog posts from Google Sheets fallback: {e}", "ERROR")
    
    log_message("Could not load recent blog posts from any source.", "WARNING")
    log_verification_status("WARNING: Could not load recent blog posts from any source.")
    return []

def load_recent_ctas():
    """
    Load recent CTAs from the log file to prevent duplicates.
    Returns a list of recent CTA offers used.
    """
    recent_ctas = []
    
    # Try to read from local log file first
    if CTA_LOG_FILE.exists():
        try:
            with open(CTA_LOG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        # Extract offer name and timestamp from log entry
                        # Expected format: [YYYY-MM-DD HH:MM:SS] Offer Name
                        match = re.match(r'\[(.*?)\] (.*)', line)
                        if match:
                            timestamp_str, offer_name = match.groups()
                            try:
                                timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                recent_ctas.append({"offer_name": offer_name, "timestamp": timestamp})
                            except ValueError:
                                log_message(f"Invalid timestamp format in CTA log: {timestamp_str}", "WARNING")
            
            log_message(f"Loaded {len(recent_ctas)} recent CTAs from local log file.")
            log_verification_status("SUCCESS: Loaded CTAs from local log file.")
            return recent_ctas
        except Exception as e:
            log_message(f"Error reading CTA log file: {e}", "ERROR")
    
    # If local log file doesn't exist or had errors, try Google Sheets fallback
    if GOOGLE_SHEETS_ID and GOOGLE_SHEETS_API_KEY:
        try:
            log_message("Attempting to fetch recent CTAs from Google Sheets fallback...")
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEETS_ID}/values/CTAs!A:B?key={GOOGLE_SHEETS_API_KEY}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "values" in data and len(data["values"]) > 1:  # Skip header row
                for row in data["values"][1:]:  # Skip header row
                    if len(row) >= 2:
                        timestamp_str, offer_name = row[0], row[1]
                        try:
                            timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                            recent_ctas.append({"offer_name": offer_name, "timestamp": timestamp})
                        except ValueError:
                            continue  # Skip invalid timestamps
            
            log_message(f"Loaded {len(recent_ctas)} recent CTAs from Google Sheets fallback.")
            log_verification_status("SUCCESS: Loaded CTAs from Google Sheets fallback.")
            return recent_ctas
        except Exception as e:
            log_message(f"Error fetching CTAs from Google Sheets fallback: {e}", "ERROR")
    
    log_message("Could not load recent CTAs from any source.", "WARNING")
    log_verification_status("WARNING: Could not load recent CTAs from any source.")
    return []

def is_duplicate_blog_post(topic, recent_posts, days_window=7):
    """
    Check if a blog post topic is a duplicate within the specified time window.
    This function now compares the base topic without timestamps or formatting.
    """
    if not recent_posts:
        return False
    
    now = datetime.datetime.now()
    window_start = now - datetime.timedelta(days=days_window)
    
    # Normalize the topic for comparison (remove special chars, lowercase)
    normalized_topic = re.sub(r'[^a-zA-Z0-9\s]', '', topic).lower().strip()
    
    for post in recent_posts:
        post_title = post["title"]
        post_timestamp = post["timestamp"]
        
        # Extract the base post title without timestamp and normalize
        # Remove any timestamp pattern like (YYYY-MM-DD HH:MM) or - Key Strategies
        base_post_title = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\)\s*', '', post_title)
        base_post_title = re.sub(r'\s*-\s*Key\s+Strategies.*', '', base_post_title)
        normalized_post_title = re.sub(r'[^a-zA-Z0-9\s]', '', base_post_title).lower().strip()
        
        # Check if normalized topics match and post is within time window
        if normalized_topic == normalized_post_title and post_timestamp >= window_start:
            log_message(f"Duplicate blog post detected: '{topic}' matches '{post_title}' from {post_timestamp}", "WARNING")
            return True
    
    return False

def is_duplicate_cta(offer_name, recent_ctas, days_window=3):
    """
    Check if a CTA offer has been used recently within the specified time window.
    """
    if not recent_ctas:
        return False
    
    now = datetime.datetime.now()
    window_start = now - datetime.timedelta(days=days_window)
    
    # Normalize the offer name for comparison
    normalized_offer = offer_name.lower().strip()
    
    for cta in recent_ctas:
        cta_offer = cta["offer_name"]
        cta_timestamp = cta["timestamp"]
        
        # Normalize the CTA offer name
        normalized_cta = cta_offer.lower().strip()
        
        # Check if normalized offer names match and CTA is within time window
        if normalized_offer == normalized_cta and cta_timestamp >= window_start:
            log_message(f"Duplicate CTA detected: '{offer_name}' was used on {cta_timestamp}", "WARNING")
            return True
    
    return False

def log_blog_post(title):
    """
    Log a blog post to the blog post log file.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {title}\n"
    
    try:
        with open(BLOG_POST_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        log_message(f"Logged blog post: {title}")
        
        # Also log to Google Sheets if available (for redundancy)
        if GOOGLE_SHEETS_ID and GOOGLE_SHEETS_API_KEY:
            try:
                # This is a simplified example - in production, use a proper Google Sheets API client
                log_message("Logging blog post to Google Sheets (not implemented in this example)")
            except Exception as e:
                log_message(f"Error logging blog post to Google Sheets: {e}", "WARNING")
    except Exception as e:
        log_message(f"Error logging blog post: {e}", "ERROR")

def log_cta(offer_name):
    """
    Log a CTA to the CTA log file.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {offer_name}\n"
    
    try:
        with open(CTA_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
        log_message(f"Logged CTA: {offer_name}")
        
        # Also log to Google Sheets if available (for redundancy)
        if GOOGLE_SHEETS_ID and GOOGLE_SHEETS_API_KEY:
            try:
                # This is a simplified example - in production, use a proper Google Sheets API client
                log_message("Logging CTA to Google Sheets (not implemented in this example)")
            except Exception as e:
                log_message(f"Error logging CTA to Google Sheets: {e}", "WARNING")
    except Exception as e:
        log_message(f"Error logging CTA: {e}", "ERROR")

def log_verification_status(status):
    """
    Log the verification status to the log verification file.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {status}\n"
    
    try:
        with open(LOG_VERIFICATION_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error logging verification status: {e}")

def select_topic():
    """
    Select a topic from the rotating topics list that hasn't been used recently.
    """
    recent_posts = load_recent_blog_posts()
    
    # Try to find a topic that hasn't been used in the last 7 days
    available_topics = list(ROTATING_TOPICS)  # Create a copy to avoid modifying the original
    random.shuffle(available_topics)  # Randomize the order
    
    for topic in available_topics:
        if not is_duplicate_blog_post(topic, recent_posts):
            log_message(f"Selected topic: {topic}")
            return topic
    
    # If all topics have been used recently, pick the least recently used one
    if recent_posts:
        # Sort posts by timestamp (oldest first)
        sorted_posts = sorted(recent_posts, key=lambda x: x["timestamp"])
        oldest_post = sorted_posts[0]
        
        # Extract the base topic from the oldest post
        oldest_title = oldest_post["title"]
        base_title = re.sub(r'\s*\(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}\)\s*', '', oldest_title)
        base_title = re.sub(r'\s*-\s*Key\s+Strategies.*', '', base_title)
        
        # Find the closest match in our rotating topics
        for topic in ROTATING_TOPICS:
            if topic.lower() in base_title.lower():
                log_message(f"All topics used recently. Selected least recent topic: {topic}")
                return topic
    
    # Fallback to a random topic if we couldn't find a match
    random_topic = random.choice(ROTATING_TOPICS)
    log_message(f"Fallback to random topic: {random_topic}")
    return random_topic

def run_daily_post(topic=None):
    """
    Run the daily blog post with duplicate prevention.
    If no topic is provided, one will be selected from the rotating topics list.
    """
    log_message("Starting daily blog post process...")
    log_verification_status("INFO: Starting daily blog post process")
    
    # Load recent blog posts and CTAs
    recent_posts = load_recent_blog_posts()
    recent_ctas = load_recent_ctas()
    
    # Select a topic if none provided
    if topic is None:
        topic = select_topic()
    else:
        # Check if the provided topic is a duplicate
        if is_duplicate_blog_post(topic, recent_posts):
            log_message(f"Provided topic '{topic}' was used recently. Selecting a different topic.", "WARNING")
            topic = select_topic()
    
    # Generate a timestamp for the blog title
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    blog_title = f"{topic} - Key Strategies ({timestamp})"
    
    # Run the WealthAutomation cycle
    try:
        run_wealthautomation_cycle(topic)
        
        # Log the blog post
        log_blog_post(blog_title)
        
        # Note: CTA logging should ideally be done within the affiliate_offer_library.py
        # when an offer is selected, but we're adding a placeholder here
        # In a real implementation, we would extract the selected offer from the return value
        # of run_wealthautomation_cycle and log it here
        
        log_message("Daily blog post process completed successfully.")
        log_verification_status("SUCCESS: Daily blog post process completed")
        return True
    except Exception as e:
        log_message(f"Error in daily blog post process: {e}", "ERROR")
        log_verification_status(f"ERROR: Daily blog post process failed: {e}")
        send_discord_notification(f"Daily blog post process failed: {e}", "ERROR")
        return False

if __name__ == "__main__":
    print("🚀 Daily Poster starting...")
    run_daily_post()
