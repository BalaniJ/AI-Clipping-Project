"""
Content Pipeline Module
Main orchestrator that coordinates all pipeline components
"""
import logging
from pathlib import Path
from typing import List, Dict, Optional
from scraper import VideoScraper
from processor import VideoProcessor
from caption_generator import CaptionGenerator
from storage import StorageManager
from bridge import OpenClawBridge
from config import (
    MIN_CLIP_LENGTH,
    MAX_CLIP_LENGTH,
    TARGET_CLIP_LENGTH,
    NUM_CAPTIONS,
    APPROVAL_ENABLED,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContentPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(
        self,
        cursor_api_key: Optional[str] = None,
        cursor_api_base: Optional[str] = None
    ):
        """
        Initialize the content pipeline
        
        Args:
            cursor_api_key: Optional Cursor API key (uses config if not provided)
            cursor_api_base: Optional Cursor API base URL (uses config if not provided)
        """
        self.scraper = VideoScraper()
        self.processor = VideoProcessor()
        self.caption_gen = CaptionGenerator(
            api_key=cursor_api_key,
            api_base=cursor_api_base
        )
        self.storage = StorageManager()
        self.bridge = OpenClawBridge() if APPROVAL_ENABLED else None
    
    def process_video(
        self,
        url: str,
        num_clips: int = 3,
        video_description: Optional[str] = None
    ) -> List[Dict]:
        """
        Full pipeline: Download → Process → Caption → Store
        
        Args:
            url: YouTube/TikTok URL to process
            num_clips: Number of clips to extract (default: 3)
            video_description: Optional description for caption generation
            
        Returns:
            List of post-ready bundles
        """
        logger.info(f"Starting pipeline for {url}")
        
        try:
            # Step 1: Validate and download
            logger.info("[1/5] Validating and downloading video...")
            if not self.scraper.validate_url(url):
                raise ValueError(f"Unsupported URL: {url}")
            
            download_result = self.scraper.download_video(url)
            if not download_result.get('success'):
                raise Exception(f"Download failed: {download_result.get('error')}")
            
            video_path = download_result['video_path']
            video_title = download_result.get('title', 'Untitled Video')
            video_duration = download_result.get('duration', 0)
            
            logger.info(f"✓ Downloaded: {video_title} ({video_duration}s)")
            
            # Use provided description or generate from title
            if not video_description:
                video_description = f"{video_title} - {download_result.get('description', '')[:200]}"
            
            # Step 2: Detect high-action segments
            logger.info("[2/5] Detecting high-action segments...")
            segments = self.processor.detect_high_action_segments(
                video_path,
                segment_duration=TARGET_CLIP_LENGTH
            )
            
            if not segments:
                logger.warning("No high-action segments found, using first portion of video")
                # Use first portion as fallback
                segments = [{
                    'start': 0,
                    'end': min(TARGET_CLIP_LENGTH, video_duration),
                    'duration': min(TARGET_CLIP_LENGTH, video_duration),
                    'score': 0.5,
                    'confidence': 0.5
                }]
            
            logger.info(f"✓ Detected {len(segments)} segments")
            
            # Step 3: Process and save clips
            logger.info(f"[3/5] Processing {min(num_clips, len(segments))} clips...")
            bundles = []
            
            for i, segment in enumerate(segments[:num_clips]):
                logger.info(f"  Processing clip {i+1}/{min(num_clips, len(segments))}...")
                
                # Ensure segment duration is within limits
                start = segment['start']
                end = segment['end']
                duration = end - start
                
                if duration < MIN_CLIP_LENGTH:
                    # Extend segment
                    extension = (MIN_CLIP_LENGTH - duration) / 2
                    start = max(0, start - extension)
                    end = min(video_duration, end + extension)
                elif duration > MAX_CLIP_LENGTH:
                    # Trim segment
                    end = start + MAX_CLIP_LENGTH
                
                # Generate clip name
                clip_name = f"clip_{i+1:02d}_{segment.get('score', 0.5):.2f}.mp4"
                clip_output_path = self.storage.clips_dir / clip_name
                
                # Crop to vertical
                self.processor.crop_to_vertical(
                    video_path,
                    str(clip_output_path),
                    start,
                    end
                )
                
                logger.info(f"  ✓ Processed clip {i+1}: {start:.2f}s - {end:.2f}s")
                
                # Step 4: Generate captions
                logger.info(f"  [4/5] Generating captions for clip {i+1}...")
                context = (
                    f"High-action segment (motion score: {segment.get('score', 0.5):.2f}, "
                    f"duration: {duration:.1f}s)"
                )
                
                captions = self.caption_gen.generate_captions(
                    video_description,
                    topic="viral content",
                    context=context
                )
                
                # Save captions
                self.storage.save_captions(captions, clip_name)
                logger.info(f"  ✓ Generated {len(captions)} captions")
                
                # Step 5: Send approval request via WhatsApp (if enabled)
                approval_response = None
                if self.bridge and APPROVAL_ENABLED:
                    logger.info(f"  [5/6] Sending approval request for clip {i+1}...")
                    
                    # Format caption for approval (use first caption)
                    caption_data = captions[0] if captions else {}
                    caption_text = self.caption_gen.format_for_instagram(caption_data)
                    
                    # Send approval request
                    approval_response = self.bridge.send_approval_request(
                        video_path=str(clip_output_path),
                        caption=caption_text,
                        metadata={
                            'source_url': url,
                            'source_title': video_title,
                            'clip_index': i + 1,
                            'clip_name': clip_name,
                            'start_time': start,
                            'end_time': end,
                            'duration': end - start,
                            'motion_score': segment.get('score', 0.5),
                            'confidence': segment.get('confidence', 0.5),
                        }
                    )
                    
                    if approval_response.get('status') == 'success':
                        logger.info(f"  ✓ Approval request sent successfully")
                    else:
                        logger.warning(f"  ⚠ Approval request failed: {approval_response.get('error', 'Unknown error')}")
                
                # Step 6: Create metadata
                metadata = {
                    'source_url': url,
                    'source_title': video_title,
                    'clip_index': i + 1,
                    'start_time': start,
                    'end_time': end,
                    'duration': end - start,
                    'motion_score': segment.get('score', 0.5),
                    'confidence': segment.get('confidence', 0.5),
                    'captions_count': len(captions),
                    'format': 'instagram_reels',
                    'aspect_ratio': '9:16',
                    'resolution': '1080x1920',
                    'approval_status': 'pending' if approval_response else 'not_required',
                    'approval_response': approval_response if approval_response else None
                }
                
                self.storage.save_metadata(metadata, clip_name)
                
                # Create post-ready bundle
                bundle = self.storage.get_post_ready_bundle(clip_name)
                bundle['approval_status'] = metadata['approval_status']
                bundle['approval_response'] = metadata['approval_response']
                bundles.append(bundle)
                logger.info(f"  ✓ Bundle ready: {clip_name}")
            
            # Step 7: Create manifest
            logger.info("[6/6] Creating posting manifest...")
            manifest_path = self.storage.create_posting_manifest()
            
            logger.info(f"✓ Pipeline complete! {len(bundles)} clips ready for posting")
            logger.info(f"  Manifest: {manifest_path}")
            logger.info(f"  Output directory: {self.storage.base_path}")
            
            return bundles
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise
        finally:
            # Cleanup downloaded video
            try:
                if 'video_path' in locals():
                    self.scraper.cleanup(video_path)
            except Exception as e:
                logger.warning(f"Cleanup warning: {str(e)}")
    
    def process_multiple_urls(
        self,
        urls: List[str],
        num_clips_per_video: int = 3
    ) -> List[Dict]:
        """
        Process multiple video URLs
        
        Args:
            urls: List of video URLs
            num_clips_per_video: Number of clips to extract per video
            
        Returns:
            List of all post-ready bundles
        """
        all_bundles = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing video {i}/{len(urls)}: {url}")
            logger.info(f"{'='*60}\n")
            
            try:
                bundles = self.process_video(url, num_clips_per_video)
                all_bundles.extend(bundles)
            except Exception as e:
                logger.error(f"Failed to process {url}: {str(e)}")
                continue
        
        logger.info(f"\n✓ Total: {len(all_bundles)} clips ready from {len(urls)} videos")
        return all_bundles
    
    def get_manifest(self) -> Dict:
        """
        Get the current posting manifest
        
        Returns:
            Manifest dictionary
        """
        manifest_path = self.storage.base_path / 'manifest.json'
        
        if not manifest_path.exists():
            # Create manifest if it doesn't exist
            self.storage.create_posting_manifest()
        
        import json
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)


# Main entry point
if __name__ == "__main__":
    import sys
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py <video_url> [num_clips]")
        print("\nExample:")
        print("  python pipeline.py https://www.youtube.com/watch?v=... 3")
        sys.exit(1)
    
    url = sys.argv[1]
    num_clips = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    
    # Check for API key
    if not os.getenv("CURSOR_API_KEY"):
        print("Warning: CURSOR_API_KEY not found in .env file")
        print("Caption generation may fail. Please set your API key.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Run pipeline
    pipeline = ContentPipeline()
    bundles = pipeline.process_video(url, num_clips)
    
    print(f"\n✓ Successfully processed {len(bundles)} clips!")
    print(f"  Output directory: {pipeline.storage.base_path}")
    print(f"  Manifest: {pipeline.storage.base_path / 'manifest.json'}")
