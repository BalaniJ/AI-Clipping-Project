# Automated Content Pipeline for Instagram Reels

A modular Python system for scraping, processing, and generating captions for vertical video content from YouTube and TikTok.

## Features

- **Video Scraping**: Downloads highest quality vertical videos using `yt-dlp`
- **High-Action Detection**: Detects engaging segments using motion detection or clipping API
- **Vertical Cropping**: Automatically crops videos to 9:16 aspect ratio (Instagram Reels format)
- **AI Caption Generation**: Generates 5 viral, engagement-focused captions using Cursor API
- **Structured Storage**: Organizes output into date-based folders (`/output/YYYY-MM-DD/`)
- **Post-Ready Format**: Outputs formatted for `instagrapi` and `clawdbot` automation

## Project Structure

```
.
├── config.py              # Configuration settings
├── scraper.py             # Video download module
├── processor.py           # Video processing & cropping module
├── caption_generator.py    # AI caption generation module
├── storage.py             # File organization module
├── bridge.py              # OpenClaw gateway bridge for WhatsApp approval
├── pipeline.py            # Main orchestrator
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
└── README.md             # This file
```

## Installation

1. **Clone or download this repository**

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
```

Edit `.env` and add your configuration:
```
CURSOR_API_KEY=your_actual_cursor_api_key_here
OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789/api/message
WHATSAPP_APPROVAL_NUMBER=+917705060708
APPROVAL_ENABLED=true
```

## Usage

### Basic Usage

Process a single video:
```bash
python pipeline.py https://www.youtube.com/watch?v=VIDEO_ID 3
```

The second parameter (3) is the number of clips to extract. Default is 3.

### Programmatic Usage

```python
from pipeline import ContentPipeline

# Initialize pipeline
pipeline = ContentPipeline()

# Process a single video
bundles = pipeline.process_video(
    url="https://www.youtube.com/watch?v=VIDEO_ID",
    num_clips=3,
    video_description="Optional description for better captions"
)

# Process multiple videos
urls = [
    "https://www.youtube.com/watch?v=VIDEO1",
    "https://www.tiktok.com/@user/video/123456"
]
all_bundles = pipeline.process_multiple_urls(urls, num_clips_per_video=3)

# Get posting manifest
manifest = pipeline.get_manifest()
```

### Testing Individual Modules

Each module can be tested independently:

**Test Scraper**:
```bash
python scraper.py
```

**Test Processor**:
```bash
python processor.py
```

**Test Caption Generator**:
```bash
python caption_generator.py
```

**Test Storage**:
```bash
python storage.py
```

**Test Bridge**:
```bash
python bridge.py
```

## Output Structure

The pipeline creates a structured output directory:

```
output/
└── 2024-01-15/
    ├── clips/
    │   ├── clip_01_0.92.mp4
    │   ├── clip_02_0.87.mp4
    │   └── clip_03_0.81.mp4
    ├── captions/
    │   ├── clip_01_0.92_captions.json
    │   ├── clip_02_0.87_captions.json
    │   └── clip_03_0.81_captions.json
    ├── metadata/
    │   ├── clip_01_0.92_metadata.json
    │   ├── clip_02_0.87_metadata.json
    │   └── clip_03_0.81_metadata.json
    ├── temp/
    │   └── (temporary downloaded videos)
    └── manifest.json
```

## WhatsApp Approval Workflow

The pipeline includes an integrated approval system that sends clips to WhatsApp via OpenClaw gateway for review before posting.

### Setup

1. **Ensure OpenClaw gateway is running** on `http://127.0.0.1:18789`
2. **Configure in `.env`**:
   ```
   OPENCLAW_GATEWAY_URL=http://127.0.0.1:18789/api/message
   WHATSAPP_APPROVAL_NUMBER=+917705060708
   APPROVAL_ENABLED=true
   ```

### How It Works

