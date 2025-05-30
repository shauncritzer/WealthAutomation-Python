import os
import requests
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
import random
import re
import time

# --- Import Custom Modules ---
# Ensure these files exist and are correctly implemented
try:
    from jwt_wordpress_integration import JWTWordPressIntegration
    from convertkit_v4_integration import ConvertKitV4Integration
    from affiliate_offer_library import AffiliateOfferLibrary
except ImportError as e:
    print(f"[ERROR] Failed to import required modules: {e}")
    exit(1)

print("🚀 WA script started")
import os
print(f"✅ ENV: WP_USER = {os.getenv('WORDPRESS_USER')}")
# Safely print API key previews with None checks
openai_key = os.getenv('OPENAI_API_KEY')
print(f"✅ ENV: OPENAI = {openai_key[:5] + '...' if openai_key else 'Not set'}")
ck_key = os.getenv('CONVERTKIT_API_KEY_V4')
print(f"✅ ENV: CK = {ck_key[:5] + '...' if ck_key else 'Not set'}")
print("🛠️ Starting modules...")

# --- Configuration & Setup ---
# Load environment variables from .env file if it exists (optional, Railway uses its own env vars)
load_dotenv()

# General Settings
# Use relative paths for Railway compatibility
LOG_DIR = "drop_reports"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
MAIN_LOG_FILE = Path(LOG_DIR) / "wealthautomation_system.log"

# OpenAI (Assuming GPT-4 or similar is used for content generation)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Discord Notifications
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# Make.com Webhook
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")

# --- Logging Function ---
def log_message(message, level="INFO"):
    """Log messages to the main system log file."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    try:
        # Ensure log directory exists
        MAIN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MAIN_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Error writing to main log file {MAIN_LOG_FILE}: {e}")
    # Print errors/warnings to console for visibility
    if level == "ERROR" or level == "WARNING":
        print(log_entry.strip())

# --- Discord Notification Function ---
def send_discord_notification(message, level="INFO"):
    """Send a notification to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        log_message("Discord webhook URL not configured, skipping notification.", "WARNING")
        return

    payload = {
        "content": f"**[{level}]** {message}"
    }
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        log_message(f"Sent Discord notification: {message}")
    except requests.exceptions.RequestException as e:
        log_message(f"Error sending Discord notification: {e}", "ERROR")

# --- Placeholder Content Generation Function ---
def generate_content(topic):
    """Placeholder function to generate blog post and email content."""
    # In a real scenario, this would call OpenAI API
    log_message(f"Generating content for topic: {topic}")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    blog_title = f"{topic} - Key Strategies ({timestamp})"
    blog_content_html = f"<p>This is an in-depth post about {topic}.</p>\n<p>Strategy 1: Do the thing.</p>\n<p>Strategy 2: Do the other thing.</p>\n<p>Conclusion: {topic} is important.</p>"
    email_subject = f"New Post: {topic} Insights"
    email_content_html = f"<p>Hi subscriber,</p>\n<p>Check out our latest post on {topic}:</p>\n<p><em>{blog_title}</em></p>\n<p>Read more for key strategies!</p>"
    
    log_message(f"Generated Blog Title: {blog_title}")
    log_message(f"Generated Email Subject: {email_subject}")
    return blog_title, blog_content_html, email_subject, email_content_html

