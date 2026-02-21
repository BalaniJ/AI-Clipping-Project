"""
Whop.com Integration
Manages creator payments and tracking for clipping service
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WhopIntegration:
    """Manages Whop.com payment links and tracking"""
    
    def __init__(self, config_file: str = "whop_config.json"):
        """
        Initialize Whop integration
        
        Args:
            config_file: Path to Whop configuration file
        """
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """Load Whop configuration"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "whop_account": None,
            "default_pricing": {
                "per_clip": 5.00,
                "per_video": 15.00,
                "monthly_subscription": 50.00
            },
            "creators": {}
        }
    
    def _save_config(self):
        """Save configuration"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def create_payment_link(
        self,
        creator_name: str,
        video_title: str,
        num_clips: int,
        pricing_type: str = "per_video"
    ) -> str:
        """
        Generate a Whop.com payment link for a creator
        
        Args:
            creator_name: Name of the creator
            video_title: Title of the video processed
            num_clips: Number of clips created
            pricing_type: "per_clip", "per_video", or "monthly"
            
        Returns:
            Whop.com payment link
        """
        # Get pricing
        pricing = self.config["default_pricing"]
        
        if pricing_type == "per_clip":
            amount = pricing["per_clip"] * num_clips
        elif pricing_type == "per_video":
            amount = pricing["per_video"]
        else:
            amount = pricing["monthly_subscription"]
        
        # Store creator payment info
        if creator_name not in self.config["creators"]:
            self.config["creators"][creator_name] = {
                "payment_links": [],
                "total_earned": 0.00,
                "total_clips": 0
            }
        
        # Generate payment link (this would integrate with Whop API)
        # For now, return a template link
        payment_link = (
            f"https://whop.com/checkout?creator={creator_name}"
            f"&amount={amount}&clips={num_clips}&video={video_title}"
        )
        
        # Store payment record
        payment_record = {
            "link": payment_link,
            "amount": amount,
            "video_title": video_title,
            "num_clips": num_clips,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        self.config["creators"][creator_name]["payment_links"].append(payment_record)
        self.config["creators"][creator_name]["total_clips"] += num_clips
        self._save_config()
        
        logger.info(f"Created payment link for {creator_name}: ${amount}")
        return payment_link
    
    def get_creator_summary(self, creator_name: str) -> Dict:
        """Get payment summary for a creator"""
        if creator_name not in self.config["creators"]:
            return {
                "total_earned": 0.00,
                "total_clips": 0,
                "pending_payments": 0
            }
        
        creator = self.config["creators"][creator_name]
        pending = len([p for p in creator["payment_links"] if p["status"] == "pending"])
        
        return {
            "total_earned": creator["total_earned"],
            "total_clips": creator["total_clips"],
            "pending_payments": pending,
            "payment_links": creator["payment_links"]
        }
    
    def mark_payment_completed(self, creator_name: str, payment_link: str):
        """Mark a payment as completed"""
        if creator_name not in self.config["creators"]:
            return
        
        for payment in self.config["creators"][creator_name]["payment_links"]:
            if payment["link"] == payment_link:
                payment["status"] = "completed"
                payment["completed_at"] = datetime.now().isoformat()
                self.config["creators"][creator_name]["total_earned"] += payment["amount"]
                self._save_config()
                logger.info(f"Payment completed for {creator_name}: ${payment['amount']}")
                return


# CLI Interface
if __name__ == "__main__":
    import sys
    
    whop = WhopIntegration()
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python whop_integration.py link <creator> <video_title> <num_clips>")
        print("  python whop_integration.py summary <creator>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "link":
        if len(sys.argv) < 5:
            print("Error: Need creator name, video title, and number of clips")
            sys.exit(1)
        
        creator = sys.argv[2]
        video_title = sys.argv[3]
        num_clips = int(sys.argv[4])
        
        link = whop.create_payment_link(creator, video_title, num_clips)
        print(f"Payment link: {link}")
    
    elif command == "summary":
        if len(sys.argv) < 3:
            print("Error: Need creator name")
            sys.exit(1)
        
        creator = sys.argv[2]
        summary = whop.get_creator_summary(creator)
        print(f"\nSummary for {creator}:")
        print(f"  Total Earned: ${summary['total_earned']:.2f}")
        print(f"  Total Clips: {summary['total_clips']}")
        print(f"  Pending Payments: {summary['pending_payments']}")
