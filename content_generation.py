import os
import requests
import json
import datetime
import re
from pathlib import Path
import random
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get OpenAI API key from environment
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

def log_message(message, level="INFO"):
    """Log messages to the console and log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    # Ensure log directory exists
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Append to log file
    try:
        with open(log_dir / "content_generation.log", "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Error writing to log file: {e}")

def select_topic():
    """Select a topic for the blog post from a predefined list, avoiding recent topics."""
    topics = [
        "Passive Income Strategies for Digital Entrepreneurs",
        "AI Tools for Content Creation and Marketing",
        "Building an Automated Email Marketing System",
        "Affiliate Marketing Strategies That Actually Work",
        "Creating Digital Products That Sell While You Sleep",
        "Scaling Your Online Business with Automation",
        "Monetizing Your Expertise Through Online Courses",
        "Building a Personal Brand in the Digital Age",
        "SEO Strategies for Automated Content Systems",
        "Leveraging Social Media for Passive Income"
    ]
    
    # Check for recently used topics
    recent_topics = []
    try:
        drop_reports_dir = Path("drop_reports")
        drop_reports_dir.mkdir(exist_ok=True)
        blog_log_path = drop_reports_dir / "blog_post_log.txt"
        
        if blog_log_path.exists():
            with open(blog_log_path, "r", encoding="utf-8") as f:
                recent_posts = f.readlines()[-5:]  # Get last 5 posts
                for post in recent_posts:
                    for topic in topics:
                        if topic in post:
                            recent_topics.append(topic)
    except Exception as e:
        log_message(f"Error reading recent topics: {e}", "WARNING")
    
    # Filter out recently used topics
    available_topics = [t for t in topics if t not in recent_topics]
    
    # If all topics were recently used, reset and use the full list
    if not available_topics:
        log_message("All topics recently used, resetting topic rotation", "INFO")
        available_topics = topics
    
    # Select a random topic from available ones
    selected_topic = random.choice(available_topics)
    log_message(f"Selected topic: {selected_topic}", "INFO")
    return selected_topic

def generate_content(topic):
    """Generate blog post and email content using OpenAI API."""
    log_message(f"Generating content for topic: {topic}")
    
    # Initialize variables for fallback case
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    blog_title = f"{topic} - Key Strategies ({timestamp})"
    email_subject = f"New Post: {topic} Insights"
    
    if not OPENAI_API_KEY:
        log_message("OpenAI API key not configured", "ERROR")
        # Use fallback content instead of raising an exception
        fallback_blog_content = f"""
        <p>This is an emergency fallback post about {topic}.</p>
        <p>Our regular content generation system is currently experiencing technical difficulties.</p>
        <p>Please check back later for our regularly scheduled content.</p>
        """
        
        fallback_email_content = f"""
        <p>We're preparing some exciting new content about {topic}.</p>
        <p>Due to technical issues, our regular content will be slightly delayed.</p>
        """
        
        log_message("Using emergency fallback content due to missing API key", "WARNING")
        return blog_title, fallback_blog_content, email_subject, fallback_email_content
    
    # Construct the prompt for the blog post
    blog_prompt = f"""
    Write a comprehensive, in-depth blog post about {topic}.
    
    The blog post should:
    - Have a professional, authoritative tone
    - Include at least 5 specific strategies or techniques
    - Provide actionable advice that readers can implement
    - Include examples where appropriate
    - Be at least 1000 words in length
    - Format the content with proper HTML tags (<p>, <h2>, <h3>, <ul>, <li>, etc.)
    
    Do not include a title or introduction saying "Introduction" - start directly with engaging content.
    """
    
    # Call OpenAI API for blog content
    try:
        log_message("Calling OpenAI API for blog content...")
        blog_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are an expert content writer specializing in digital marketing, online business, and wealth automation."},
                    {"role": "user", "content": blog_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2500
            },
            timeout=60
        )
        blog_response.raise_for_status()
        blog_content_html = blog_response.json()["choices"][0]["message"]["content"]
        log_message("Successfully generated blog content")
        
        # Construct the prompt for the email
        email_prompt = f"""
        Write an engaging email to announce a new blog post about {topic}.
        
        The email should:
        - Have a friendly, conversational tone
        - Highlight 2-3 key points from the blog post
        - Create curiosity to encourage clicking through to the full post
        - Be concise (150-200 words)
        - Format with proper HTML tags (<p>, <strong>, etc.)
        
        Do not include a greeting like "Hi [Name]" - start with engaging content.
        """
        
        # Call OpenAI API for email content
        log_message("Calling OpenAI API for email content...")
        email_response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an expert email copywriter specializing in engaging newsletter content."},
                    {"role": "user", "content": email_prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 500
            },
            timeout=30
        )
        email_response.raise_for_status()
        email_content_html = email_response.json()["choices"][0]["message"]["content"]
        log_message("Successfully generated email content")
        
        # Basic content quality validation
        if len(blog_content_html) < 500:
            log_message("Generated blog content is too short, may need regeneration", "WARNING")
            
        if not re.search(r'<h[2-3]|<p>', blog_content_html):
            log_message("Generated blog content lacks proper HTML formatting, adding basic formatting", "WARNING")
            # Add basic formatting
            formatted_content = blog_content_html.replace('\n\n', '</p><p>')
            blog_content_html = f"<p>{formatted_content}</p>"
        
        log_message(f"Successfully generated content for topic: {topic}")
        log_message(f"Generated Blog Title: {blog_title}")
        log_message(f"Generated Email Subject: {email_subject}")
        
        # Log the generated content for debugging
        drop_reports_dir = Path("drop_reports")
        drop_reports_dir.mkdir(exist_ok=True)
        
        # Log blog post details
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        blog_log_entry = f"{timestamp_str} | {blog_title} | {len(blog_content_html)} chars\n"
        with open(drop_reports_dir / "blog_post_log.txt", "a", encoding="utf-8") as f:
            f.write(blog_log_entry)
        
        # Update verification status
        with open(drop_reports_dir / "log_verification_status.txt", "a", encoding="utf-8") as f:
            f.write(f"{timestamp_str} | Content generation successful | {topic}\n")
        
        return blog_title, blog_content_html, email_subject, email_content_html
        
    except requests.exceptions.RequestException as e:
        log_message(f"Error calling OpenAI API: {e}", "ERROR")
        
        # Provide emergency fallback content
        fallback_blog_content = f"""
        <p>This is an emergency fallback post about {topic}.</p>
        <p>Our regular content generation system is currently experiencing technical difficulties.</p>
        <p>Please check back later for our regularly scheduled content.</p>
        <p>In the meantime, you might be interested in exploring our previous posts on similar topics.</p>
        """
        
        fallback_email_content = f"""
        <p>We're preparing some exciting new content about {topic}.</p>
        <p>Due to technical issues, our regular content will be slightly delayed.</p>
        <p>Please check back on our website soon for the latest updates.</p>
        """
        
        # Log the error
        drop_reports_dir = Path("drop_reports")
        drop_reports_dir.mkdir(exist_ok=True)
        timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(drop_reports_dir / "log_verification_status.txt", "a", encoding="utf-8") as f:
            f.write(f"{timestamp_str} | Content generation failed: {e} | {topic}\n")
        
        log_message("Using emergency fallback content due to API failure", "WARNING")
        return blog_title, fallback_blog_content, email_subject, fallback_email_content
