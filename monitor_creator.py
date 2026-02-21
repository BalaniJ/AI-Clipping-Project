"""
Creator Channel Monitor
Monitors YouTube channels for new uploads and automatically processes them
"""
import yt_dlp
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import sys
from pathlib import Path

# Add AI-Clipping-Project to path for imports
sys.path.insert(0, str(Path(__file__).parent / "AI-Clipping-Project"))

from pipeline import ContentPipeline
from storage import StorageManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CreatorMonitor:
    """Monitors YouTube channels and auto-processes new videos"""
    
    def __init__(self, config_file: str = "creator_config.json"):
        """
        Initialize the creator monitor
        
        Args:
            config_file: Path to configuration file with creator settings
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
        self.pipeline = ContentPipeline()
        self.storage = StorageManager()
        self.processed_videos = self._load_processed_videos()
    
    def _load_config(self) -> Dict:
        """Load creator configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "creators": [],
            "check_interval_minutes": 60,
            "auto_post": False,
            "notification_enabled": True
        }
    
    def _save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def _load_processed_videos(self) -> Dict[str, List[str]]:
        """Load list of already processed videos per creator"""
        processed_file = Path("processed_videos.json")
        if processed_file.exists():
            with open(processed_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _save_processed_videos(self):
        """Save processed videos list"""
        processed_file = Path("processed_videos.json")
        with open(processed_file, 'w', encoding='utf-8') as f:
            json.dump(self.processed_videos, f, indent=2)
    
    def add_creator(
        self,
        creator_name: str,
        channel_url: str,
        instagram_account: Optional[str] = None,
        whop_link: Optional[str] = None,
        num_clips_per_video: int = 3
    ):
        """
        Add a creator to monitor
        
        Args:
            creator_name: Name of the creator
            channel_url: YouTube channel URL
            instagram_account: Instagram username to post to
            whop_link: Whop.com payment link for this creator
            num_clips_per_video: Number of clips to extract per video
        """
        creator = {
            "name": creator_name,
            "channel_url": channel_url,
            "channel_id": self._extract_channel_id(channel_url),
            "instagram_account": instagram_account,
            "whop_link": whop_link,
            "num_clips_per_video": num_clips_per_video,
            "added_date": datetime.now().isoformat(),
            "active": True
        }
        
        if "creators" not in self.config:
            self.config["creators"] = []
        
        # Check if creator already exists
        for i, existing in enumerate(self.config["creators"]):
            if existing.get("channel_id") == creator["channel_id"]:
                self.config["creators"][i] = creator
                logger.info(f"Updated creator: {creator_name}")
                self._save_config()
                return
        
        self.config["creators"].append(creator)
        self._save_config()
        logger.info(f"Added creator: {creator_name}")
    
    def _extract_channel_id(self, channel_url: str) -> str:
        """Extract channel ID from URL"""
        try:
            ydl_opts = {'quiet': True, 'extract_flat': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(channel_url, download=False)
                return info.get('channel_id', '')
        except Exception as e:
            logger.error(f"Failed to extract channel ID: {e}")
            return ""
    
    def check_creator_for_new_videos(self, creator: Dict) -> List[Dict]:
        """
        Check a specific creator's channel for new videos
        
        Args:
            creator: Creator configuration dictionary
            
        Returns:
            List of new video dictionaries
        """
        channel_url = creator["channel_url"]
        creator_id = creator["channel_id"]
        creator_name = creator["name"]
        
        try:
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'playlistend': 5  # Check last 5 videos
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get channel videos feed
                if '/channel/' in channel_url or '/c/' in channel_url or '/user/' in channel_url:
                    feed_url = f"{channel_url}/videos"
                else:
                    feed_url = channel_url
                
                info = ydl.extract_info(feed_url, download=False)
                entries = info.get('entries', [])
                
                if not entries:
                    return []
                
                new_videos = []
                processed = self.processed_videos.get(creator_id, [])
                
                for entry in entries:
                    video_id = entry.get('id')
                    if not video_id:
                        continue
                    
                    # Check if already processed
                    if video_id in processed:
                        continue
                    
                    video_url = f"https://www.youtube.com/watch?v={video_id}"
                    video_title = entry.get('title', 'Untitled')
                    upload_date = entry.get('upload_date', '')
                    
                    new_videos.append({
                        'video_id': video_id,
                        'video_url': video_url,
                        'title': video_title,
                        'upload_date': upload_date,
                        'creator_name': creator_name,
                        'creator_id': creator_id
                    })
                
                return new_videos
                
        except Exception as e:
            logger.error(f"Error checking {creator_name}: {e}")
            return []
    
    def process_new_video(
        self,
        video_info: Dict,
        creator: Dict
    ) -> List[Dict]:
        """
        Process a new video through the pipeline
        
        Args:
            video_info: Video information dictionary
            creator: Creator configuration
            
        Returns:
            List of processed clip bundles
        """
        video_url = video_info['video_url']
        creator_name = creator['name']
        num_clips = creator.get('num_clips_per_video', 3)
        
        logger.info(f"Processing new video from {creator_name}: {video_info['title']}")
        
        try:
            # Process through pipeline
            bundles = self.pipeline.process_video(
                url=video_url,
                num_clips=num_clips,
                video_description=f"{creator_name} - {video_info['title']}"
            )
            
            # Mark video as processed
            creator_id = creator['channel_id']
            if creator_id not in self.processed_videos:
                self.processed_videos[creator_id] = []
            
            self.processed_videos[creator_id].append(video_info['video_id'])
            self._save_processed_videos()
            
            # Add creator metadata to bundles
            for bundle in bundles:
                bundle['creator_name'] = creator_name
                bundle['creator_whop_link'] = creator.get('whop_link')
                bundle['source_video_url'] = video_url
                bundle['source_video_title'] = video_info['title']
            
            logger.info(f"✓ Processed {len(bundles)} clips from {creator_name}")
            return bundles
            
        except Exception as e:
            logger.error(f"Failed to process video: {e}")
            return []
    
    def check_all_creators(self) -> Dict[str, List[Dict]]:
        """
        Check all active creators for new videos
        
        Returns:
            Dictionary mapping creator names to lists of new videos
        """
        results = {}
        active_creators = [c for c in self.config.get("creators", []) if c.get("active", True)]
        
        for creator in active_creators:
            creator_name = creator["name"]
            new_videos = self.check_creator_for_new_videos(creator)
            
            if new_videos:
                results[creator_name] = new_videos
                logger.info(f"Found {len(new_videos)} new video(s) from {creator_name}")
        
        return results
    
    def run_monitoring_loop(self, check_interval_minutes: Optional[int] = None):
        """
        Run continuous monitoring loop
        
        Args:
            check_interval_minutes: How often to check (defaults to config)
        """
        interval = check_interval_minutes or self.config.get("check_interval_minutes", 60)
        interval_seconds = interval * 60
        
        logger.info(f"Starting monitoring loop (checking every {interval} minutes)")
        logger.info(f"Monitoring {len(self.config.get('creators', []))} creator(s)")
        
        while True:
            try:
                logger.info(f"Checking for new videos... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")
                
                new_videos_by_creator = self.check_all_creators()
                
                for creator_name, new_videos in new_videos_by_creator.items():
                    # Find creator config
                    creator = next(
                        (c for c in self.config["creators"] if c["name"] == creator_name),
                        None
                    )
                    
                    if not creator:
                        continue
                    
                    for video_info in new_videos:
                        bundles = self.process_new_video(video_info, creator)
                        
                        if bundles and self.config.get("notification_enabled"):
                            # Send notification (via bridge or WhatsApp)
                            self._send_notification(creator, video_info, bundles)
                
                logger.info(f"Sleeping for {interval} minutes...")
                time.sleep(interval_seconds)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _send_notification(self, creator: Dict, video_info: Dict, bundles: List[Dict]):
        """Send notification about new processed clips"""
        try:
            # Import from AI-Clipping-Project
            from bridge import OpenClawBridge
            bridge = OpenClawBridge()
            
            message = (
                f"🎬 New clips ready from {creator['name']}!\n\n"
                f"Video: {video_info['title']}\n"
                f"Clips processed: {len(bundles)}\n\n"
            )
            
            if creator.get('whop_link'):
                message += f"💰 Share this link with creator for payment: {creator['whop_link']}\n\n"
            
            message += "✅ Ready to post to Instagram!"
            
            # Send notification (first bundle as example)
            if bundles:
                bridge.send_approval_request(
                    video_path=bundles[0]['video_path'],
                    caption=message,
                    metadata={
                        'creator_name': creator['name'],
                        'video_title': video_info['title'],
                        'whop_link': creator.get('whop_link')
                    }
                )
        except Exception as e:
            logger.warning(f"Could not send notification: {e}")


# CLI Interface
if __name__ == "__main__":
    import sys
    
    monitor = CreatorMonitor()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python monitor_creator.py add <name> <channel_url> [instagram] [whop_link]")
        print("  python monitor_creator.py check")
        print("  python monitor_creator.py run")
        print("  python monitor_creator.py list")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "add":
        if len(sys.argv) < 4:
            print("Error: Need creator name and channel URL")
            sys.exit(1)
        
        name = sys.argv[2]
        channel_url = sys.argv[3]
        instagram = sys.argv[4] if len(sys.argv) > 4 else None
        whop_link = sys.argv[5] if len(sys.argv) > 5 else None
        
        monitor.add_creator(name, channel_url, instagram, whop_link)
        print(f"✓ Added creator: {name}")
    
    elif command == "check":
        print("Checking for new videos...")
        results = monitor.check_all_creators()
        
        if results:
            for creator, videos in results.items():
                print(f"\n{creator}: {len(videos)} new video(s)")
                for video in videos:
                    print(f"  - {video['title']}")
        else:
            print("No new videos found")
    
    elif command == "run":
        print("Starting continuous monitoring...")
        monitor.run_monitoring_loop()
    
    elif command == "list":
        creators = monitor.config.get("creators", [])
        if creators:
            print("\nMonitored Creators:")
            for creator in creators:
                status = "✓ Active" if creator.get("active") else "✗ Inactive"
                print(f"  {status} - {creator['name']}")
                print(f"    Channel: {creator['channel_url']}")
                if creator.get('whop_link'):
                    print(f"    Whop Link: {creator['whop_link']}")
        else:
            print("No creators configured yet")
    
    else:
        print(f"Unknown command: {command}")
