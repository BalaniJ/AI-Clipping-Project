"""
Video Processor Module
Detects high-action segments and crops videos to 9:16 aspect ratio
Supports both motion detection and clipping API integration
"""
import cv2
import numpy as np
from moviepy.editor import VideoFileClip
import logging
import requests
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from config import (
    MOTION_THRESHOLD,
    FRAME_SAMPLE_RATE,
    TARGET_ASPECT_RATIO,
    OUTPUT_RESOLUTION,
    MIN_CLIP_LENGTH,
    MAX_CLIP_LENGTH,
    TARGET_CLIP_LENGTH,
    OUTPUT_CODEC,
    OUTPUT_BITRATE,
    CLIPPING_API_ENABLED,
    CLIPPING_API_KEY,
    CLIPPING_API_URL,
    OPTICAL_FLOW_PYR_SCALE,
    OPTICAL_FLOW_LEVELS,
    OPTICAL_FLOW_WINSIZE,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video processing: motion detection, cropping, and clipping"""
    
    def __init__(self):
        """Initialize the video processor"""
        self.motion_threshold = MOTION_THRESHOLD
        self.frame_sample_rate = FRAME_SAMPLE_RATE
        self.use_clipping_api = CLIPPING_API_ENABLED
        self.clipping_api_key = CLIPPING_API_KEY
        self.clipping_api_url = CLIPPING_API_URL
    
    def detect_high_action_segments(
        self, 
        video_path: str, 
        segment_duration: int = None
    ) -> List[Dict]:
        """
        Detect high-action segments using motion detection or clipping API
        
        Args:
            video_path: Path to input video
            segment_duration: Target duration for each segment (defaults to TARGET_CLIP_LENGTH)
            
        Returns:
            List of segment dictionaries with 'start', 'end', 'duration', and 'score'
        """
        if segment_duration is None:
            segment_duration = TARGET_CLIP_LENGTH
        
        if self.use_clipping_api and self.clipping_api_key:
            logger.info("Using clipping API for segment detection")
            return self._detect_segments_with_api(video_path, segment_duration)
        else:
            logger.info("Using motion detection for segment detection")
            return self._detect_segments_with_motion(video_path, segment_duration)
    
    def _detect_segments_with_api(self, video_path: str, segment_duration: int) -> List[Dict]:
        """
        Use clipping API to detect high-action segments
        
        Args:
            video_path: Path to video file
            segment_duration: Target segment duration
            
        Returns:
            List of segment dictionaries
        """
        try:
            # Upload video to clipping API
            with open(video_path, 'rb') as video_file:
                files = {'video': video_file}
                headers = {'Authorization': f'Bearer {self.clipping_api_key}'}
                data = {
                    'target_duration': segment_duration,
                    'min_duration': MIN_CLIP_LENGTH,
                    'max_duration': MAX_CLIP_LENGTH,
                }
                
                response = requests.post(
                    f"{self.clipping_api_url}/analyze",
                    files=files,
                    headers=headers,
                    data=data,
                    timeout=300
                )
                
                if response.status_code == 200:
                    result = response.json()
                    segments = []
                    for seg in result.get('segments', []):
                        segments.append({
                            'start': seg['start_time'],
                            'end': seg['end_time'],
                            'duration': seg['end_time'] - seg['start_time'],
                            'score': seg.get('action_score', 0.5),
                            'confidence': seg.get('confidence', 0.5)
                        })
                    logger.info(f"API detected {len(segments)} segments")
                    return segments
                else:
                    logger.warning(f"API request failed: {response.status_code}, falling back to motion detection")
                    return self._detect_segments_with_motion(video_path, segment_duration)
                    
        except Exception as e:
            logger.warning(f"Clipping API error: {str(e)}, falling back to motion detection")
            return self._detect_segments_with_motion(video_path, segment_duration)
    
    def _detect_segments_with_motion(self, video_path: str, segment_duration: int) -> List[Dict]:
        """
        Detect high-action segments using optical flow motion detection
        
        Args:
            video_path: Path to video file
            segment_duration: Target segment duration
            
        Returns:
            List of segment dictionaries
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError(f"Could not open video: {video_path}")
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            total_duration = total_frames / fps if fps > 0 else 0
            
            logger.info(f"Analyzing video: {fps:.2f} FPS, {total_frames} frames, {total_duration:.2f}s")
            
            motion_scores = []
            prev_frame = None
            frame_idx = 0
            
            # Process frames
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Sample frames for speed
                if frame_idx % self.frame_sample_rate != 0:
                    frame_idx += 1
                    continue
                
                # Resize for faster processing
                frame_resized = cv2.resize(frame, (320, 240))
                gray = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2GRAY)
                
                if prev_frame is not None:
                    # Calculate optical flow for motion detection
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_frame, gray, None,
                        OPTICAL_FLOW_PYR_SCALE,
                        OPTICAL_FLOW_LEVELS,
                        OPTICAL_FLOW_WINSIZE,
                        3, 5, 1.2, 0
                    )
                    
                    # Calculate motion magnitude
                    magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    motion_score = np.mean(magnitude)
                    motion_scores.append({
                        'frame': frame_idx,
                        'time': frame_idx / fps,
                        'score': motion_score
                    })
                
                prev_frame = gray
                frame_idx += 1
            
            cap.release()
            
            if not motion_scores:
                logger.warning("No motion data collected")
                return []
            
            # Normalize motion scores
            scores = [m['score'] for m in motion_scores]
            max_score = max(scores)
            min_score = min(scores)
            score_range = max_score - min_score if max_score > min_score else 1
            
            for m in motion_scores:
                m['normalized_score'] = (m['score'] - min_score) / score_range
            
            # Extract segments with high motion
            segments = self._extract_segments_from_scores(
                motion_scores, fps, segment_duration
            )
            
            logger.info(f"Detected {len(segments)} high-action segments")
            return segments
            
        except Exception as e:
            logger.error(f"Motion detection failed: {str(e)}")
            return []
    
    def _extract_segments_from_scores(
        self, 
        motion_scores: List[Dict], 
        fps: float, 
        segment_duration: int
    ) -> List[Dict]:
        """
        Extract continuous high-motion segments from motion scores
        
        Args:
            motion_scores: List of motion score dictionaries
            fps: Video frame rate
            segment_duration: Target segment duration
            
        Returns:
            List of segment dictionaries
        """
        if not motion_scores:
            return []
        
        # Calculate threshold (mean + std)
        normalized_scores = [m['normalized_score'] for m in motion_scores]
        mean_score = np.mean(normalized_scores)
        std_score = np.std(normalized_scores)
        threshold = mean_score + (std_score * 0.5)
        
        # Find high-motion regions
        segments = []
        in_segment = False
        segment_start = None
        segment_scores = []
        
        window_size = int(fps * segment_duration / self.frame_sample_rate)
        step_size = window_size // 2
        
        for i in range(0, len(motion_scores) - window_size, step_size):
            window = motion_scores[i:i + window_size]
            avg_score = np.mean([m['normalized_score'] for m in window])
            
            if avg_score > threshold:
                start_time = window[0]['time']
                end_time = window[-1]['time']
                duration = end_time - start_time
                
                # Ensure duration is within limits
                if duration < MIN_CLIP_LENGTH:
                    # Extend segment
                    extension = (MIN_CLIP_LENGTH - duration) / 2
                    start_time = max(0, start_time - extension)
                    end_time = min(motion_scores[-1]['time'], end_time + extension)
                    duration = end_time - start_time
                
                if duration >= MIN_CLIP_LENGTH and duration <= MAX_CLIP_LENGTH:
                    segments.append({
                        'start': start_time,
                        'end': end_time,
                        'duration': duration,
                        'score': avg_score,
                        'confidence': min(1.0, avg_score * 1.5)
                    })
        
        # Sort by score (highest first) and remove overlaps
        segments = sorted(segments, key=lambda x: x['score'], reverse=True)
        segments = self._remove_overlapping_segments(segments)
        
        return segments
    
    def _remove_overlapping_segments(self, segments: List[Dict]) -> List[Dict]:
        """Remove overlapping segments, keeping highest scoring ones"""
        if not segments:
            return []
        
        non_overlapping = []
        for seg in segments:
            overlaps = False
            for existing in non_overlapping:
                # Check if segments overlap
                if not (seg['end'] <= existing['start'] or seg['start'] >= existing['end']):
                    overlaps = True
                    break
            
            if not overlaps:
                non_overlapping.append(seg)
        
        return non_overlapping
    
    def crop_to_vertical(
        self, 
        video_path: str, 
        output_path: str, 
        start_time: float, 
        end_time: float
    ) -> str:
        """
        Crop video segment to 9:16 aspect ratio (vertical format)
        
        Args:
            video_path: Path to input video
            output_path: Path to save cropped video
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            Path to output video
        """
        try:
            logger.info(f"Cropping segment {start_time:.2f}s - {end_time:.2f}s to 9:16")
            
            # Load video clip
            clip = VideoFileClip(video_path)
            
            # Extract segment
            segment = clip.subclip(start_time, end_time)
            
            # Get dimensions
            w, h = segment.size
            target_w, target_h = OUTPUT_RESOLUTION
            
            # Calculate crop dimensions for 9:16 aspect ratio
            target_aspect = target_w / target_h  # 9/16 = 0.5625
            
            if w / h > target_aspect:
                # Video is wider than target - crop width (center crop)
                new_w = int(h * target_aspect)
                x_offset = (w - new_w) // 2
                cropped = segment.crop(x1=x_offset, y1=0, x2=x_offset + new_w, y2=h)
            else:
                # Video is taller than target - crop height (center crop)
                new_h = int(w / target_aspect)
                y_offset = (h - new_h) // 2
                cropped = segment.crop(x1=0, y1=y_offset, x2=w, y2=y_offset + new_h)
            
            # Resize to exact output resolution
            final = cropped.resize(height=target_h)
            
            # Set standard frame rate
            final = final.set_fps(30)
            
            # Write video file
            final.write_videofile(
                output_path,
                codec=OUTPUT_CODEC,
                audio_codec='aac',
                bitrate=OUTPUT_BITRATE,
                verbose=False,
                logger=None,
                preset='medium'
            )
            
            # Clean up
            segment.close()
            cropped.close()
            final.close()
            clip.close()
            
            logger.info(f"✓ Cropped video saved: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Crop failed: {str(e)}")
            raise


# Test the processor independently
if __name__ == "__main__":
    processor = VideoProcessor()
    
    # Test with a sample video
    test_video = "test_video.mp4"
    if Path(test_video).exists():
        segments = processor.detect_high_action_segments(test_video)
        print(f"Found {len(segments)} segments:")
        for i, seg in enumerate(segments, 1):
            print(f"  {i}. {seg['start']:.2f}s - {seg['end']:.2f}s (score: {seg['score']:.3f})")
        
        if segments:
            output_path = "test_output_clip.mp4"
            processor.crop_to_vertical(
                test_video,
                output_path,
                segments[0]['start'],
                segments[0]['end']
            )
            print(f"✓ Test clip created: {output_path}")
    else:
        print(f"Test video not found: {test_video}")
        print("Place a test video file to test the processor")
