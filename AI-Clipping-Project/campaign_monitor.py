"""
Campaign Monitor
Monitors approved sources for campaigns and processes them
"""
import sys
from pathlib import Path
import logging
import time
import json
from typing import Dict, List, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / "AI-Clipping-Project"))

from campaign_manager import CampaignManager
from campaign_processor import CampaignProcessor
import yt_dlp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CampaignMonitor:
    """Monitors campaign-approved sources for new content"""
    
    def __init__(self):
        """Initialize campaign monitor"""
        self.campaign_manager = CampaignManager()
        self.processor = CampaignProcessor()
        self.processed_content = self._load_processed()
    
    def _load_processed(self) -> Dict[str, List[str]]:
        """Load processed content tracking"""
        processed_file = Path("campaigns_processed.json")
        if processed_file.exists():
            with open(processed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_processed(self):
        """Save processed content tracking"""
        processed_file = Path("campaigns_processed.json")
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_content, f, indent=2)
    
    def check_campaign_sources(self, campaign_id: str) -> List[Dict]:
        """
        Check approved sources for a campaign for processable content
        
        Args:
            campaign_id: Campaign to check
            
        Returns:
            List of content items to process
        """
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            return []
        
        approved = campaign.get("approved_sources", {})
        new_content = []
        processed = self.processed_content.get(campaign_id, [])
        
        # Check YouTube sources
        for source_type in ["youtube_longform", "youtube_shorts"]:
            urls = approved.get(source_type, [])
            for url in urls:
                # Extract video ID
                video_id = self._extract_video_id(url)
                if video_id and video_id not in processed:
                    new_content.append({
                        "url": url,
                        "type": "youtube",
                        "campaign_id": campaign_id,
                        "source_type": source_type
                    })
        
        # Check Google Drive (would need Google Drive API)
        # Check Twitch VODs (would need Twitch API)
        # For now, focus on YouTube
        
        return new_content
    
    def _extract_video_id(self, url: str) -> Optional[str]:
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
    
    def process_campaign_content(self, campaign_id: str, max_items: int = 5) -> List[Dict]:
        """
        Process new content for a campaign
        
        Args:
            campaign_id: Campaign to process
            max_items: Maximum items to process in one run
            
        Returns:
            List of processed bundles
        """
        new_content = self.check_campaign_sources(campaign_id)
        
        if not new_content:
            logger.info(f"No new content found for campaign '{campaign_id}'")
            return []
        
        # Limit processing
        new_content = new_content[:max_items]
        
        all_bundles = []
        for item in new_content:
            try:
                logger.info(f"Processing: {item['url']} for campaign '{campaign_id}'")
                
                bundles = self.processor.process_for_campaign(
                    video_url=item['url'],
                    campaign_id=campaign_id,
                    num_clips=3
                )
                
                all_bundles.extend(bundles)
                
                # Mark as processed
                video_id = self._extract_video_id(item['url'])
                if video_id:
                    if campaign_id not in self.processed_content:
                        self.processed_content[campaign_id] = []
                    self.processed_content[campaign_id].append(video_id)
                
            except Exception as e:
                logger.error(f"Failed to process {item['url']}: {e}")
                continue
        
        self._save_processed()
        return all_bundles
    
    def monitor_all_campaigns(self, check_interval_minutes: int = 60):
        """Monitor all campaigns continuously"""
        campaigns = self.campaign_manager.list_campaigns()
        
        logger.info(f"Monitoring {len(campaigns)} campaign(s)")
        logger.info(f"Check interval: {check_interval_minutes} minutes")
        
        while True:
            try:
                logger.info(f"Checking campaigns... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                
                for campaign in campaigns:
                    campaign_id = campaign['id']
                    logger.info(f"Checking campaign: {campaign_id}")
                    
                    bundles = self.process_campaign_content(campaign_id, max_items=3)
                    
                    if bundles:
                        logger.info(f"✓ Processed {len(bundles)} clips for {campaign_id}")
                
                logger.info(f"Sleeping for {check_interval_minutes} minutes...")
                time.sleep(check_interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped")
                break
            except Exception as e:
                logger.error(f"Error in monitoring: {e}")
                time.sleep(60)


# CLI Interface
if __name__ == "__main__":
    import sys
    
    monitor = CampaignMonitor()
    
    if len(sys.argv) < 2:
        print("Campaign Monitor")
        print("\nUsage:")
        print("  python campaign_monitor.py check <campaign_id>")
        print("  python campaign_monitor.py process <campaign_id>")
        print("  python campaign_monitor.py run [interval_minutes]")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "check":
        if len(sys.argv) < 3:
            print("Error: Need campaign ID")
            sys.exit(1)
        
        campaign_id = sys.argv[2]
        content = monitor.check_campaign_sources(campaign_id)
        
        if content:
            print(f"\nFound {len(content)} new content item(s) for '{campaign_id}':")
            for item in content:
                print(f"  - {item['url']}")
        else:
            print(f"No new content found for '{campaign_id}'")
    
    elif command == "process":
        if len(sys.argv) < 3:
            print("Error: Need campaign ID")
            sys.exit(1)
        
        campaign_id = sys.argv[2]
        bundles = monitor.process_campaign_content(campaign_id)
        print(f"\n✓ Processed {len(bundles)} clip(s) for '{campaign_id}'")
    
    elif command == "run":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        monitor.monitor_all_campaigns(interval)
    
    else:
        print(f"Unknown command: {command}")
