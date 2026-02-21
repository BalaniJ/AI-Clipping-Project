"""
Instagram Auto-Poster
Automatically posts approved clips to Instagram using instagrapi
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from instagrapi import Client
    from instagrapi.exceptions import LoginRequired, ChallengeRequired
    INSTAGRAPI_AVAILABLE = True
except ImportError:
    INSTAGRAPI_AVAILABLE = False
    logger.warning("instagrapi not installed. Install with: pip install instagrapi")


class AutoPoster:
    """Automatically posts clips to Instagram"""
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        session_file: str = "instagram_session.json"
    ):
        """
        Initialize Instagram auto-poster
        
        Args:
            username: Instagram username
            password: Instagram password
            session_file: Path to save session for reuse
        """
        self.username = username
        self.password = password
        self.session_file = Path(session_file)
        self.client = None
        
        if not INSTAGRAPI_AVAILABLE:
            raise ImportError("instagrapi is required. Install with: pip install instagrapi")
    
    def login(self, username: Optional[str] = None, password: Optional[str] = None) -> bool:
        """
        Login to Instagram
        
        Args:
            username: Override default username
            password: Override default password
            
        Returns:
            True if login successful
        """
        username = username or self.username
        password = password or self.password
        
        if not username or not password:
            raise ValueError("Username and password required for login")
        
        try:
            self.client = Client()
            
            # Try to load existing session
            if self.session_file.exists():
                try:
                    self.client.load_settings(self.session_file)
                    self.client.login(username, password)
                    logger.info("✓ Logged in using saved session")
                    return True
                except:
                    logger.info("Saved session expired, logging in fresh...")
            
            # Fresh login
            self.client.login(username, password)
            
            # Save session for next time
            self.client.dump_settings(self.session_file)
            logger.info("✓ Logged in and saved session")
            return True
            
        except ChallengeRequired:
            logger.error("Instagram requires challenge (2FA). Handle manually first.")
            return False
        except LoginRequired:
            logger.error("Login failed. Check credentials.")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def post_clip(
        self,
        video_path: str,
        caption: str,
        delay_seconds: Optional[int] = None
    ) -> Dict:
        """
        Post a single clip to Instagram
        
        Args:
            video_path: Path to video file
            caption: Caption text
            delay_seconds: Optional delay before posting (for scheduling)
            
        Returns:
            Dictionary with post result
        """
        if not self.client:
            raise ValueError("Not logged in. Call login() first.")
        
        if delay_seconds:
            logger.info(f"Waiting {delay_seconds} seconds before posting...")
            time.sleep(delay_seconds)
        
        try:
            video_path = Path(video_path)
            if not video_path.exists():
                raise FileNotFoundError(f"Video not found: {video_path}")
            
            logger.info(f"Posting clip: {video_path.name}")
            
            # Upload as Reel
            media = self.client.clip_upload(
                path=str(video_path),
                caption=caption,
                thumbnail=None  # Let Instagram auto-generate
            )
            
            result = {
                "status": "success",
                "media_id": media.pk if hasattr(media, 'pk') else None,
                "video_path": str(video_path),
                "caption": caption,
                "posted_at": datetime.now().isoformat()
            }
            
            logger.info(f"✓ Posted successfully: {video_path.name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to post clip: {e}")
            return {
                "status": "error",
                "error": str(e),
                "video_path": str(video_path)
            }
    
    def post_approved_clips(
        self,
        storage_path: Optional[str] = None,
        max_posts_per_run: int = 5,
        min_delay_minutes: int = 30,
        max_delay_minutes: int = 120
    ) -> List[Dict]:
        """
        Post all approved clips from storage
        
        Args:
            storage_path: Path to storage directory (defaults to today's output)
            max_posts_per_run: Maximum clips to post in one run
            min_delay_minutes: Minimum delay between posts (randomized)
            max_delay_minutes: Maximum delay between posts (randomized)
            
        Returns:
            List of posting results
        """
        import sys
        from pathlib import Path
        
        # Add AI-Clipping-Project to path
        sys.path.insert(0, str(Path(__file__).parent / "AI-Clipping-Project"))
        from storage import StorageManager
        
        storage = StorageManager(base_path=Path(storage_path) if storage_path else None)
        bundles = storage.get_all_post_ready_bundles()
        
        # Filter for approved clips
        approved = [
            b for b in bundles
            if b.get('approval_status') == 'approved' and not b.get('posted', False)
        ]
        
        if not approved:
            logger.info("No approved clips ready to post")
            return []
        
        # Limit number of posts
        approved = approved[:max_posts_per_run]
        
        results = []
        for i, bundle in enumerate(approved):
            if i > 0:
                # Random delay between posts (to avoid detection)
                delay = random.randint(min_delay_minutes, max_delay_minutes) * 60
                logger.info(f"Waiting {delay//60} minutes before next post...")
                time.sleep(delay)
            
            # Get caption
            captions = bundle.get('captions', [])
            if captions:
                caption_data = captions[0]
                caption = f"{caption_data.get('caption', '')}\n\n{' '.join(caption_data.get('hashtags', []))}"
            else:
                caption = "Check this out! 🔥"
            
            # Post clip
            result = self.post_clip(
                video_path=bundle['video_path'],
                caption=caption
            )
            
            # Mark as posted in metadata
            if result['status'] == 'success':
                self._mark_as_posted(bundle)
            
            results.append(result)
        
        logger.info(f"Posted {len([r for r in results if r['status'] == 'success'])} clip(s)")
        return results
    
    def _mark_as_posted(self, bundle: Dict):
        """Mark bundle as posted in metadata"""
        try:
            metadata_path = bundle.get('metadata_path')
            if metadata_path and Path(metadata_path).exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                metadata['posted'] = True
                metadata['posted_at'] = datetime.now().isoformat()
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not mark as posted: {e}")
    
    def schedule_posts(
        self,
        posts_per_day: int = 3,
        posting_hours: List[int] = [9, 14, 20]
    ):
        """
        Schedule posts throughout the day
        
        Args:
            posts_per_day: Number of posts per day
            posting_hours: Preferred hours for posting (24-hour format)
        """
        logger.info(f"Scheduling {posts_per_day} posts per day")
        logger.info(f"Preferred hours: {posting_hours}")
        
        # This would integrate with a scheduler
        # For now, just log the intent
        pass


# CLI Interface
if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python auto_poster.py login <username> <password>")
        print("  python auto_poster.py post <video_path> <caption>")
        print("  python auto_poster.py post-approved")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    poster = AutoPoster()
    
    if command == "login":
        if len(sys.argv) < 4:
            print("Error: Need username and password")
            sys.exit(1)
        
        username = sys.argv[2]
        password = sys.argv[3]
        
        if poster.login(username, password):
            print("✓ Logged in successfully")
        else:
            print("✗ Login failed")
            sys.exit(1)
    
    elif command == "post":
        if len(sys.argv) < 4:
            print("Error: Need video path and caption")
            sys.exit(1)
        
        # Load credentials from env or config
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        
        if not username or not password:
            print("Error: Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env")
            sys.exit(1)
        
        if not poster.login(username, password):
            print("✗ Login failed")
            sys.exit(1)
        
        video_path = sys.argv[2]
        caption = sys.argv[3]
        
        result = poster.post_clip(video_path, caption)
        if result['status'] == 'success':
            print(f"✓ Posted: {video_path}")
        else:
            print(f"✗ Failed: {result.get('error')}")
    
    elif command == "post-approved":
        username = os.getenv("INSTAGRAM_USERNAME")
        password = os.getenv("INSTAGRAM_PASSWORD")
        
        if not username or not password:
            print("Error: Set INSTAGRAM_USERNAME and INSTAGRAM_PASSWORD in .env")
            sys.exit(1)
        
        if not poster.login(username, password):
            print("✗ Login failed")
            sys.exit(1)
        
        results = poster.post_approved_clips()
        print(f"\nPosted {len([r for r in results if r['status'] == 'success'])} clip(s)")
    
    else:
        print(f"Unknown command: {command}")
