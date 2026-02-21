"""
Master Script for Option B: Creator Clipping Service
Orchestrates monitoring, processing, and posting
"""
import sys
import logging
from pathlib import Path

# Add AI-Clipping-Project to path
sys.path.insert(0, str(Path(__file__).parent / "AI-Clipping-Project"))

from monitor_creator import CreatorMonitor
from auto_poster import AutoPoster
from whop_integration import WhopIntegration
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class OptionBOrchestrator:
    """Orchestrates the complete Option B workflow"""
    
    def __init__(self):
        """Initialize all components"""
        self.monitor = CreatorMonitor()
        self.whop = WhopIntegration()
        self.poster = None  # Initialize when needed
        
        # Load Instagram credentials
        self.instagram_username = os.getenv("INSTAGRAM_USERNAME")
        self.instagram_password = os.getenv("INSTAGRAM_PASSWORD")
    
    def initialize_instagram(self):
        """Initialize Instagram poster"""
        if not self.instagram_username or not self.instagram_password:
            logger.warning("Instagram credentials not set. Auto-posting disabled.")
            return False
        
        try:
            self.poster = AutoPoster(
                username=self.instagram_username,
                password=self.instagram_password
            )
            return self.poster.login()
        except Exception as e:
            logger.error(f"Failed to initialize Instagram: {e}")
            return False
    
    def process_new_videos_and_post(self, auto_post: bool = False):
        """
        Check for new videos, process them, and optionally post
        
        Args:
            auto_post: If True, automatically post approved clips
        """
        logger.info("Checking for new videos from all creators...")
        
        # Check for new videos
        new_videos_by_creator = self.monitor.check_all_creators()
        
        if not new_videos_by_creator:
            logger.info("No new videos found")
            return
        
        # Process each new video
        for creator_name, new_videos in new_videos_by_creator.items():
            creator = next(
                (c for c in self.monitor.config["creators"] if c["name"] == creator_name),
                None
            )
            
            if not creator:
                continue
            
            for video_info in new_videos:
                # Process video
                bundles = self.monitor.process_new_video(video_info, creator)
                
                if bundles:
                    # Generate Whop.com payment link
                    whop_link = self.whop.create_payment_link(
                        creator_name=creator_name,
                        video_title=video_info['title'],
                        num_clips=len(bundles),
                        pricing_type="per_video"
                    )
                    
                    logger.info(f"Payment link for {creator_name}: {whop_link}")
                    
                    # Send notification with payment link
                    self.monitor._send_notification(creator, video_info, bundles)
        
        # Auto-post if enabled
        if auto_post and self.poster:
            logger.info("Posting approved clips to Instagram...")
            results = self.poster.post_approved_clips()
            logger.info(f"Posted {len([r for r in results if r['status'] == 'success'])} clip(s)")
    
    def run_full_automation(self):
        """Run full automation loop with monitoring and posting"""
        # Initialize Instagram
        if self.instagram_username and self.instagram_password:
            if self.initialize_instagram():
                logger.info("✓ Instagram initialized")
            else:
                logger.warning("Instagram not available, monitoring only")
        
        # Start monitoring loop
        logger.info("Starting full automation...")
        logger.info("This will check for new videos and process them automatically")
        
        # Run monitoring (this is a blocking call)
        self.monitor.run_monitoring_loop()


# CLI Interface
if __name__ == "__main__":
    orchestrator = OptionBOrchestrator()
    
    if len(sys.argv) < 2:
        print("Option B: Creator Clipping Service")
        print("\nUsage:")
        print("  python run_option_b.py check          - Check for new videos")
        print("  python run_option_b.py process         - Process new videos (no auto-post)")
        print("  python run_option_b.py process --post  - Process and auto-post")
        print("  python run_option_b.py run             - Full automation loop")
        print("\nManagement:")
        print("  python monitor_creator.py add <name> <channel_url> [instagram] [whop_link]")
        print("  python monitor_creator.py list")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "check":
        new_videos = orchestrator.monitor.check_all_creators()
        if new_videos:
            for creator, videos in new_videos.items():
                print(f"\n{creator}: {len(videos)} new video(s)")
                for video in videos:
                    print(f"  - {video['title']}")
        else:
            print("No new videos found")
    
    elif command == "process":
        auto_post = "--post" in sys.argv
        orchestrator.process_new_videos_and_post(auto_post=auto_post)
    
    elif command == "run":
        orchestrator.run_full_automation()
    
    else:
        print(f"Unknown command: {command}")
