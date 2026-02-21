"""
Campaign-Specific Processor
Processes videos according to campaign-specific rules
"""
import sys
from pathlib import Path
import logging
from typing import Dict, List, Optional

# Add AI-Clipping-Project to path
sys.path.insert(0, str(Path(__file__).parent / "AI-Clipping-Project"))

from campaign_manager import CampaignManager
from pipeline import ContentPipeline
from processor import VideoProcessor
from caption_generator import CaptionGenerator
from storage import StorageManager
from bridge import OpenClawBridge
from config import APPROVAL_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CampaignProcessor:
    """Processes videos according to campaign-specific rules"""
    
    def __init__(self):
        """Initialize campaign processor"""
        self.campaign_manager = CampaignManager()
        self.pipeline = ContentPipeline()
        self.processor = VideoProcessor()
        self.caption_gen = CaptionGenerator()
        self.storage = StorageManager()
        self.bridge = OpenClawBridge() if APPROVAL_ENABLED else None
    
    def process_for_campaign(
        self,
        video_url: str,
        campaign_id: str,
        num_clips: int = 3
    ) -> List[Dict]:
        """
        Process a video according to campaign-specific rules
        
        Args:
            video_url: URL of video to process
            campaign_id: Campaign ID to process for
            num_clips: Number of clips to extract
            
        Returns:
            List of processed clip bundles
        """
        # Validate campaign exists
        campaign = self.campaign_manager.get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign '{campaign_id}' not found")
        
        # Validate source URL
        if not self.campaign_manager.validate_source_url(video_url, campaign_id):
            raise ValueError(
                f"URL is not from an approved source for campaign '{campaign_id}'. "
                f"Check campaign guidelines for approved sources."
            )
        
        logger.info(f"Processing video for campaign: {campaign_id}")
        logger.info(f"Video URL: {video_url}")
        
        # Get campaign-specific rules
        clipping_rules = self.campaign_manager.get_clipping_rules(campaign_id)
        caption_requirements = self.campaign_manager.get_caption_requirements(campaign_id)
        
        # Process video with campaign-aware clipping
        bundles = self._process_with_campaign_rules(
            video_url=video_url,
            campaign_id=campaign_id,
            clipping_rules=clipping_rules,
            caption_requirements=caption_requirements,
            num_clips=num_clips
        )
        
        return bundles
    
    def _process_with_campaign_rules(
        self,
        video_url: str,
        campaign_id: str,
        clipping_rules: Dict,
        caption_requirements: Dict,
        num_clips: int
    ) -> List[Dict]:
        """Process video following campaign-specific rules"""
        from scraper import VideoScraper
        from config import MIN_CLIP_LENGTH, MAX_CLIP_LENGTH
        
        scraper = VideoScraper()
        
        # Download video
        download_result = scraper.download_video(video_url)
        if not download_result.get('success'):
            raise Exception(f"Download failed: {download_result.get('error')}")
        
        video_path = download_result['video_path']
        video_title = download_result.get('title', 'Untitled')
        
        # Detect segments (campaign-aware)
        # For ADDICTED: Focus on wins, reactions, high-stakes moments
        segments = self.processor.detect_high_action_segments(
            video_path,
            segment_duration=30
        )
        
        # Apply campaign-specific filtering
        if clipping_rules.get("focus_on"):
            # Could enhance segment detection based on "focus_on" keywords
            # For now, we use motion detection but could add keyword-based filtering
            pass
        
        if not segments:
            # Fallback to first portion
            segments = [{
                'start': 0,
                'end': 30,
                'duration': 30,
                'score': 0.5,
                'confidence': 0.5
            }]
        
        # Process clips
        bundles = []
        campaign_output = self.campaign_manager.get_campaign_output_path(campaign_id)
        campaign_output.mkdir(parents=True, exist_ok=True)
        
        for i, segment in enumerate(segments[:num_clips]):
            start = segment['start']
            end = segment['end']
            
            # Generate clip name
            clip_name = f"{campaign_id}_clip_{i+1:02d}_{segment.get('score', 0.5):.2f}.mp4"
            clip_output_path = campaign_output / "clips" / clip_name
            clip_output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Crop to vertical (9:16)
            self.processor.crop_to_vertical(
                video_path,
                str(clip_output_path),
                start,
                end
            )
            
            # Generate campaign-specific captions
            caption_context = (
                f"Campaign: {campaign_id}. "
                f"Content: {video_title}. "
                f"Tone: {caption_requirements.get('tone', 'exciting')}. "
                f"Style: {caption_requirements.get('style', 'engaging')}"
            )
            
            captions = self.caption_gen.generate_captions(
                video_description=f"{video_title} - {campaign_id} campaign",
                topic="viral content",
                context=caption_context
            )
            
            # Apply campaign-specific caption requirements
            captions = self._apply_caption_requirements(captions, caption_requirements, "instagram")
            
            # Save captions
            captions_dir = campaign_output / "captions"
            captions_dir.mkdir(parents=True, exist_ok=True)
            captions_file = captions_dir / f"{Path(clip_name).stem}_captions.json"
            import json
            with open(captions_file, 'w', encoding='utf-8') as f:
                json.dump(captions, f, indent=2, ensure_ascii=False)
            
            # Create metadata
            metadata = {
                'campaign_id': campaign_id,
                'campaign_name': self.campaign_manager.get_campaign(campaign_id).get('campaign_name'),
                'source_url': video_url,
                'source_title': video_title,
                'clip_index': i + 1,
                'start_time': start,
                'end_time': end,
                'duration': end - start,
                'motion_score': segment.get('score', 0.5),
                'clipping_rules_applied': clipping_rules,
                'caption_requirements': caption_requirements,
                'approval_status': 'pending',
                'posted': False
            }
            
            metadata_dir = campaign_output / "metadata"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            metadata_file = metadata_dir / f"{Path(clip_name).stem}_metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            # Send approval request
            if self.bridge:
                caption_text = self.caption_gen.format_for_instagram(captions[0] if captions else {})
                approval_response = self.bridge.send_approval_request(
                    video_path=str(clip_output_path),
                    caption=caption_text,
                    metadata=metadata
                )
                metadata['approval_response'] = approval_response
            
            # Create bundle
            bundle = {
                'campaign_id': campaign_id,
                'clip_id': Path(clip_name).stem,
                'video_path': str(clip_output_path),
                'captions_path': str(captions_file),
                'metadata_path': str(metadata_file),
                'captions': captions,
                'metadata': metadata,
                'timestamp': datetime.now().isoformat()
            }
            
            bundles.append(bundle)
        
        return bundles
    
    def _apply_caption_requirements(
        self,
        captions: List[Dict],
        requirements: Dict,
        platform: str
    ) -> List[Dict]:
        """Apply campaign-specific caption requirements"""
        tagging = requirements.get('tagging', {})
        tags = tagging.get('tags', [])
        
        # Add required tags to each caption
        for caption in captions:
            existing_hashtags = caption.get('hashtags', [])
            # Add campaign tags
            caption['hashtags'] = existing_hashtags + tags
        
        return captions


# CLI Interface
if __name__ == "__main__":
    import sys
    
    processor = CampaignProcessor()
    
    if len(sys.argv) < 4:
        print("Campaign Processor")
        print("\nUsage:")
        print("  python campaign_processor.py process <video_url> <campaign_id> [num_clips]")
        print("\nExample:")
        print("  python campaign_processor.py process https://youtube.com/watch?v=abc123 addicted 3")
        sys.exit(1)
    
    video_url = sys.argv[2]
    campaign_id = sys.argv[3]
    num_clips = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    
    try:
        bundles = processor.process_for_campaign(video_url, campaign_id, num_clips)
        print(f"\n✓ Processed {len(bundles)} clips for campaign '{campaign_id}'")
        print(f"  Output: {processor.campaign_manager.get_campaign_output_path(campaign_id)}")
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
