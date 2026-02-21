"""
Video Scraper Module
Downloads highest quality vertical videos from YouTube/TikTok using yt-dlp
"""
import yt_dlp
import os
import logging
from pathlib import Path
from typing import Optional, Dict
from config import TEMP_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoScraper:
    """Handles video downloads from YouTube and TikTok"""
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the video scraper
        
        Args:
            output_dir: Directory to save downloaded videos (defaults to TEMP_DIR)
        """
        self.output_dir = output_dir or TEMP_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if URL is from a supported platform
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is supported, False otherwise
        """
        supported_domains = [
            "youtube.com",
            "youtu.be",
            "m.youtube.com",
            "tiktok.com",
            "vm.tiktok.com",
            "www.tiktok.com"
        ]
        return any(domain in url.lower() for domain in supported_domains)
    
    def download_video(self, url: str, video_id: Optional[str] = None) -> Dict:
        """
        Download highest quality vertical video from YouTube/TikTok
        
        Args:
            url: Video URL to download
            video_id: Optional custom video ID for naming
            
        Returns:
            Dictionary with download results:
            {
                'success': bool,
                'video_path': str,
                'video_id': str,
                'title': str,
                'duration': float,
                'error': str (if failed)
            }
        """
        if not self.validate_url(url):
            error_msg = f"Unsupported URL: {url}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        try:
            # Configure yt-dlp options for highest quality vertical video
            ydl_opts = {
                'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
                'outtmpl': str(self.output_dir / '%(id)s.%(ext)s'),
                'quiet': False,
                'no_warnings': False,
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Downloading video from {url}")
                info = ydl.extract_info(url, download=True)
                
                video_id = info.get('id', video_id or 'unknown')
                video_path = ydl.prepare_filename(info)
                
                # Ensure file exists
                if not os.path.exists(video_path):
                    # Try alternative extension
                    for ext in ['mp4', 'webm', 'mkv']:
                        alt_path = str(self.output_dir / f"{video_id}.{ext}")
                        if os.path.exists(alt_path):
                            video_path = alt_path
                            break
                
                result = {
                    'success': True,
                    'video_path': video_path,
                    'video_id': video_id,
                    'title': info.get('title', 'Untitled'),
                    'duration': info.get('duration', 0),
                    'width': info.get('width', 0),
                    'height': info.get('height', 0),
                    'description': info.get('description', ''),
                }
                
                logger.info(f"✓ Downloaded: {result['title']} ({result['duration']}s)")
                return result
                
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
    
    def cleanup(self, video_path: Optional[str] = None):
        """
        Clean up downloaded files
        
        Args:
            video_path: Specific file to remove, or None to clear temp directory
        """
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                logger.info(f"Cleaned up: {video_path}")
            elif video_path is None:
                # Clear entire temp directory
                import shutil
                if self.output_dir.exists():
                    shutil.rmtree(self.output_dir)
                    self.output_dir.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Cleaned up temp directory: {self.output_dir}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {str(e)}")


# Test the scraper independently
if __name__ == "__main__":
    scraper = VideoScraper()
    
    # Test URL validation
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.tiktok.com/@user/video/123456",
        "https://invalid-url.com"
    ]
    
    for url in test_urls:
        is_valid = scraper.validate_url(url)
        print(f"URL: {url}")
        print(f"Valid: {is_valid}")
        print()
    
    # Uncomment to test actual download
    # result = scraper.download_video("https://www.youtube.com/shorts/EXAMPLE")
    # print(f"Download result: {result}")
