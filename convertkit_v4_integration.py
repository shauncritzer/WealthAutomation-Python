import os
import requests
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

class ConvertKitV4Integration:
    """Handles Kit (formerly ConvertKit) integration using the V4 API."""

    def __init__(self):
        """Initialize with credentials from environment variables."""
        load_dotenv() # Load .env file in the current directory if it exists (for local testing)
        self.api_secret = os.getenv("CONVERTKIT_API_SECRET") 
        self.api_key_v4 = os.getenv("CONVERTKIT_API_KEY_V4") # Now prioritize this for auth
        # Updated base URL for Kit API V4
        self.base_url = "https://api.kit.com/v4" 
        # Use relative paths for Railway compatibility
        self.log_dir = Path("drop_reports")
        self.fallback_dir = self.log_dir / "ck_fallback"
        self.log_file = self.log_dir / "convertkit_v4_integration.log"
        # Ensure directories exist
        self._ensure_dirs_exist()
        self._log("Kit V4 Integration initialized")
        if not self.api_key_v4:
            # Log error if V4 key is missing, as we are now trying it for auth
            self._log("Missing CONVERTKIT_API_KEY_V4 in environment variables", "ERROR")
        if not self.api_secret:
            self._log("Missing CONVERTKIT_API_SECRET in environment variables", "WARNING") # Log warning for secret

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

    def _get_headers(self):
        """Return the authorization header for API requests using API Key V4."""
        if not self.api_key_v4:
            self._log("API Key V4 not available for headers", "ERROR")
            return None
        return {
            "X-Kit-Api-Key": self.api_key_v4, 
            "Content-Type": "application/json"
        }

    def get_forms(self):
        """Retrieve forms from Kit."""
        headers = self._get_headers()
        if not headers:
            return []
            
        # Updated endpoint path if necessary (assuming /forms is still correct)
        endpoint = f"{self.base_url}/forms"
        self._log(f"Attempting to get forms from {endpoint} using API Key V4")
        try:
            response = requests.get(endpoint, headers=headers, timeout=30)
            response.raise_for_status()
            forms_data = response.json()
            forms = forms_data.get("forms", [])
            self._log(f"Successfully retrieved {len(forms)} forms using API Key V4")
            return forms
        except requests.exceptions.RequestException as e:
            self._log(f"Error getting forms using API Key V4: {e}", "ERROR")
            if hasattr(e, 'response') and e.response is not None:
                 self._log(f"Response status: {e.response.status_code}", "ERROR")
                 self._log(f"Response text: {e.response.text}", "ERROR")
            return []

    def create_and_send_broadcast(self, subject, content):
        """Create and automatically send a broadcast using Kit V4 API."""
        headers = self._get_headers()
        if not headers:
            self._log("Cannot create broadcast, headers unavailable (missing API Key V4?).", "ERROR")
            return None, self._save_fallback(subject, content), False
            
        # Updated endpoint for creating broadcasts
        endpoint = f"{self.base_url}/broadcasts" 
        data = {
            "subject": subject,
            "content": content
            # V4 sends immediately upon creation
        }
        self._log(f"Attempting to create and send broadcast to {endpoint} using API Key V4", "INFO")
        try:
            response = requests.post(endpoint, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            broadcast_data = response.json()
            # Updated key check for broadcast ID
            broadcast_id = broadcast_data.get("broadcast", {}).get("id") 
            
            if broadcast_id:
                self._log(f"Successfully created and sent broadcast with ID: {broadcast_id} using API Key V4")
                # V4 sends automatically
                return broadcast_id, None, True 
            else:
                self._log(f"Failed to create broadcast using API Key V4. Response: {broadcast_data}", "ERROR")
                fallback_file = self._save_fallback(subject, content)
                return None, fallback_file, False
                
        except requests.exceptions.RequestException as e:
            self._log(f"Error creating/sending broadcast using API Key V4: {e}", "ERROR")
            if hasattr(e, 'response') and e.response is not None:
                 self._log(f"Response status: {e.response.status_code}", "ERROR")
                 response_text = e.response.text[:500] + ('...' if len(e.response.text) > 500 else '')
                 self._log(f"Response text: {response_text}", "ERROR")
            fallback_file = self._save_fallback(subject, content)
            return None, fallback_file, False

    def _save_fallback(self, subject, content):
        """Save email content locally if API call fails."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_subject = "".join(c if c.isalnum() else "_" for c in subject)[:50]
        fallback_filename = self.fallback_dir / f"ck_fallback_{timestamp}_{safe_subject}.html"
        try:
            fallback_filename.parent.mkdir(parents=True, exist_ok=True)
            with open(fallback_filename, "w", encoding="utf-8") as f:
                f.write(f"<h1>{subject}</h1>\n{content}")
            self._log(f"Saved fallback content to {fallback_filename}", "WARNING")
            return str(fallback_filename) # Return as string path
        except Exception as e:
            self._log(f"Error saving fallback file: {e}", "ERROR")
            return None

# Example usage (for testing)
if __name__ == "__main__":
    ck_integration = ConvertKitV4Integration()
    if ck_integration.api_key_v4: # Check if API Key V4 is loaded
        print("\n--- Testing Get Forms (using API Key V4) ---")
        forms = ck_integration.get_forms()
        if forms:
            print(f"Retrieved {len(forms)} forms.")
            for form in forms:
                form_id_val = form["id"]
                form_name = form["name"]
                print(f"  - ID: {form_id_val}, Name: {form_name}")
        else:
            print("Failed to retrieve forms.")
            
        print("\n--- Testing Create and Send Broadcast (using API Key V4) ---")
        test_subject_timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        test_subject = f"Kit V4 API Test Broadcast (V4 Key Auth) - {test_subject_timestamp}"
        test_content = "<p>This is a test broadcast sent via the Kit V4 API using the API Key V4 for authentication.</p>"
        # Updated method name
        broadcast_id, fallback_file, sent = ck_integration.create_and_send_broadcast(test_subject, test_content)
        if broadcast_id and sent:
            print(f"Successfully created and sent broadcast: ID {broadcast_id}")
        else:
            print(f"Failed to create/send broadcast. Fallback saved to: {fallback_file}")
    else:
        print("Failed to initialize Kit V4 Integration (missing API Key V4).")

