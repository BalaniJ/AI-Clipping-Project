"""
OpenClaw Gateway Bridge Module
Connects to OpenClaw gateway to send WhatsApp messages for approval workflow
"""
import requests
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from config import (
    OPENCLAW_GATEWAY_URL,
    WHATSAPP_APPROVAL_NUMBER,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OpenClawBridge:
    """Bridge to OpenClaw gateway for WhatsApp messaging"""
    
    def __init__(
        self,
        gateway_url: Optional[str] = None,
        phone_number: Optional[str] = None
    ):
        """
        Initialize OpenClaw bridge
        
        Args:
            gateway_url: OpenClaw gateway URL (defaults to config)
            phone_number: WhatsApp number for approvals (defaults to config)
        """
        self.gateway_url = gateway_url or OPENCLAW_GATEWAY_URL
        self.phone_number = phone_number or WHATSAPP_APPROVAL_NUMBER
        self.timeout = 30
    
    def send_approval_request(
        self,
        video_path: str,
        caption: str,
        metadata: Optional[Dict] = None,
        phone_number: Optional[str] = None
    ) -> Dict:
        """
        Send clipped video and caption to WhatsApp for approval
        
        Args:
            video_path: Path to the clipped video file
            caption: AI-generated caption text
            metadata: Additional metadata (source URL, clip info, etc.)
            phone_number: Override default phone number
            
        Returns:
            Dictionary with response status and details
        """
        try:
            # Verify video file exists
            video_file = Path(video_path)
            if not video_file.exists():
                raise FileNotFoundError(f"Video file not found: {video_path}")
            
            # Get absolute path for the gateway
            abs_video_path = str(video_file.absolute())
            
            # Format message with caption and metadata
            message = self._format_approval_message(caption, metadata)
            
            # Prepare payload for OpenClaw gateway
            # Try multiple formats - adjust based on your OpenClaw API requirements
            payload = {
                "phone": phone_number or self.phone_number,
                "message": message,
                "media": abs_video_path,  # File path - OpenClaw may accept this directly
                "media_type": "video",
                "filename": video_file.name,
                "metadata": metadata or {}
            }
            
            # Alternative format (uncomment if your OpenClaw API requires this):
            # payload = {
            #     "phone": phone_number or self.phone_number,
            #     "message": message,
            #     "media": {
            #         "type": "video",
            #         "path": abs_video_path,
            #         "filename": video_file.name
            #     },
            #     "metadata": metadata or {}
            # }
            
            logger.info(f"Sending approval request to {phone_number or self.phone_number}")
            logger.info(f"Video: {video_file.name}")
            
            # Send request to OpenClaw gateway
            response = requests.post(
                self.gateway_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✓ Approval request sent successfully")
                return {
                    "status": "success",
                    "message_id": result.get("id") or result.get("messageId"),
                    "timestamp": result.get("timestamp"),
                    "response": result
                }
            else:
                error_msg = f"Gateway returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {
                    "status": "error",
                    "code": response.status_code,
                    "error": response.text,
                    "details": error_msg
                }
                
        except FileNotFoundError as e:
            logger.error(str(e))
            return {
                "status": "error",
                "error": str(e),
                "type": "file_not_found"
            }
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "type": "network_error"
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "type": "unknown"
            }
    
    def _format_approval_message(
        self,
        caption: str,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Format the approval message sent to WhatsApp
        
        Args:
            caption: Caption text
            metadata: Additional metadata
            
        Returns:
            Formatted message string
        """
        message_parts = [
            "🎬 *Content Approval Request*",
            "",
            f"*Caption:*\n{caption}",
            ""
        ]
        
        if metadata:
            if metadata.get('source_url'):
                message_parts.append(f"*Source:* {metadata['source_url']}")
            if metadata.get('duration'):
                message_parts.append(f"*Duration:* {metadata['duration']:.1f}s")
            if metadata.get('motion_score'):
                message_parts.append(f"*Action Score:* {metadata['motion_score']:.2f}")
            message_parts.append("")
        
        message_parts.extend([
            "📋 *Reply with:*",
            "✅ Approve - Post this clip",
            "❌ Reject - Skip this clip",
            "📝 Edit - Request caption revision"
        ])
        
        return "\n".join(message_parts)
    
    def send_text_message(
        self,
        message: str,
        phone_number: Optional[str] = None
    ) -> Dict:
        """
        Send a simple text message (no media)
        
        Args:
            message: Text message to send
            phone_number: Override default phone number
            
        Returns:
            Response dictionary
        """
        try:
            payload = {
                "phone": phone_number or self.phone_number,
                "message": message
            }
            
            response = requests.post(
                self.gateway_url,
                json=payload,
                timeout=self.timeout,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                return {
                    "status": "success",
                    "response": response.json()
                }
            else:
                return {
                    "status": "error",
                    "code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            logger.error(f"Failed to send text message: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def check_gateway_health(self) -> bool:
        """
        Check if OpenClaw gateway is accessible
        
        Returns:
            True if gateway is reachable, False otherwise
        """
        try:
            # Try a simple health check endpoint or ping the main endpoint
            health_url = self.gateway_url.replace("/api/message", "/health")
            response = requests.get(health_url, timeout=5)
            return response.status_code == 200
        except:
            # If health endpoint doesn't exist, try the main endpoint
            try:
                response = requests.get(
                    self.gateway_url.replace("/api/message", ""),
                    timeout=5
                )
                return True
            except:
                logger.warning("Could not verify gateway health - will attempt to send anyway")
                return False


# Test the bridge independently
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize bridge
    bridge = OpenClawBridge()
    
    # Test gateway health
    print("Checking gateway health...")
    is_healthy = bridge.check_gateway_health()
    print(f"Gateway health: {'✓ Healthy' if is_healthy else '⚠ Could not verify'}")
    
    # Test sending a text message
    print("\nTesting text message...")
    result = bridge.send_text_message("Test message from bridge.py")
    print(f"Result: {result}")
    
    # Test sending approval request (requires a test video file)
    test_video = "test_video.mp4"
    if Path(test_video).exists():
        print(f"\nTesting approval request with {test_video}...")
        result = bridge.send_approval_request(
            video_path=test_video,
            caption="This is a test caption for approval 🔥",
            metadata={
                "source_url": "https://youtube.com/watch?v=test",
                "duration": 30.5,
                "motion_score": 0.85
            }
        )
        print(f"Result: {result}")
    else:
        print(f"\nSkipping video test - {test_video} not found")
        print("To test video sending, place a test video file in the project directory")