1. **Video Processing**: After a video is downloaded and clipped, the pipeline:
   - Generates AI captions
   - Crops video to 9:16 format
   - Sends the clip and caption to your WhatsApp via OpenClaw gateway

2. **Approval Request**: You receive a WhatsApp message with:
   - The clipped video
   - AI-generated caption
   - Source URL and metadata
   - Options to Approve, Reject, or Edit

3. **Status Tracking**: Each clip's approval status is saved in metadata:
   - `approval_status`: "pending", "approved", "rejected", or "not_required"
   - `approval_response`: Full response from OpenClaw gateway

### Disabling Approval

Set `APPROVAL_ENABLED=false` in `.env` to skip the approval step and process clips directly.

### Testing the Bridge

Test the OpenClaw connection independently:
```bash
python bridge.py
```

This will:
- Check gateway health
- Send a test text message
- Test video sending (if test video exists)

## Integration with Automation Tools

### instagrapi Integration

```python
from instagrapi import Client
from pipeline import ContentPipeline

# Initialize pipeline and get bundles
pipeline = ContentPipeline()
bundles = pipeline.get_manifest()['clips']

# Initialize Instagram client
cl = Client()
cl.login(username="your_username", password="your_password")

# Post each clip
for bundle in bundles:
    # Get first caption (or rotate through all 5)
    caption_data = bundle['captions'][0]
    full_caption = f"{caption_data['caption']}\n\n{' '.join(caption_data['hashtags'])}"
    
    # Upload clip
    cl.clip_upload(
        path=bundle['video_path'],
        caption=full_caption
    )
```

### clawdbot Integration

The manifest.json file is formatted for clawdbot automation:

```json
{
  "date": "2024-01-15",
  "timestamp": "2024-01-15T12:00:00",
  "total_count": 3,
  "clips": [
    {
      "clip_id": "clip_01_0.92",
      "video_path": "output/2024-01-15/clips/clip_01_0.92.mp4",
      "captions": [...],
      "metadata": {...}
    }
  ]
}
```

## Configuration

Edit `config.py` to customize:

- **Video Settings**: Clip length, resolution, bitrate
- **Motion Detection**: Sensitivity thresholds
- **Caption Settings**: Number of captions, hashtag count
- **Storage Paths**: Output directories

## Clipping API Integration

To use an external clipping API instead of motion detection:

1. Set `CLIPPING_API_ENABLED=true` in `.env`
2. Add your `CLIPPING_API_KEY` and `CLIPPING_API_URL`
3. The processor will automatically use the API when available

## Requirements

- Python 3.8+
- FFmpeg (required by moviepy)
- Cursor API key (for caption generation)

### Installing FFmpeg

**Windows**:
- Download from https://ffmpeg.org/download.html
- Add to PATH

**macOS**:
```bash
brew install ffmpeg
```

**Linux**:
```bash
sudo apt-get install ffmpeg
```

## Troubleshooting

### "Download failed" errors
- Check your internet connection
- Verify the URL is accessible
- Some videos may have download restrictions

### "Caption generation failed" errors
- Verify your CURSOR_API_KEY is set correctly
- Check your API quota/limits
- Fallback captions will be used if API fails

### "Motion detection found no segments"
- Try lowering `MOTION_THRESHOLD` in `config.py`
- The pipeline will use the first portion of the video as fallback

### FFmpeg errors
- Ensure FFmpeg is installed and in your PATH
- Check video codec compatibility

### "Approval request failed" errors
- Verify OpenClaw gateway is running on `http://127.0.0.1:18789`
- Check that `OPENCLAW_GATEWAY_URL` in `.env` matches your gateway endpoint
- Ensure WhatsApp number format is correct (include country code with +)
- Test the bridge independently: `python bridge.py`
- Check gateway logs for detailed error messages

## License

This project is provided as-is for personal use.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review module-specific test scripts
3. Verify all dependencies are installed correctly
