"""
Caption Generator Module
Generates viral Instagram Reel captions using Cursor API client library
"""
import json
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from config import (
    CURSOR_API_KEY,
    CURSOR_API_BASE,
    NUM_CAPTIONS,
    MAX_CAPTION_LENGTH,
    HASHTAG_COUNT,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptionGenerator:
    """Generates engaging Instagram Reel captions using Cursor API"""
    
    def __init__(self, api_key: Optional[str] = None, api_base: Optional[str] = None):
        """
        Initialize the caption generator
        
        Args:
            api_key: Cursor API key (defaults to CURSOR_API_KEY from config)
            api_base: Cursor API base URL (defaults to CURSOR_API_BASE from config)
        """
        self.api_key = api_key or CURSOR_API_KEY
        self.api_base = api_base or CURSOR_API_BASE
        
        if not self.api_key:
            raise ValueError("CURSOR_API_KEY is required. Set it in .env file or pass as parameter.")
        
        # Initialize OpenAI client (Cursor API is OpenAI-compatible)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base
        )
    
    def generate_captions(
        self, 
        video_description: str, 
        topic: str = "viral content",
        context: Optional[str] = None
    ) -> List[Dict]:
        """
        Generate viral, engagement-focused Instagram Reel captions
        
        Args:
            video_description: Description of the video content
            topic: Topic/category of the content
            context: Additional context (e.g., motion score, duration)
            
        Returns:
            List of caption dictionaries with 'caption' and 'hashtags' keys
        """
        try:
            prompt = self._build_prompt(video_description, topic, context)
            
            logger.info("Generating captions via Cursor API...")
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a viral content strategist specializing in Instagram Reels. "
                            "Your captions maximize engagement, shares, and comments. "
                            "You understand trending formats, hooks, and hashtag strategies. "
                            "Always return valid JSON format."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.8,
                max_tokens=2000
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            try:
                # Try to parse as JSON
                result = json.loads(content)
                
                # Handle different response formats
                if isinstance(result, dict):
                    if 'captions' in result:
                        captions = result['captions']
                    elif 'data' in result:
                        captions = result['data']
                    else:
                        # Assume the dict itself contains caption data
                        captions = [result] if 'caption' in result else []
                elif isinstance(result, list):
                    captions = result
                else:
                    captions = []
                
                # Validate and format captions
                formatted_captions = self._format_captions(captions)
                
                logger.info(f"✓ Generated {len(formatted_captions)} captions")
                return formatted_captions
                
            except json.JSONDecodeError:
                logger.warning("Could not parse JSON response, attempting fallback parsing")
                return self._parse_fallback_response(content)
                
        except Exception as e:
            logger.error(f"Caption generation failed: {str(e)}")
            return self._generate_fallback_captions(video_description, topic)
    
    def _build_prompt(
        self, 
        video_description: str, 
        topic: str, 
        context: Optional[str]
    ) -> str:
        """Build the prompt for caption generation"""
        context_text = f"\nAdditional Context: {context}" if context else ""
        
        return f"""Generate exactly {NUM_CAPTIONS} viral, highly engaging Instagram Reel captions.

Video Description: {video_description}
Topic/Category: {topic}{context_text}

Requirements for each caption:
1. Hook the viewer in the first 3-5 words
2. Keep main caption under {MAX_CAPTION_LENGTH} characters (excluding hashtags)
3. Include {HASHTAG_COUNT} relevant, trending hashtags
4. Use 2-4 strategic emojis
5. Include a call-to-action (question, tag someone, save/share prompt)
6. Make it shareable and relatable
7. Use power words: "viral", "wait for it", "obsessed", "game changer", etc.
8. Match trending Reels algorithm preferences

Return as JSON with this exact structure:
{{
  "captions": [
    {{
      "caption": "Your engaging caption text here with emojis 🎯",
      "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3", "#hashtag4", "#hashtag5"]
    }},
    ...
  ]
}}

Make each caption unique and optimized for maximum engagement."""
    
    def _format_captions(self, captions: List[Dict]) -> List[Dict]:
        """
        Format and validate captions
        
        Args:
            captions: Raw caption data from API
            
        Returns:
            Formatted list of caption dictionaries
        """
        formatted = []
        
        for i, cap in enumerate(captions[:NUM_CAPTIONS]):
            if isinstance(cap, dict):
                caption_text = cap.get('caption', '')
                hashtags = cap.get('hashtags', [])
                
                # Ensure hashtags is a list
                if isinstance(hashtags, str):
                    hashtags = [h.strip() for h in hashtags.split() if h.startswith('#')]
                elif not isinstance(hashtags, list):
                    hashtags = []
                
                # Limit hashtag count
                hashtags = hashtags[:HASHTAG_COUNT]
                
                formatted.append({
                    'caption': caption_text,
                    'hashtags': hashtags
                })
            elif isinstance(cap, str):
                # Handle string-only responses
                formatted.append({
                    'caption': cap,
                    'hashtags': []
                })
        
        # Ensure we have exactly NUM_CAPTIONS
        while len(formatted) < NUM_CAPTIONS:
            formatted.append({
                'caption': f"Check out this amazing content! 🔥",
                'hashtags': ['#viral', '#trending', '#reels', '#fyp', '#foryou']
            })
        
        return formatted[:NUM_CAPTIONS]
    
    def _parse_fallback_response(self, content: str) -> List[Dict]:
        """
        Fallback parser if JSON parsing fails
        
        Args:
            content: Raw response content
            
        Returns:
            List of caption dictionaries
        """
        import re
        
        captions = []
        
        # Try to extract caption blocks
        caption_pattern = r'"caption":\s*"([^"]+)"'
        hashtag_pattern = r'"hashtags":\s*\[(.*?)\]'
        
        caption_matches = re.findall(caption_pattern, content)
        hashtag_matches = re.findall(hashtag_pattern, content)
        
        for i, caption_text in enumerate(caption_matches[:NUM_CAPTIONS]):
            hashtags = []
            if i < len(hashtag_matches):
                hashtag_str = hashtag_matches[i]
                hashtags = re.findall(r'"(#\w+)"', hashtag_str)
            
            captions.append({
                'caption': caption_text,
                'hashtags': hashtags[:HASHTAG_COUNT]
            })
        
        # If no structured data found, split by lines
        if not captions:
            lines = [l.strip() for l in content.split('\n') if l.strip()]
            for line in lines[:NUM_CAPTIONS]:
                # Extract hashtags from line
                hashtags = re.findall(r'#\w+', line)
                caption = re.sub(r'#\w+', '', line).strip()
                
                captions.append({
                    'caption': caption or "Amazing content! 🔥",
                    'hashtags': hashtags[:HASHTAG_COUNT]
                })
        
        return self._format_captions(captions)
    
    def _generate_fallback_captions(
        self, 
        video_description: str, 
        topic: str
    ) -> List[Dict]:
        """
        Generate fallback captions if API fails
        
        Args:
            video_description: Video description
            topic: Content topic
            
        Returns:
            List of basic caption dictionaries
        """
        logger.warning("Using fallback captions")
        
        base_captions = [
            {
                'caption': f"Wait for it... 🔥 This {topic} content is INSANE!",
                'hashtags': ['#viral', '#trending', '#reels', '#fyp', '#foryou']
            },
            {
                'caption': f"You won't believe this! 😱 {video_description[:50]}...",
                'hashtags': ['#viral', '#trending', '#reels', '#fyp', '#foryou']
            },
            {
                'caption': f"Obsessed with this! 💯 Tag someone who needs to see this 👇",
                'hashtags': ['#viral', '#trending', '#reels', '#fyp', '#foryou']
            },
            {
                'caption': f"Game changer! 🎯 Save this for later! {video_description[:40]}...",
                'hashtags': ['#viral', '#trending', '#reels', '#fyp', '#foryou']
            },
            {
                'caption': f"This is why I'm obsessed! 🔥 What do you think? Comment below! 👇",
                'hashtags': ['#viral', '#trending', '#reels', '#fyp', '#foryou']
            },
        ]
        
        return base_captions[:NUM_CAPTIONS]
    
    def format_for_instagram(self, caption_data: Dict) -> str:
        """
        Format caption data for Instagram posting
        
        Args:
            caption_data: Caption dictionary with 'caption' and 'hashtags'
            
        Returns:
            Formatted string ready for Instagram
        """
        caption = caption_data.get('caption', '')
        hashtags = ' '.join(caption_data.get('hashtags', []))
        
        if hashtags:
            return f"{caption}\n\n{hashtags}"
        return caption


# Test the caption generator independently
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    if not os.getenv("CURSOR_API_KEY"):
        print("Error: CURSOR_API_KEY not found in .env file")
        print("Please set your Cursor API key in .env file")
    else:
        generator = CaptionGenerator()
        
        test_description = "Epic gaming moment with amazing headshot in competitive match"
        captions = generator.generate_captions(
            test_description,
            topic="gaming",
            context="High-action segment with fast-paced gameplay"
        )
        
        print(f"\nGenerated {len(captions)} captions:\n")
        for i, cap in enumerate(captions, 1):
            print(f"Caption {i}:")
            print(generator.format_for_instagram(cap))
            print("-" * 50)