# --- Main Workflow Function ---
def run_wealthautomation_cycle(topic="Passive Income Automation"):
    """Executes one cycle of the WealthAutomation system."""
    log_message("Starting WealthAutomation cycle...")
    send_discord_notification("WealthAutomation cycle started.", "INFO")

    # 1. Generate Content
    try:
        blog_title, blog_content_html, email_subject, email_content_html = generate_content(topic)
    except Exception as e:
        log_message(f"Content generation failed: {e}", "ERROR")
        send_discord_notification(f"Content generation failed: {e}", "ERROR")
        return # Stop cycle if content generation fails

    # 2. Initialize Integrations
    try:
        wp_integration = JWTWordPressIntegration()
        ck_integration = ConvertKitV4Integration() # Uses API Secret by default now
        offer_library = AffiliateOfferLibrary()
    except Exception as e:
        log_message(f"Failed to initialize integration modules: {e}", "ERROR")
        send_discord_notification(f"Failed to initialize integration modules: {e}", "ERROR")
        return

    # 3. Affiliate Offer Integration
    blog_content_with_cta = blog_content_html
    email_content_with_cta = email_content_html
    selected_offer = None
    try:
        selected_offer = offer_library.match_content_to_offer(blog_content_html, blog_title)
        if selected_offer:
            offer_name = selected_offer.get("name", "N/A")
            log_message(f"Selected affiliate offer: {offer_name}")
            # Inject into Blog Post (Middle Position)
            blog_content_with_cta = offer_library.inject_cta_into_content(blog_content_html, selected_offer, position="middle")
            # Inject into Email (End Position)
            email_content_with_cta = offer_library.inject_cta_into_content(email_content_html, selected_offer, position="end")
            offer_library.log_offer_usage(selected_offer, blog_title, content_type="blog_and_email")
            log_message("Successfully injected CTA into blog and email content.")
        else:
            log_message("No suitable affiliate offer found or library empty.", "WARNING")
    except Exception as e:
        log_message(f"Affiliate offer integration failed: {e}", "ERROR")
        send_discord_notification(f"Affiliate offer integration failed: {e}", "ERROR")
        # Continue without CTA if integration fails

    # 4. Post to WordPress (with Fallback)
    post_id = None
    post_url = None
    wp_fallback_file = None
    wp_auth_method = "Unknown" # Initialize auth method used
    try:
        log_message("Attempting to post to WordPress (JWT preferred, Basic Auth fallback)...")
        # Unpack the four return values, including the auth method used
        post_id, post_url, wp_fallback_file, wp_auth_method = wp_integration.create_post(blog_title, blog_content_with_cta)
        
        if post_id:
            log_message(f"Successfully posted to WordPress using {wp_auth_method} Auth. Post ID: {post_id}, URL: {post_url}", "SUCCESS")
            send_discord_notification(f"New WordPress Post ({wp_auth_method} Auth): {blog_title} - {post_url}", "SUCCESS")
        else:
            # Log failure, mentioning the method attempted/failed
            log_message(f"WordPress posting failed (tried {wp_auth_method} Auth). Fallback file: {wp_fallback_file}", "WARNING")
            send_discord_notification(f"WordPress posting FAILED (tried {wp_auth_method} Auth). Content saved to fallback: {wp_fallback_file}", "WARNING")
            # Specific check for Basic Auth failure
            if wp_auth_method == "Basic":
                 log_message("Basic Auth failed. Check Application Password validity and permissions in WordPress.", "ERROR")
                 send_discord_notification("WordPress Basic Auth failed. Check Application Password/permissions.", "ERROR")
                 
    except Exception as e:
        log_message(f"CRITICAL ERROR during WordPress posting attempt: {e}", "ERROR")
        send_discord_notification(f"CRITICAL ERROR during WordPress posting: {e}", "ERROR")
        # Attempt to save fallback even if the method failed unexpectedly
        if not wp_fallback_file:
             wp_fallback_file = wp_integration._save_fallback(blog_title, blog_content_with_cta)
             if wp_fallback_file:
                  log_message(f"Saved emergency fallback for WP: {wp_fallback_file}", "ERROR")
                  send_discord_notification(f"Saved emergency fallback for WP: {wp_fallback_file}", "ERROR")

    # 5. Send ConvertKit Email Blast (with Fallback)
    email_blast_id = None
    ck_fallback_file = None
    email_sent = False
    try:
        log_message("Attempting to send ConvertKit email blast...")
        # Add blog post URL to email content if post was successful
        final_email_content = email_content_with_cta
        if post_url:
            final_email_content += f"<p>Read the full post here: <a href=\"{post_url}\">{post_url}</a></p>"
        
        email_blast_id, ck_fallback_file, email_sent = ck_integration.create_and_send_broadcast(email_subject, final_email_content)
        if email_blast_id and email_sent:
            log_message(f"Successfully sent ConvertKit email blast. Blast ID: {email_blast_id}", "SUCCESS")
            send_discord_notification(f"ConvertKit Email Sent: {email_subject} (Blast ID: {email_blast_id})", "SUCCESS")
        else:
            log_message(f"ConvertKit email sending failed. Fallback file: {ck_fallback_file}", "WARNING")
            send_discord_notification(f"ConvertKit email sending FAILED. Content saved to fallback: {ck_fallback_file}", "WARNING")
    except Exception as e:
        log_message(f"Error during ConvertKit sending attempt: {e}", "ERROR")
        send_discord_notification(f"CRITICAL ERROR during ConvertKit sending: {e}", "ERROR")
        # Attempt to save fallback even if the method failed unexpectedly
        if not ck_fallback_file:
             ck_fallback_file = ck_integration._save_fallback(email_subject, email_content_with_cta)
             if ck_fallback_file:
                  log_message(f"Saved emergency fallback for CK: {ck_fallback_file}", "ERROR")
                  send_discord_notification(f"Saved emergency fallback for CK: {ck_fallback_file}", "ERROR")

    # 6. Trigger Make.com Webhook (Optional - only if WP post succeeded)
    if post_id and post_url and MAKE_WEBHOOK_URL:
        try:
            log_message("Triggering Make.com webhook...")
            webhook_payload = {
                "event": "new_wordpress_post",
                "post_id": post_id,
                "post_title": blog_title,
                "post_url": post_url,
                "auth_method_used": wp_auth_method, # Include auth method in webhook
                "timestamp": datetime.datetime.now().isoformat()
            }
            response = requests.post(MAKE_WEBHOOK_URL, json=webhook_payload, timeout=15)
            response.raise_for_status()
            log_message(f"Successfully triggered Make.com webhook. Response: {response.text}")
            send_discord_notification(f"Triggered Make.com webhook for post ID {post_id} ({wp_auth_method} Auth)", "INFO")
        except requests.exceptions.RequestException as e:
            log_message(f"Error triggering Make.com webhook: {e}", "ERROR")
            send_discord_notification(f"Make.com webhook trigger FAILED: {e}", "ERROR")
    elif not post_id:
         log_message("Skipping Make.com webhook trigger because WordPress post failed.", "INFO")
    elif not MAKE_WEBHOOK_URL:
         log_message("Make.com webhook URL not configured, skipping trigger.", "INFO")

    log_message("WealthAutomation cycle finished.")
    send_discord_notification("WealthAutomation cycle finished.", "INFO")

