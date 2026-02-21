"""
Campaign Manager
Manages Whop.com campaigns with specific guidelines and rules
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CampaignManager:
    """Manages multiple Whop.com campaigns with their specific rules"""
    
    def __init__(self, campaigns_dir: str = "campaigns"):
        """
        Initialize campaign manager
        
        Args:
            campaigns_dir: Directory containing campaign folders
        """
        self.campaigns_dir = Path(campaigns_dir)
        self.campaigns_dir.mkdir(exist_ok=True)
        self.campaigns = self._load_all_campaigns()
    
    def _load_all_campaigns(self) -> Dict[str, Dict]:
        """Load all campaigns from the campaigns directory"""
        campaigns = {}
        
        if not self.campaigns_dir.exists():
            return campaigns
        
        for campaign_folder in self.campaigns_dir.iterdir():
            if not campaign_folder.is_dir():
                continue
            
            campaign_id = campaign_folder.name
            guidelines_file = campaign_folder / "guidelines.json"
            
            if guidelines_file.exists():
                try:
                    with open(guidelines_file, 'r', encoding='utf-8') as f:
                        campaign_data = json.load(f)
                        campaigns[campaign_id] = campaign_data
                        logger.info(f"Loaded campaign: {campaign_id}")
                except Exception as e:
                    logger.error(f"Failed to load campaign {campaign_id}: {e}")
        
        return campaigns
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Get campaign by ID"""
        return self.campaigns.get(campaign_id)
    
    def list_campaigns(self) -> List[Dict]:
        """List all available campaigns"""
        return [
            {
                "id": campaign_id,
                "name": data.get("campaign_name", campaign_id),
                "whop_url": data.get("whop_campaign_url")
            }
            for campaign_id, data in self.campaigns.items()
        ]
    
    def validate_source_url(self, url: str, campaign_id: str) -> bool:
        """
        Check if a URL is from an approved source for the campaign
        
        Args:
            url: URL to validate
            campaign_id: Campaign to check against
            
        Returns:
            True if URL is approved
        """
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return False
        
        approved = campaign.get("approved_sources", {})
        
        # Check all source types
        for source_type, urls in approved.items():
            for approved_url in urls:
                # Check if URL matches or is from the same source
                if self._url_matches(url, approved_url):
                    return True
        
        return False
    
    def _url_matches(self, url: str, approved_url: str) -> bool:
        """Check if URL matches approved source"""
        # Extract base URLs for comparison
        url_lower = url.lower()
        approved_lower = approved_url.lower()
        
        # Direct match
        if approved_url in url or url in approved_url:
            return True
        
        # YouTube video ID match
        if "youtube.com/watch" in url_lower and "youtube.com/watch" in approved_lower:
            url_id = self._extract_youtube_id(url)
            approved_id = self._extract_youtube_id(approved_url)
            if url_id and approved_id and url_id == approved_id:
                return True
        
        # YouTube Shorts match
        if "youtube.com/shorts" in url_lower and "youtube.com/shorts" in approved_lower:
            url_id = self._extract_youtube_id(url)
            approved_id = self._extract_youtube_id(approved_url)
            if url_id and approved_id and url_id == approved_id:
                return True
        
        # Google Drive folder match
        if "drive.google.com" in url_lower and "drive.google.com" in approved_lower:
            # Same folder structure
            return True
        
        return False
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        import re
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtube\.com\/shorts\/|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_clipping_rules(self, campaign_id: str) -> Dict:
        """Get clipping rules for a campaign"""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return {}
        
        return campaign.get("clipping_rules", {})
    
    def get_caption_requirements(self, campaign_id: str, platform: str = "instagram") -> Dict:
        """Get caption requirements for a campaign and platform"""
        campaign = self.get_campaign(campaign_id)
        if not campaign:
            return {}
        
        tagging = campaign.get("tagging_requirements", {}).get(platform, {})
        caption_guidelines = campaign.get("caption_guidelines", {})
        
        return {
            "tagging": tagging,
            "guidelines": caption_guidelines,
            "style": caption_guidelines.get("style", ""),
            "tone": caption_guidelines.get("tone", "")
        }
    
    def create_campaign_folder(self, campaign_id: str, guidelines: Dict) -> Path:
        """
        Create a new campaign folder with guidelines
        
        Args:
            campaign_id: Unique campaign identifier
            guidelines: Campaign guidelines dictionary
            
        Returns:
            Path to created campaign folder
        """
        campaign_folder = self.campaigns_dir / campaign_id
        campaign_folder.mkdir(exist_ok=True)
        
        guidelines_file = campaign_folder / "guidelines.json"
        with open(guidelines_file, 'w', encoding='utf-8') as f:
            json.dump(guidelines, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created campaign folder: {campaign_folder}")
        return campaign_folder
    
    def get_campaign_output_path(self, campaign_id: str) -> Path:
        """Get output path for campaign-specific clips"""
        return Path("output") / "campaigns" / campaign_id / datetime.now().strftime("%Y-%m-%d")


# CLI Interface
if __name__ == "__main__":
    import sys
    
    manager = CampaignManager()
    
    if len(sys.argv) < 2:
        print("Campaign Manager")
        print("\nUsage:")
        print("  python campaign_manager.py list")
        print("  python campaign_manager.py get <campaign_id>")
        print("  python campaign_manager.py validate <url> <campaign_id>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        campaigns = manager.list_campaigns()
        if campaigns:
            print("\nAvailable Campaigns:")
            for camp in campaigns:
                print(f"  {camp['id']}: {camp['name']}")
        else:
            print("No campaigns found")
    
    elif command == "get":
        if len(sys.argv) < 3:
            print("Error: Need campaign ID")
            sys.exit(1)
        
        campaign_id = sys.argv[2]
        campaign = manager.get_campaign(campaign_id)
        
        if campaign:
            print(f"\nCampaign: {campaign.get('campaign_name')}")
            print(f"ID: {campaign_id}")
            print(f"\nClipping Rules:")
            rules = campaign.get('clipping_rules', {})
            for rule in rules.get('critical', []):
                print(f"  ⚠ {rule}")
        else:
            print(f"Campaign '{campaign_id}' not found")
    
    elif command == "validate":
        if len(sys.argv) < 4:
            print("Error: Need URL and campaign ID")
            sys.exit(1)
        
        url = sys.argv[2]
        campaign_id = sys.argv[3]
        
        is_valid = manager.validate_source_url(url, campaign_id)
        if is_valid:
            print(f"✓ URL is approved for campaign '{campaign_id}'")
        else:
            print(f"✗ URL is NOT approved for campaign '{campaign_id}'")
