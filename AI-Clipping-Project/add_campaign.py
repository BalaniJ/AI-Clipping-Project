"""
Helper script to add a new Whop.com campaign
Creates the campaign folder structure and guidelines.json
"""
import json
import sys
from pathlib import Path
from datetime import datetime

def create_campaign():
    """Interactive campaign creation"""
    print("=" * 60)
    print("Add New Whop.com Campaign")
    print("=" * 60)
    print()
    
    # Get campaign details
    campaign_id = input("Campaign ID (e.g., 'addicted', 'creator_name'): ").strip().lower()
    campaign_name = input("Campaign Name (full title): ").strip()
    whop_url = input("Whop.com Campaign URL: ").strip()
    
    print("\n--- Clipping Rules ---")
    critical_rules = []
    print("Enter critical clipping rules (one per line, empty to finish):")
    while True:
        rule = input("  Rule: ").strip()
        if not rule:
            break
        critical_rules.append(rule)
    
    focus_points = []
    print("\nWhat to focus on (one per line, empty to finish):")
    while True:
        point = input("  Focus: ").strip()
        if not point:
            break
        focus_points.append(point)
    
    print("\n--- Approved Sources ---")
    print("Enter approved source URLs (one per line, empty to finish):")
    print("Format: type:url (e.g., youtube_longform:https://youtube.com/watch?v=...)")
    print("Types: youtube_longform, youtube_shorts, google_drive, twitch_vod, kick_clip")
    
    sources = {
        "youtube_longform": [],
        "youtube_shorts": [],
        "google_drive": [],
        "twitch_vod": [],
        "kick_clip": []
    }
    
    while True:
        source_input = input("  Source: ").strip()
        if not source_input:
            break
        
        if ":" in source_input:
            source_type, url = source_input.split(":", 1)
            if source_type in sources:
                sources[source_type].append(url.strip())
            else:
                print(f"  ⚠ Unknown type '{source_type}', skipping")
        else:
            # Assume YouTube if no type specified
            if "youtube.com" in source_input or "youtu.be" in source_input:
                if "/shorts/" in source_input:
                    sources["youtube_shorts"].append(source_input)
                else:
                    sources["youtube_longform"].append(source_input)
            else:
                print(f"  ⚠ Could not determine type for '{source_input}', skipping")
    
    print("\n--- Tagging Requirements ---")
    instagram_tags = input("Instagram tags (comma-separated, or empty): ").strip()
    youtube_tags = input("YouTube tags (comma-separated, or empty): ").strip()
    
    print("\n--- Caption Guidelines ---")
    caption_style = input("Caption style/guidelines: ").strip() or "flexible, engaging"
    caption_tone = input("Caption tone (e.g., exciting, high-energy): ").strip() or "exciting"
    
    print("\n--- Requirements ---")
    keep_live_days = input("Keep posts live for (days, default 30): ").strip() or "30"
    min_engagement = input("Minimum engagement rate (e.g., 0.01 for 1%): ").strip() or "0.01"
    
    # Build guidelines structure
    guidelines = {
        "campaign_name": campaign_name,
        "campaign_id": campaign_id,
        "whop_campaign_url": whop_url,
        "clipping_rules": {
            "critical": critical_rules,
            "focus_on": focus_points,
            "goal": "attention + excitement"
        },
        "approved_sources": sources,
        "tagging_requirements": {
            "instagram": {
                "required": bool(instagram_tags),
                "tags": [t.strip() for t in instagram_tags.split(",") if t.strip()]
            },
            "youtube": {
                "required": bool(youtube_tags),
                "tags": [t.strip() for t in youtube_tags.split(",") if t.strip()]
            }
        },
        "caption_guidelines": {
            "style": caption_style,
            "tone": caption_tone,
            "rejection_reason": "If it makes 0 sense to the content you posted, it will be rejected"
        },
        "on_screen_text": {
            "required": False,
            "guidelines": "Do what makes sense with the content"
        },
        "requirements": {
            "use_approved_content_only": True,
            "tag_in_caption": True,
            "high_quality": True,
            "english_only": True,
            "keep_live_days": int(keep_live_days),
            "engagement_rate": {
                "minimum": float(min_engagement),
                "example": f"1,000 views = {int(1000 * float(min_engagement))} likes"
            }
        },
        "not_allowed": [],
        "ftc_compliance": True,
        "dedicated_page": {
            "required": False
        }
    }
    
    # Create campaign folder
    campaigns_dir = Path("campaigns")
    campaigns_dir.mkdir(exist_ok=True)
    
    campaign_folder = campaigns_dir / campaign_id
    campaign_folder.mkdir(exist_ok=True)
    
    # Save guidelines
    guidelines_file = campaign_folder / "guidelines.json"
    with open(guidelines_file, 'w', encoding='utf-8') as f:
        json.dump(guidelines, f, indent=2, ensure_ascii=False)
    
    print(f"\n✓ Campaign created: {campaign_folder}")
    print(f"  Guidelines: {guidelines_file}")
    print(f"\nYou can now process videos for this campaign:")
    print(f"  python campaign_processor.py process <video_url> {campaign_id}")


if __name__ == "__main__":
    try:
        create_campaign()
    except KeyboardInterrupt:
        print("\n\nCancelled")
    except Exception as e:
        print(f"\n✗ Error: {e}")
