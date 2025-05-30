import os
import requests
import json
import base64
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Define a standard browser User-Agent
BROWSER_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"

class JWTWordPressIntegration:
    """Handles WordPress integration using JWT authentication."""

    def __init__(self):
        """Initialize with credentials from environment variables."""
        load_dotenv() # Load .env file in the current directory if it exists (for local testing)
        self.wp_user = os.getenv("WORDPRESS_USER")
        self.wp_app_password = os.getenv("WORDPRESS_APP_PASSWORD") # Still needed for JWT token generation
        self.wp_endpoint = os.getenv("WORDPRESS_API_URL", "https://wealthautomationhq.com/wp-json/wp/v2/posts")
        self.jwt_token = None
        self.log_dir = Path("drop_reports")
        self.fallback_dir = self.log_dir / "wp_fallback" # Keep for failed posts, not auth fallback
        self.log_file = self.log_dir / "jwt_wordpress_integration.log"
        self._ensure_dirs_exist()
        self._log("JWTWordPressIntegration initialized (JWT only).")
        self._get_jwt_token() # Attempt to get token on init

    def _ensure_dirs_exist(self):
        """Create log and fallback directories if they don't exist."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.fallback_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating directories {self.log_dir} or {self.fallback_dir}: {e}")

    def _log(self, message, level="INFO"):
        """Log messages to a file."""
        if not self.log_dir.exists():
            print(f"[{level}] {message} (Logging disabled: log directory {self.log_dir} missing)")
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_message)
        except Exception as e:
             print(f"Error writing to log file {self.log_file}: {e}")
             
        if level == "ERROR" or level == "WARNING":
            print(log_message.strip())

    def _get_jwt_token(self):
        """Obtain JWT token from WordPress. Returns True on success, False otherwise."""
        self._log("Attempting to obtain JWT token.")
        if not self.wp_user or not self.wp_app_password:
            self._log("Missing WORDPRESS_USER or WORDPRESS_APP_PASSWORD for JWT token generation", "ERROR")
            return False

        base_api_url = os.getenv("WORDPRESS_API_URL", "").replace("/wp/v2/posts", "")
        if not base_api_url:
             self._log("Missing WORDPRESS_API_URL in environment variables", "ERROR")
             return False
        token_endpoint = f"{base_api_url}/jwt-auth/v1/token"
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": BROWSER_USER_AGENT 
        }
        data = {
            "username": self.wp_user,
            "password": self.wp_app_password.replace(" ", "")
        }
        
        self._log(f"--- JWT Token Request --- START ---")
        self._log(f"Request URL: POST {token_endpoint}")
        self._log(f"Request Body Keys: {list(data.keys())}") 
        self._log(f"--- JWT Token Request --- SENDING ---")
        
        response = None
        try:
            response = requests.post(token_endpoint, headers=headers, json=data, timeout=30)
            response.raise_for_status() 
            
            try:
                token_data = response.json()
                if "token" in token_data:
                    self.jwt_token = token_data["token"]
                    self._log("Successfully obtained JWT token")
                    self._log(f"--- JWT Token Request --- SUCCESS ---")
                    return True
                else:
                    self._log(f"Failed to obtain JWT token. Response JSON: {token_data}", "ERROR")
                    self._log(f"--- JWT Token Request --- FAILED (No Token in JSON) ---")
                    self._log_response_details(response, "JWT Token Response (No Token)")
                    return False
            except requests.exceptions.JSONDecodeError as json_err:
                self._log(f"Error obtaining JWT token: JSONDecodeError - {json_err}", "ERROR")
                self._log(f"--- JWT Token Response (JSON Decode Error) --- START ---")
                self._log(f"Response Status Code: {response.status_code}", "ERROR")
                self._log(f"Response Body (RAW): {response.text[:1000] + ('...' if len(response.text) > 1000 else '')}", "ERROR")
                self._log(f"--- JWT Token Response (JSON Decode Error) --- END ---")
                return False # No specific error type needed now
                
        except requests.exceptions.RequestException as e:
            self._log(f"Error obtaining JWT token: {e}", "ERROR")
            if response is not None:
                 self._log_response_details(response, "JWT Token Response (Request Error)")
            else:
                 self._log(f"--- JWT Token Request --- FAILED (No Response Object) ---")
            return False

    def _get_auth_header(self):
        """Return the JWT authentication header."""
        self._log("Attempting to use JWT authentication...")

        if self.jwt_token:
            self._log("Using existing JWT token.")
            return {
                "Authorization": f"Bearer {self.jwt_token}",
                "User-Agent": BROWSER_USER_AGENT
            }

        self._log("No valid JWT token found, attempting to refresh.")
        if self._get_jwt_token(): # This will set self.jwt_token on success
            self._log("Successfully refreshed JWT token.")
            return {
                "Authorization": f"Bearer {self.jwt_token}",
                "User-Agent": BROWSER_USER_AGENT
            }
        else:
            self._log("Failed to refresh JWT token. Cannot create auth header.", "ERROR")
            return None

    def _log_response_details(self, response, context="Response Details"):
        """Helper function to log response status, headers, and body."""
        self._log(f"--- {context} --- START ---")
        self._log(f"Response Status Code: {response.status_code}", "ERROR")
        response_text = response.text[:1000] + ("..." if len(response.text) > 1000 else "")
        self._log(f"Response Body: {response_text}", "ERROR")
        self._log(f"--- {context} --- END ---")

    def create_post(self, title, content, status="publish"):
        """Create a new post in WordPress using JWT authentication."""
        headers = self._get_auth_header()
        if not headers:
            self._log("Failed to get JWT authentication header. Cannot create post.", "ERROR")
            return None, None, self._save_fallback(title, content), "JWT Auth Failure"
        
        self._log(f"Attempting to create post using JWT Auth: 	{title[:60]}...	", "INFO")
        
        headers["Content-Type"] = "application/json"
        data = {
            "title": title,
            "content": content,
            "status": status
        }
        
        response = None
        try:
            response = requests.post(self.wp_endpoint, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            try:
                post_data = response.json()
                post_id = post_data.get("id")
                post_url = post_data.get("link")
                if post_id and post_url:
                    self._log(f"Successfully created post using JWT Auth. ID: {post_id}, URL: {post_url}")
                    return post_id, post_url, None, "JWT"
                else:
                    self._log(f"Post created (JWT Auth) but response missing ID/URL. Response: {post_data}", "WARNING")
                    return None, None, self._save_fallback(title, content), "JWT"
            except requests.exceptions.JSONDecodeError as json_err:
                self._log(f"Error decoding JSON response for create_post (JWT Auth): {json_err}", "ERROR")
                self._log_response_details(response, f"Create Post JSON Decode Error (JWT Auth)")
                return None, None, self._save_fallback(title, content), "JWT"
                
        except requests.exceptions.RequestException as e:
            self._log(f"Error creating post (JWT Auth): {e}", "ERROR")
            if response is not None:
                 self._log_response_details(response, f"Create Post Request Error (JWT Auth)")
            fallback_file = self._save_fallback(title, content)
            return None, None, fallback_file, "JWT"

    def _save_fallback(self, title, content):
        """Save post content locally if API call fails."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:50]
        fallback_filename = self.fallback_dir / f"wp_fallback_{timestamp}_{safe_title}.html"
        try:
            fallback_filename.parent.mkdir(parents=True, exist_ok=True)
            with open(fallback_filename, "w", encoding="utf-8") as f:
                f.write(f"<h1>{title}</h1>\n{content}")
            self._log(f"Saved fallback content to {fallback_filename}", "WARNING")
            return str(fallback_filename)
        except Exception as e:
            self._log(f"Error saving fallback file: {e}", "ERROR")
            return None

# Example usage (for testing)
if __name__ == "__main__":
    print("--- Initializing WordPress Integration (JWT Only) ---")
    wp_integration = JWTWordPressIntegration()
    
    print("\n--- Testing Create Post (JWT Auth) ---")
    test_title_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    test_title = f"JWT Only Test Post - {test_title_timestamp}"
    test_content = "<p>This post tests the JWT-only authentication mechanism.</p>"
    
    post_id, post_url, fallback_file, method_used = wp_integration.create_post(test_title, test_content)
    
    print(f"\n--- Create Post Result ---")
    print(f"Authentication Method Attempted/Used: {method_used}")
    if post_id:
        print(f"Successfully created post: {post_url}")
    else:
        print(f"Failed to create post.")
        if fallback_file:
            print(f"Fallback content saved to: {fallback_file}")
        else:
            print("Fallback file could not be saved.")

