import os
import requests
from flask import Flask, jsonify, request
from pathlib import Path

# Import the daily poster module
from daily_poster import run_daily_post, log_message, log_verification_status

app = Flask(__name__)

# --- Configuration & Setup ---
# Use relative paths for Railway compatibility
LOG_DIR = "drop_reports"
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
LOG_VERIFICATION_FILE = Path(LOG_DIR) / "log_verification_status.txt"

def get_env(var, default=None):
    value = os.getenv(var)
    if not value:
        print(f"⚠️ Warning: Missing ENV var {var}")
        return default
    return value

OPENAI_API_KEY = get_env("OPENAI_API_KEY")
WORDPRESS_USER = get_env("WORDPRESS_USER")
WORDPRESS_APP_PASSWORD = get_env("WORDPRESS_APP_PASSWORD")
CONVERTKIT_API_KEY = get_env("CONVERTKIT_API_KEY")
CONVERTKIT_BASIC_TAG_ID = get_env("CONVERTKIT_BASIC_TAG_ID")
MAKE_WEBHOOK_URL = get_env("MAKE_WEBHOOK_URL")
GOOGLE_SHEETS_UTM_TRACKER_ID = get_env("GOOGLE_SHEETS_UTM_TRACKER_ID")
DISCORD_WEBHOOK_URL = get_env("DISCORD_WEBHOOK_URL")

@app.route('/')
def index():
    return jsonify({
        "status": "online",
        "service": "WealthAutomationHQ API",
        "endpoints": [
            "/run - Trigger daily blog post",
            "/run_social_post - Trigger social media post (not implemented yet)",
            "/status - Check system status"
        ]
    })

@app.route('/run')
def run():
    try:
        log_message("Endpoint /run triggered")
        log_verification_status("INFO: Endpoint /run triggered")
        
        # Get optional topic parameter
        topic = request.args.get('topic', None)
        
        # Run daily post with the provided topic or let it select one
        success = run_daily_post(topic=topic)
        
        if success:
            response = {
                "status": "success",
                "message": "Daily blog post process completed successfully"
            }
            log_verification_status("SUCCESS: Endpoint /run completed successfully")
            return jsonify(response), 200
        else:
            response = {
                "status": "warning",
                "message": "Daily blog post process completed with warnings or was skipped (possible duplicate)"
            }
            log_verification_status("WARNING: Endpoint /run completed with warnings")
            return jsonify(response), 200
    except Exception as e:
        error_message = f"Error in /run endpoint: {e}"
        log_message(error_message, "ERROR")
        log_verification_status(f"ERROR: Endpoint /run failed: {e}")
        return jsonify({
            "status": "error",
            "message": error_message
        }), 500

@app.route('/run_social_post')
def run_social_post():
    try:
        log_message("Endpoint /run_social_post triggered")
        log_verification_status("INFO: Endpoint /run_social_post triggered")
        
        # This is a placeholder for future social post functionality
        # For now, we'll just log that it was triggered
        log_verification_status("INFO: Social post functionality not implemented yet")
        
        return jsonify({
            "status": "success",
            "message": "Social post functionality not implemented yet"
        }), 200
    except Exception as e:
        error_message = f"Error in /run_social_post endpoint: {e}"
        log_message(error_message, "ERROR")
        log_verification_status(f"ERROR: Endpoint /run_social_post failed: {e}")
        return jsonify({
            "status": "error",
            "message": error_message
        }), 500

@app.route('/status')
def status():
    try:
        # Check if log files exist
        blog_log_exists = Path(LOG_DIR) / "blog_post_log.txt"
        cta_log_exists = Path(LOG_DIR) / "cta_log.txt"
        verification_log_exists = Path(LOG_DIR) / "log_verification_status.txt"
        
        # Get the last few lines of the verification log if it exists
        last_verification = "No verification log found"
        if verification_log_exists.exists():
            try:
                with open(verification_log_exists, "r") as f:
                    lines = f.readlines()
                    last_verification = "".join(lines[-5:]) if lines else "Log file is empty"
            except Exception as e:
                last_verification = f"Error reading log: {e}"
        
        return jsonify({
            "status": "online",
            "service": "WealthAutomationHQ API",
            "logs": {
                "blog_log": blog_log_exists.exists(),
                "cta_log": cta_log_exists.exists(),
                "verification_log": verification_log_exists.exists()
            },
            "last_verification": last_verification,
            "env_vars_set": {
                "OPENAI_API_KEY": bool(OPENAI_API_KEY),
                "WORDPRESS_USER": bool(WORDPRESS_USER),
                "WORDPRESS_APP_PASSWORD": bool(WORDPRESS_APP_PASSWORD),
                "CONVERTKIT_API_KEY": bool(CONVERTKIT_API_KEY),
                "MAKE_WEBHOOK_URL": bool(MAKE_WEBHOOK_URL),
                "GOOGLE_SHEETS_UTM_TRACKER_ID": bool(GOOGLE_SHEETS_UTM_TRACKER_ID),
                "DISCORD_WEBHOOK_URL": bool(DISCORD_WEBHOOK_URL)
            }
        }), 200
    except Exception as e:
        error_message = f"Error in /status endpoint: {e}"
        log_message(error_message, "ERROR")
        return jsonify({
            "status": "error",
            "message": error_message
        }), 500

# Simulated run for confirmation
if __name__ == "__main__":
    print("✅ ENV vars loaded.")
    print("✅ Flask app initialized.")
    print("Ready to trigger automation...")
    
    # For local testing only
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
