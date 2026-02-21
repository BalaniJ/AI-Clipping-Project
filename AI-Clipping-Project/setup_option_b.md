# Option B Setup Guide: Creator Clipping Service

This guide will help you set up the automated creator clipping service that monitors YouTube channels and posts clips to Instagram, with Whop.com payment integration.

## Quick Start

### 1. Install Additional Dependencies

```bash
pip install instagrapi
```

Or update your requirements:
```bash
pip install -r AI-Clipping-Project/requirements.txt
```

### 2. Configure Instagram Account

Add to your `.env` file:
```
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
```

**Important**: Instagram may require 2FA. Handle the challenge manually the first time.

### 3. Add Your First Creator to Monitor

```bash
python monitor_creator.py add "Creator Name" "https://youtube.com/@channel" "instagram_username" "https://whop.com/your-payment-link"
```

Example:
```bash
python monitor_creator.py add "MrBeast" "https://youtube.com/@MrBeast" "your_instagram" "https://whop.com/checkout/abc123"
```

### 4. Test the Monitoring

Check for new videos:
```bash
python monitor_creator.py check
```

List all monitored creators:
```bash
python monitor_creator.py list
```

### 5. Start Continuous Monitoring

Run the monitoring loop (checks every hour by default):
```bash
python monitor_creator.py run
```

This will:
- Check all creators for new videos every hour
- Auto-process new videos through the pipeline
- Send you notifications on WhatsApp
- Generate Whop.com payment links

### 6. Set Up Instagram Auto-Posting

First, login to Instagram:
```bash
python auto_poster.py login your_username your_password
```

Post approved clips:
```bash
python auto_poster.py post-approved
```

## Clawdbot Integration

Once JB Clippings is set up on WhatsApp, you can control everything via messages:

### Add a Creator
```
JB, add creator "MrBeast" from https://youtube.com/@MrBeast
Instagram: your_account
Whop link: https://whop.com/checkout/abc123
```

### Check for New Videos
```
JB, check for new videos from all creators
```

### Start Monitoring
```
JB, start monitoring all creators. Check every 60 minutes.
```

### Post Approved Clips
```
JB, post all approved clips to Instagram
```

## Workflow Overview

1. **Monitoring**: `monitor_creator.py` watches YouTube channels
2. **Processing**: When new video detected → runs `pipeline.py`
3. **Approval**: Clips sent to WhatsApp via `bridge.py`
4. **Posting**: Approved clips posted via `auto_poster.py`
5. **Payment**: Whop.com links generated for creators

## Configuration Files

- `creator_config.json` - Manages all monitored creators
- `whop_config.json` - Payment tracking and links
- `processed_videos.json` - Tracks which videos have been processed

## Next Steps

1. Add your first creator using the command above
2. Test with a single check: `python monitor_creator.py check`
3. Set up Clawdbot commands (see above)
4. Start the monitoring loop
5. Share Whop.com links with creators for payment

## Troubleshooting

**Instagram Login Issues**: 
- Handle 2FA challenge manually first time
- Session is saved in `instagram_session.json`

**No New Videos Found**:
- Check channel URL is correct
- Verify creator is active in `creator_config.json`

**Rate Limits**:
- Adjust `check_interval_minutes` in `creator_config.json`
- Instagram posting has built-in delays to avoid detection
