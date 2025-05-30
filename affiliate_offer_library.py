import os
import json
import random
import datetime
from pathlib import Path
from dotenv import load_dotenv
import re

class AffiliateOfferLibrary:
    """Manages affiliate offers and injects them into content."""

    def __init__(self, offers_file="affiliate_offers.json"):
        """Initialize with offers from a JSON file."""
        # Load environment variables from .env file if it exists (optional)
        load_dotenv()
        self.offers_file = Path(offers_file) # Use Path object
        # Define log files using relative paths and Path objects
        self.log_dir = Path("drop_reports")
        self.log_file = self.log_dir / "affiliate_offer_library.log"
        self.usage_log_file = self.log_dir / "offer_usage_log.csv"
        # Ensure log directory exists before loading offers or logging
        self._ensure_log_dir_exists()
        # Now load offers and ensure usage log exists
        self.offers = self._load_offers()
        self._ensure_usage_log_exists()
        self._log("AffiliateOfferLibrary initialized")

    def _ensure_log_dir_exists(self):
        """Create the log directory if it doesn"t exist."""
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            print(f"Error creating log directory {self.log_dir}: {e}")

    def _log(self, message, level="INFO"):
        """Log messages to a file."""
        # Check if log directory exists
        if not self.log_dir.exists():
            print(f"[{level}] {message} (Logging disabled: log directory {self.log_dir} missing)")
            return
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] [{level}] {message}\n"
        try:
            with open(self.log_file, "a") as f:
                f.write(log_message)
        except Exception as e:
             print(f"Error writing to log file {self.log_file}: {e}")
             
        if level == "ERROR" or level == "WARNING":
            print(log_message.strip())

    def _load_offers(self):
        """Load offers from the JSON file."""
        try:
            with open(self.offers_file, "r") as f:
                data = json.load(f)
            if not isinstance(data, dict) or "offers" not in data:
                self._log(f"Offers file {self.offers_file} does not contain a dictionary with an 'offers' key.", "ERROR")
                return []
            
            offers_data = data["offers"]
            if not isinstance(offers_data, list):
                self._log(f"The 'offers' key in {self.offers_file} does not contain a list.", "ERROR")
                return []
            
            valid_offers = []
            for i, offer in enumerate(offers_data):
                if isinstance(offer, dict):
                    valid_offers.append(offer)
                else:
                    self._log(f"Item at index {i} in the 'offers' list is not a dictionary, skipping.", "WARNING")
            
            self._log(f"Loaded {len(valid_offers)} valid offers from {self.offers_file}")
            return valid_offers
        except FileNotFoundError:
            self._log(f"Offers file not found: {self.offers_file}", "ERROR")
            return []
        except json.JSONDecodeError as e:
            self._log(f"Error decoding JSON from {self.offers_file}: {e}", "ERROR")
            return []
        except Exception as e:
            self._log(f"Error loading offers: {e}", "ERROR")
            return []

    def _ensure_usage_log_exists(self):
        """Create the usage log CSV file with headers if it doesn"t exist."""
        if not self.log_dir.exists():
            print(f"Warning: Log directory {self.log_dir} not found. Usage log creation skipped.")
            return
            
        if not self.usage_log_file.exists():
            try:
                with open(self.usage_log_file, "w") as f:
                    f.write("Timestamp,OfferID,OfferName,ContentType,ContentTitle\n")
                self._log(f"Created offer usage log file: {self.usage_log_file}")
            except Exception as e:
                self._log(f"Error creating usage log file: {e}", "ERROR")

    def get_all_categories(self):
        """Return a list of unique categories from the offers."""
        categories = set()
        if not self.offers:
             return []
        for offer in self.offers:
            if isinstance(offer, dict):
                categories.update(offer.get("categories", []))
            else:
                self._log(f"Skipping non-dictionary item during category gathering: {offer}", "WARNING")
        return list(categories)

    def _score_offer(self, offer, content, title):
        """Calculate a relevance score for an offer based on content and title."""
        if not isinstance(offer, dict):
            self._log(f"Attempted to score non-dictionary item: {offer}", "WARNING")
            return 0
            
        score = 0
        keywords = offer.get("keywords", [])
        categories = offer.get("categories", [])
        priority = offer.get("priority", 1)
        
        if not isinstance(keywords, list): keywords = []
        if not isinstance(categories, list): categories = []
            
        content_lower = content.lower()
        title_lower = title.lower()

        for keyword in keywords:
            if isinstance(keyword, str) and keyword.lower() in content_lower: score += 2
        for keyword in keywords:
             if isinstance(keyword, str) and keyword.lower() in title_lower: score += 5
        for category in categories:
            if isinstance(category, str) and category.lower() in content_lower: score += 1
            if isinstance(category, str) and category.lower() in title_lower: score += 3
        if isinstance(priority, (int, float)): score += priority
        
        return score

    def match_content_to_offer(self, content, title):
        """Match content and title to the most relevant offer."""
        if not self.offers:
            self._log("No offers loaded, cannot match content.", "WARNING")
            return None
            
        best_offer = None
        highest_score = -1

        for offer in self.offers:
            if not isinstance(offer, dict):
                self._log(f"Skipping non-dictionary item during matching: {offer}", "WARNING")
                continue
                
            score = self._score_offer(offer, content, title)
            current_priority = offer.get("priority", 1)
            best_priority = best_offer.get("priority", 1) if isinstance(best_offer, dict) else 1
            
            if score > highest_score:
                highest_score = score
                best_offer = offer
            elif score == highest_score and isinstance(current_priority, (int, float)) and isinstance(best_priority, (int, float)) and current_priority > best_priority:
                 best_offer = offer

        if isinstance(best_offer, dict) and highest_score > 0:
            offer_name = best_offer.get("name", "Unnamed Offer")
            self._log(f"Matched content to offer: {offer_name} with score {highest_score}")
        else:
            valid_offers_for_fallback = [o for o in self.offers if isinstance(o, dict)]
            if not valid_offers_for_fallback:
                self._log("No valid dictionary offers available for fallback.", "ERROR")
                return None
                
            best_offer = random.choice(valid_offers_for_fallback)
            fallback_offer_name = best_offer.get("name", "Unnamed Fallback Offer")
            self._log(f"No relevant offer found (score <= 0), falling back to random offer: {fallback_offer_name}", "WARNING")
            
        if isinstance(best_offer, dict):
            return best_offer
        else:
            self._log(f"Match content resulted in non-dictionary: {best_offer}", "ERROR")
            return None

    def generate_cta_html(self, offer):
        """Generate a CTA HTML block from the offer's templates."""
        if not isinstance(offer, dict):
            self._log(f"Cannot generate CTA for non-dictionary item: {offer}", "WARNING")
            return ""
            
        cta_templates = offer.get("ctaTemplates")
        if not cta_templates or not isinstance(cta_templates, list) or not cta_templates:
            self._log(f"Offer '{offer.get('name', 'N/A')}' has no valid CTA templates.", "WARNING")
            return ""
            
        valid_templates = [t for t in cta_templates if isinstance(t, str)]
        if not valid_templates:
             self._log(f"Offer '{offer.get('name', 'N/A')}' has no valid string CTA templates.", "WARNING")
             return ""
             
        template = random.choice(valid_templates)
        offer_url = offer.get("url", "#")
        if not isinstance(offer_url, str): offer_url = "#"
            
        utm_source = "wealthautomation"
        utm_medium = "blog" # Or "email"
        utm_campaign = offer.get("id", "offer")
        
        separator = "&" if "?" in offer_url else "?"
        tracked_url = f"{offer_url}{separator}utm_source={utm_source}&utm_medium={utm_medium}&utm_campaign={utm_campaign}"
        
        cta_html = template.replace("{{url}}", tracked_url)
        return cta_html

    def inject_cta_into_content(self, content, offer, position="end"):
        """Inject the generated CTA HTML into the content."""
        if not isinstance(offer, dict):
             self._log(f"Cannot inject CTA for non-dictionary item: {offer}", "WARNING")
             return content
             
        cta_html = self.generate_cta_html(offer)
        if not cta_html:
            return content

        cta_wrapper = f"<div class=\"wealthautomation-cta\">{cta_html}</div>"

        if position == "end":
            return f"{content}\n\n{cta_wrapper}"
        elif position == "middle":
            paragraphs = re.split(r"(</p>\s*)", content, flags=re.IGNORECASE)
            if len(paragraphs) > 3:
                middle_index = (len(paragraphs) // 2) 
                if middle_index % 2 == 0: middle_index -= 1
                paragraphs.insert(middle_index + 1, cta_wrapper)
                return "".join(paragraphs)
            else:
                self._log("Content too short or not structured with <p> tags for middle injection, falling back to end.", "WARNING")
                return f"{content}\n\n{cta_wrapper}"
        elif position == "start":
             return f"{cta_wrapper}\n\n{content}"
        else:
             return f"{content}\n\n{cta_wrapper}"

    def log_offer_usage(self, offer, content_title, content_type="blog"):
        """Log the usage of an offer to a CSV file."""
        if not isinstance(offer, dict):
            self._log(f"Cannot log usage for non-dictionary item: {offer}", "WARNING")
            return
            
        timestamp = datetime.datetime.now().isoformat()
        offer_id = offer.get("id", "N/A")
        offer_name = offer.get("name", "N/A")
        safe_title = content_title.replace('"', '').replace(',', ';')
        
        escaped_offer_name = str(offer_name).replace('"', '""')
        quoted_offer_name = f'"{escaped_offer_name}"'
        escaped_safe_title = safe_title.replace('"', '""')
        quoted_safe_title = f'"{escaped_safe_title}"'
        log_entry = f'{timestamp},{offer_id},{quoted_offer_name},{content_type},{quoted_safe_title}\n'
        
        try:
            if not self.log_dir.exists():
                 print(f"Warning: Log directory {self.log_dir} not found. Usage log skipped.")
                 return
                 
            with open(self.usage_log_file, "a") as f:
                f.write(log_entry)
            self._log(f"Logged usage for offer: {offer_name}")
        except Exception as e:
            self._log(f"Error logging offer usage: {e}", "ERROR")

# Example usage (for testing)
if __name__ == "__main__":
    # Use relative path for dummy offers file
    dummy_offers_file = Path("affiliate_offers.json")
    
    # Create dummy data if file doesn't exist
    if not dummy_offers_file.exists():
        dummy_data_dict = {
            "offers": [
                {
                    "id": "ck_offer",
                    "name": "ConvertKit Trial",
                    "description": "Start your free ConvertKit trial.",
                    "url": "https://convertkit.com/?lmref=example",
                    "commission": "30% recurring",
                    "categories": ["Email Marketing", "Automation"],
                    "keywords": ["email list", "newsletter", "automation", "convertkit"],
                    "priority": 5,
                    "ctaTemplates": [
                        '''<p><strong>Ready to grow your email list?</strong> <a href="{{url}}">Start your free ConvertKit trial today!</a></p>''',
                        '''<div style="border: 1px solid #ccc; padding: 15px; margin: 15px 0;"><p>Build your audience with the email marketing platform designed for creators. <a href="{{url}}">Try ConvertKit free!</a></p></div>'''
                    ]
                },
                {
                    "id": "ai_tool_offer",
                    "name": "AI Writing Assistant",
                    "description": "Generate content faster with AI.",
                    "url": "https://aiwritingtool.com/partner=example",
                    "commission": "20% one-time",
                    "categories": ["AI Tools", "Content Creation"],
                    "keywords": ["artificial intelligence", "writing", "copywriting", "ai tool"],
                    "priority": 4,
                    "ctaTemplates": [
                        '''<p><strong>Need help writing content?</strong> <a href="{{url}}">Check out this AI Writing Assistant!</a></p>'''
                    ]
                }
            ]
        }
        try:
            with open(dummy_offers_file, "w") as f:
                json.dump(dummy_data_dict, f, indent=4)
            print(f"Created dummy offers file: {dummy_offers_file}")
        except Exception as e:
            print(f"Error creating dummy offers file: {e}")

    # Test the library
    library = AffiliateOfferLibrary(offers_file=str(dummy_offers_file))
    print("\n--- Testing Offer Matching ---")
    test_content = "<p>Learn about email marketing automation.</p>"
    test_title = "Grow Your Email List"
    matched_offer = library.match_content_to_offer(test_content, test_title)
    if matched_offer:
        print(f"Matched Offer: {matched_offer.get('name')}")
        print("\n--- Testing CTA Injection (Middle) ---")
        injected_content_middle = library.inject_cta_into_content(test_content + "<p>More content here.</p>", matched_offer, position="middle")
        print(injected_content_middle)
        print("\n--- Testing CTA Injection (End) ---")
        injected_content_end = library.inject_cta_into_content(test_content, matched_offer, position="end")
        print(injected_content_end)
        print("\n--- Testing Usage Logging ---")
        library.log_offer_usage(matched_offer, test_title, content_type="test_blog")
    else:
        print("No offer matched.")

    print("\n--- Testing Categories ---")
    print(f"All Categories: {library.get_all_categories()}")

