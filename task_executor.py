import json
import datetime
import os
from pathlib import Path

# --- Configuration ---
# Use relative paths for Railway compatibility
LOG_DIR = Path("drop_reports")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "") # Use the same webhook as the main system

# --- Logging Helper ---
def _log_task_activity(message, level="INFO"):
    """Log messages related to task execution."""
    # This could be expanded to write to a dedicated task log file if needed
    # For now, just print to console/Railway logs
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [TaskExecutor] [{level}] {message}"
    print(log_entry)
    # Optionally send critical errors to Discord
    if level == "ERROR" and DISCORD_WEBHOOK_URL:
        _send_discord_alert(f"Task Execution ERROR: {message}")

def _send_discord_alert(message):
    """Sends a simple alert to Discord."""
    try:
        import requests
        payload = {"content": f"**[TaskExecutor Alert]** {message}"}
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
    except Exception as e:
        print(f"[TaskExecutor] [ERROR] Failed to send Discord alert: {e}")

# --- Task Handlers ---
def handle_social_post(task_data):
    """Handles the 'create_social_post' task type.
    Currently simulates by logging details.
    Future: Integrate with Meta API or browser automation.
    """
    brand = task_data.get("brand", "N/A")
    platforms = task_data.get("platforms", [])
    image_prompt = task_data.get("image_prompt", "N/A")
    caption = task_data.get("caption", "N/A")
    cta = task_data.get("cta", "N/A")

    _log_task_activity(f"Received social post task for brand: {brand}")
    _log_task_activity(f"  Platforms: {", ".join(platforms)}")
    _log_task_activity(f"  Image Prompt: {image_prompt}")
    _log_task_activity(f"  Caption: {caption}")
    _log_task_activity(f"  CTA: {cta}")

    # --- Placeholder for actual execution ---
    # 1. Generate image using image_prompt (e.g., call MidJourney API)
    # 2. For each platform in platforms:
    #    - Format caption/CTA appropriately
    #    - Post image + text using platform API (e.g., Meta Graph API)
    #    - OR use browser automation (Manus) if API not feasible
    # 3. Log success/failure for each platform
    # --- End Placeholder ---

    # Simulate success for now
    status_message = "Social post task processed (simulation). Actual posting needs implementation."
    _log_task_activity(status_message, "INFO")
    return {"status": "processed_simulation", "message": status_message}

# --- Main Executor Function ---
def execute_task(task_data):
    """Receives task data, logs it, and dispatches to the appropriate handler."""
    task_type = task_data.get("task_type", "unknown")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f") # Added microseconds for uniqueness
    
    # Ensure log directory exists
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_filename = LOG_DIR / f"task_received_{task_type}_{timestamp}.json"
        # Save the raw task data received
        with open(log_filename, "w", encoding="utf-8") as f:
            json.dump(task_data, f, indent=2)
        _log_task_activity(f"Received and logged task to {log_filename}")
    except Exception as e:
        _log_task_activity(f"Failed to save received task JSON: {e}", "ERROR")
        # Continue execution attempt even if logging fails

    result = {}
    try:
        # --- Task Dispatching Logic ---
        if task_type == "create_social_post":
            result = handle_social_post(task_data)
        # --- Add more task types here as elif blocks ---
        # elif task_type == "create_wp_post":
        #     result = handle_wp_post(task_data)
        # elif task_type == "send_ck_email":
        #     result = handle_ck_email(task_data)
        else:
            _log_task_activity(f"Unrecognized task type: {task_type}", "WARNING")
            result = {"status": "unrecognized_task_type", "message": f"Task type 	'{task_type}	' not handled."}

        # Log final result
        _log_task_activity(f"Task 	'{task_type}	' finished with status: {result.get(	'status	', 	'unknown	')}")

    except Exception as e:
        _log_task_activity(f"Exception during task execution ({task_type}): {e}", "ERROR")
        result = {"status": "execution_error", "message": str(e)}

    return result

# Example of how this might be called (for testing)
if __name__ == "__main__":
    print("Testing task_executor...")
    test_task = {
      "task_type": "create_social_post",
      "brand": "TestBrand",
      "platforms": ["Facebook", "Instagram"],
      "image_prompt": "A test image prompt",
      "caption": "This is a test caption.",
      "cta": "http://example.com"
    }
    execution_result = execute_task(test_task)
    print(f"\nExecution Result:\n{json.dumps(execution_result, indent=2)}")

    test_unknown_task = {
        "task_type": "unknown_task_example",
        "data": "some data"
    }
    unknown_result = execute_task(test_unknown_task)
    print(f"\nUnknown Task Result:\n{json.dumps(unknown_result, indent=2)}")

