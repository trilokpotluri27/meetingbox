"""
Mock Backend Client

For testing device UI without real backend running.
Set environment variable: MOCK_BACKEND=1
"""

import asyncio
import logging
from typing import List, Dict, Optional, AsyncIterator
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)


class MockBackendClient:
    """
    Mock implementation of BackendClient for testing.
    
    Simulates backend behavior without actual API calls.
    """
    
    def __init__(self, base_url: str = None):
        self.current_recording = None
        self.meetings = self._generate_mock_meetings()
        logger.info("Using MOCK backend client")
    
    async def close(self):
        """No-op for mock"""
        pass
    
    # ========================================================================
    # MOCK DATA GENERATORS
    # ========================================================================
    
    def _generate_mock_meetings(self) -> List[Dict]:
        """Generate fake meeting data for testing"""
        now = datetime.now()
        
        meetings = [
            {
                "id": "1",
                "title": "Q4 Planning Session",
                "start_time": (now - timedelta(hours=2)).isoformat(),
                "end_time": (now - timedelta(hours=1, minutes=15)).isoformat(),
                "duration": 2700,  # 45 minutes
                "status": "completed",
                "pending_actions": 3,
                "summary": {
                    "summary": "Team discussed Q4 priorities and resource allocation. Key focus on hiring and feature roadmap.",
                    "action_items": [
                        {"task": "Sarah: Update budget proposal by Friday", "assignee": "Sarah Chen", "due_date": "2026-02-14", "completed": False},
                        {"task": "Mike: Schedule engineering review", "assignee": "Mike Johnson", "due_date": "2026-02-18", "completed": False},
                        {"task": "Lisa: Send revised proposal to client", "assignee": "Lisa Park", "due_date": "2026-02-20", "completed": True}
                    ],
                    "decisions": [
                        "Delay Feature X to Q1 2027",
                        "Hire 2 additional senior engineers"
                    ],
                    "topics": ["Q4 Planning", "Resource Allocation", "Hiring", "Feature Roadmap"],
                    "sentiment": "Productive and collaborative"
                }
            },
            {
                "id": "2",
                "title": "Client Proposal Review - Acme Corp",
                "start_time": (now - timedelta(days=1)).isoformat(),
                "end_time": (now - timedelta(days=1) + timedelta(hours=1)).isoformat(),
                "duration": 3600,
                "status": "completed",
                "pending_actions": 0,
                "summary": {
                    "summary": "Reviewed pricing and timeline for Acme Corp proposal. Team aligned on $52K pricing with 10-week delivery.",
                    "action_items": [
                        {"task": "John: Finalize proposal by Wednesday", "assignee": "John Martinez", "due_date": "2026-02-12", "completed": True}
                    ],
                    "decisions": [
                        "Pricing set at $52,000",
                        "Timeline extended to 10 weeks"
                    ],
                    "topics": ["Proposal", "Pricing", "Timeline"],
                    "sentiment": "Focused and decisive"
                }
            },
            {
                "id": "3",
                "title": "Team Standup",
                "start_time": (now - timedelta(days=2)).isoformat(),
                "end_time": (now - timedelta(days=2) + timedelta(minutes=15)).isoformat(),
                "duration": 900,
                "status": "completed",
                "pending_actions": 0,
                "summary": {
                    "summary": "Daily standup covering progress and blockers.",
                    "action_items": [],
                    "decisions": [],
                    "topics": ["Standup", "Progress Updates"],
                    "sentiment": "Brief and informative"
                }
            }
        ]
        
        return meetings
    
    # ========================================================================
    # MEETINGS API (MOCK)
    # ========================================================================
    
    async def start_recording(self) -> Dict:
        """Mock start recording"""
        await asyncio.sleep(0.5)  # Simulate network delay
        
        self.current_recording = {
            "session_id": f"mock_{datetime.now().timestamp()}",
            "status": "recording",
            "start_time": datetime.now().isoformat()
        }
        
        logger.info(f"[MOCK] Started recording: {self.current_recording['session_id']}")
        return self.current_recording
    
    async def stop_recording(self, session_id: str) -> Dict:
        """Mock stop recording"""
        await asyncio.sleep(0.5)
        
        result = {
            "status": "processing",
            "session_id": session_id,
            "duration": random.randint(300, 3600)
        }
        
        self.current_recording = None
        logger.info(f"[MOCK] Stopped recording: {session_id}")
        return result
    
    async def pause_recording(self, session_id: str) -> Dict:
        """Mock pause recording"""
        await asyncio.sleep(0.3)
        return {"status": "paused", "session_id": session_id}
    
    async def resume_recording(self, session_id: str) -> Dict:
        """Mock resume recording"""
        await asyncio.sleep(0.3)
        return {"status": "recording", "session_id": session_id}
    
    async def get_meetings(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """Mock get meetings list"""
        await asyncio.sleep(0.3)
        return self.meetings[offset:offset + limit]
    
    async def get_meeting_detail(self, meeting_id: str) -> Dict:
        """Mock get meeting detail"""
        await asyncio.sleep(0.3)
        
        # Find meeting in mock data
        meeting = next((m for m in self.meetings if m['id'] == meeting_id), None)
        
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")
        
        # Add mock transcript segments
        meeting['segments'] = [
            {"segment_num": 1, "start_time": 0, "end_time": 5, "text": "So let's talk about Q4 roadmap.", "speaker_id": "1", "confidence": 0.95},
            {"segment_num": 2, "start_time": 5, "end_time": 12, "text": "Sarah, you mentioned concerns about the timeline. Can you elaborate?", "speaker_id": "1", "confidence": 0.93},
            {"segment_num": 3, "start_time": 12, "end_time": 25, "text": "Yes, I think we're being too aggressive. The engineering team is stretched thin.", "speaker_id": "2", "confidence": 0.97}
        ]
        
        return meeting
    
    async def delete_meeting(self, meeting_id: str) -> None:
        """Mock delete meeting"""
        await asyncio.sleep(0.3)
        self.meetings = [m for m in self.meetings if m['id'] != meeting_id]
        logger.info(f"[MOCK] Deleted meeting: {meeting_id}")
    
    # ========================================================================
    # SETTINGS API (MOCK)
    # ========================================================================
    
    async def get_settings(self) -> Dict:
        """Mock get settings"""
        await asyncio.sleep(0.2)
        return {
            "device_name": "Conference Room A",
            "timezone": "America/New_York"
        }
    
    async def update_settings(self, settings: Dict) -> Dict:
        """Mock update settings"""
        await asyncio.sleep(0.3)
        logger.info(f"[MOCK] Updated settings: {settings}")
        return settings
    
    # ========================================================================
    # INTEGRATIONS API (MOCK)
    # ========================================================================
    
    async def get_integrations(self) -> List[Dict]:
        """Mock get integrations"""
        await asyncio.sleep(0.2)
        return [
            {
                "id": "gmail",
                "name": "Gmail",
                "description": "Send AI-drafted emails",
                "connected": False,
                "icon": "email"
            },
            {
                "id": "calendar",
                "name": "Google Calendar",
                "description": "Auto-schedule meetings",
                "connected": True,
                "icon": "calendar"
            }
        ]
    
    async def get_integration_auth_url(self, integration_id: str) -> str:
        """Mock get auth URL"""
        await asyncio.sleep(0.2)
        return f"https://mock-oauth.example.com/auth?integration={integration_id}"
    
    async def disconnect_integration(self, integration_id: str) -> None:
        """Mock disconnect integration"""
        await asyncio.sleep(0.3)
        logger.info(f"[MOCK] Disconnected integration: {integration_id}")
    
    # ========================================================================
    # SYSTEM API (MOCK)
    # ========================================================================
    
    async def get_system_info(self) -> Dict:
        """Mock get system info"""
        await asyncio.sleep(0.2)
        return {
            "device_name": "Conference Room A",
            "firmware_version": "1.0.0-dev",
            "ip_address": "192.168.1.100",
            "wifi_ssid": "Office-Network",
            "wifi_signal": 85,
            "storage_used": 25000000000,  # 25 GB
            "storage_total": 512000000000,  # 512 GB
            "uptime": 86400,  # 1 day
            "meetings_count": len(self.meetings)
        }
    
    async def check_for_updates(self) -> Dict:
        """Mock check for updates"""
        await asyncio.sleep(1.0)
        return {
            "update_available": False,
            "current_version": "1.0.0",
            "latest_version": None,
            "release_notes": None
        }
    
    async def install_update(self) -> Dict:
        """Mock install update"""
        await asyncio.sleep(2.0)
        return {"status": "success"}
    
    # ========================================================================
    # WIFI API (MOCK)
    # ========================================================================
    
    async def get_wifi_networks(self) -> List[Dict]:
        """Mock get WiFi networks"""
        await asyncio.sleep(1.0)
        return [
            {"ssid": "Office-Network", "signal_strength": 85, "security": "wpa2", "connected": True},
            {"ssid": "Office-Guest", "signal_strength": 70, "security": "wpa2", "connected": False},
            {"ssid": "Conference-5G", "signal_strength": 60, "security": "wpa2", "connected": False}
        ]
    
    async def connect_wifi(self, ssid: str, password: str = None) -> Dict:
        """Mock connect WiFi"""
        await asyncio.sleep(2.0)
        logger.info(f"[MOCK] Connected to WiFi: {ssid}")
        return {"status": "connected", "message": f"Connected to {ssid}"}
    
    async def disconnect_wifi(self) -> None:
        """Mock disconnect WiFi"""
        await asyncio.sleep(0.5)
        logger.info("[MOCK] Disconnected from WiFi")
    
    # ========================================================================
    # WEBSOCKET (MOCK)
    # ========================================================================
    
    async def subscribe_events(self) -> AsyncIterator[Dict]:
        """
        Mock WebSocket events.
        
        Simulates periodic events for testing.
        """
        logger.info("[MOCK] WebSocket connected")
        
        while True:
            await asyncio.sleep(5)  # Send event every 5 seconds
            
            # Randomly send different event types
            event_type = random.choice([
                "heartbeat",
                "transcription_update",
                "status_update"
            ])
            
            if event_type == "heartbeat":
                yield {"type": "heartbeat", "data": {"timestamp": datetime.now().isoformat()}}
            
            elif event_type == "transcription_update" and self.current_recording:
                yield {
                    "type": "transcription_update",
                    "data": {
                        "session_id": self.current_recording['session_id'],
                        "text": random.choice([
                            "So I think we should focus on Q4 priorities first...",
                            "The engineering team has capacity concerns...",
                            "Let's schedule a follow-up meeting next week..."
                        ]),
                        "speaker_id": str(random.randint(1, 3))
                    }
                }
            
            elif event_type == "status_update":
                yield {
                    "type": "status_update",
                    "data": {
                        "cpu_usage": random.randint(20, 60),
                        "memory_usage": random.randint(40, 70),
                        "temperature": random.randint(45, 65)
                    }
                }
    
    # ========================================================================
    # HEALTH CHECK (MOCK)
    # ========================================================================
    
    async def health_check(self) -> bool:
        """Mock health check - always returns True"""
        await asyncio.sleep(0.1)
        return True