# --- Main Execution ---
if __name__ == "__main__":
    log_message("========================================")
    log_message("WealthAutomation System Initializing...")
    log_message("========================================")
    
    # --- Check Essential Credentials ---
    # Added WORDPRESS_APP_PASSWORD as essential for the fallback
    essential_vars = ["OPENAI_API_KEY", "WORDPRESS_USER", "WORDPRESS_JWT_SECRET", "WORDPRESS_APP_PASSWORD", "CONVERTKIT_API_KEY_V4"]
    missing_vars = [var for var in essential_vars if not os.getenv(var)]
    if missing_vars:
        message = f"CRITICAL ERROR: Missing essential environment variables: {', '.join(missing_vars)}. System cannot run."
        log_message(message, "ERROR")
        send_discord_notification(message, "ERROR")
        exit(1)
    else:
        log_message("All essential credentials loaded.")

    # --- Run the Cycle ---
    try:
        # You can replace the topic with dynamic topic generation logic later
        run_wealthautomation_cycle(topic="Advanced AI Monetization Techniques")
    except Exception as e:
        # Catch any unexpected errors during the cycle
        error_message = f"UNHANDLED EXCEPTION in main cycle: {e}"
        log_message(error_message, "ERROR")
        send_discord_notification(error_message, "ERROR")

    log_message("========================================")
    log_message("WealthAutomation System Shutdown.")
    log_message("========================================")

