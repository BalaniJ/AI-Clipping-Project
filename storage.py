"""
Storage Manager Module
Organizes processed clips, captions, and metadata into structured folders
Formats output for instagrapi and clawdbot automation
"""
import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging
from config import (
    TODAY_OUTPUT,
    CLIPS_DIR,
    CAPTIONS_DIR,
    METADATA_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StorageManager:
    """Manages file organization and metadata storage"""
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize storage manager
        
        Args:
            base_path: Base output directory (defaults to TODAY_OUTPUT from config)
        """
        self.base_path = base_path or TODAY_OUTPUT
        self.clips_dir = self.base_path / "clips"
        self.captions_dir = self.base_path / "captions"
        self.metadata_dir = self.base_path / "metadata"
        
        # Ensure directories exist
        for dir_path in [self.clips_dir, self.captions_dir, self.metadata_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def save_clip(self, video_path: str, clip_name: Optional[str] = None) -> str:
        """
        Save processed clip to structured folder
        
        Args:
            video_path: Path to processed video file
            clip_name: Optional custom name for the clip
            
        Returns:
            Path to saved clip
        """
        if not clip_name:
            timestamp = datetime.now().strftime('%H%M%S')
            clip_name = f"clip_{timestamp}.mp4"
        
        # Ensure .mp4 extension
        if not clip_name.endswith('.mp4'):
            clip_name = f"{Path(clip_name).stem}.mp4"
        
        output_path = self.clips_dir / clip_name
        
        try:
            # Copy video file
            shutil.copy2(video_path, output_path)
            logger.info(f"✓ Clip saved: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save clip: {str(e)}")
            raise
    
    def save_captions(self, captions_list: List[Dict], clip_name: str) -> str:
        """
        Save captions as JSON file
        
        Args:
            captions_list: List of caption dictionaries
            clip_name: Name of the associated clip
            
        Returns:
            Path to saved captions file
        """
        # Generate caption filename from clip name
        clip_stem = Path(clip_name).stem
        caption_filename = f"{clip_stem}_captions.json"
        output_path = self.captions_dir / caption_filename
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(captions_list, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Captions saved: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save captions: {str(e)}")
            raise
    
    def save_metadata(
        self, 
        metadata: Dict, 
        clip_name: str
    ) -> str:
        """
        Save video metadata for automation tools
        
        Args:
            metadata: Metadata dictionary
            clip_name: Name of the associated clip
            
        Returns:
            Path to saved metadata file
        """
        clip_stem = Path(clip_name).stem
        metadata_filename = f"{clip_stem}_metadata.json"
        output_path = self.metadata_dir / metadata_filename
        
        try:
            # Add timestamp and format info
            metadata['timestamp'] = datetime.now().isoformat()
            metadata['clip_filename'] = clip_name
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Metadata saved: {output_path}")
            return str(output_path)
        except Exception as e:
            logger.error(f"Failed to save metadata: {str(e)}")
            raise
    
    def get_post_ready_bundle(self, clip_name: str) -> Dict:
        """
        Get structured bundle ready for instagrapi/clawdbot automation
        
        Args:
            clip_name: Name of the clip
            
        Returns:
            Dictionary with all paths and data needed for posting
        """
        clip_stem = Path(clip_name).stem
        
        # Load captions
        captions_path = self.captions_dir / f"{clip_stem}_captions.json"
        captions = []
        if captions_path.exists():
            with open(captions_path, 'r', encoding='utf-8') as f:
                captions = json.load(f)
        
        # Load metadata
        metadata_path = self.metadata_dir / f"{clip_stem}_metadata.json"
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        
        # Build bundle
        bundle = {
            'clip_id': clip_stem,
            'video_path': str(self.clips_dir / clip_name),
            'captions_path': str(captions_path) if captions_path.exists() else None,
            'metadata_path': str(metadata_path) if metadata_path.exists() else None,
            'captions': captions,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat(),
            'date_folder': self.base_path.name,
        }
        
        return bundle
    
    def create_posting_manifest(self) -> str:
        """
        Create a manifest file listing all ready-to-post items
        
        Returns:
            Path to manifest file
        """
        manifest = {
            'date': self.base_path.name,
            'timestamp': datetime.now().isoformat(),
            'clips': []
        }
        
        # Find all clips
        for clip_file in self.clips_dir.glob('*.mp4'):
            bundle = self.get_post_ready_bundle(clip_file.name)
            manifest['clips'].append(bundle)
        
        manifest['total_count'] = len(manifest['clips'])
        
        # Save manifest
        manifest_path = self.base_path / 'manifest.json'
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Manifest created: {manifest_path} ({manifest['total_count']} clips)")
        return str(manifest_path)
    
    def get_all_post_ready_bundles(self) -> List[Dict]:
        """
        Get all post-ready bundles for the current date
        
        Returns:
            List of bundle dictionaries
        """
        bundles = []
        
        for clip_file in self.clips_dir.glob('*.mp4'):
            bundle = self.get_post_ready_bundle(clip_file.name)
            bundles.append(bundle)
        
        return bundles


# Test the storage manager independently
if __name__ == "__main__":
    storage = StorageManager()
    
    # Test saving a dummy clip
    test_clip_path = "test_clip.mp4"
    if Path(test_clip_path).exists():
        saved_path = storage.save_clip(test_clip_path, "test_clip_001.mp4")
        print(f"✓ Saved clip: {saved_path}")
    
    # Test saving captions
    test_captions = [
        {
            'caption': 'Test caption 1 🔥',
            'hashtags': ['#test', '#viral']
        },
        {
            'caption': 'Test caption 2 💯',
            'hashtags': ['#test', '#trending']
        }
    ]
    captions_path = storage.save_captions(test_captions, "test_clip_001.mp4")
    print(f"✓ Saved captions: {captions_path}")
    
    # Test saving metadata
    test_metadata = {
        'source_url': 'https://youtube.com/watch?v=test',
        'duration': 30.5,
        'motion_score': 0.85
    }
    metadata_path = storage.save_metadata(test_metadata, "test_clip_001.mp4")
    print(f"✓ Saved metadata: {metadata_path}")
    
    # Test getting bundle
    bundle = storage.get_post_ready_bundle("test_clip_001.mp4")
    print(f"\n✓ Post-ready bundle:")
    print(json.dumps(bundle, indent=2))
    
    # Test manifest
    manifest_path = storage.create_posting_manifest()
    print(f"\n✓ Manifest: {manifest_path}")
