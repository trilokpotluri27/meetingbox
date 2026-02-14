"""
Backend API Client

Handles all communication with the MeetingBox FastAPI backend.
"""

import asyncio
import json
import logging
from typing import List, Dict, Optional, AsyncIterator
from datetime import datetime

import httpx
import websockets
from websockets.exceptions import ConnectionClosed

from config import (
    BACKEND_URL,
    BACKEND_WS_URL,
    API_TIMEOUT,
    WS_RECONNECT_DELAY,
    WS_MAX_RECONNECT_ATTEMPTS
)

logger = logging.getLogger(__name__)


class BackendClient:
    """
    Client for MeetingBox backend API.
    
    Provides methods to:
    - Start/stop recordings
    - Fetch meetings and details
    - Update settings
    - Subscribe to real-time events via WebSocket
    """
    
    def __init__(self, base_url: str = BACKEND_URL):
        self.base_url = base_url.rstrip('/')
        self.ws_url = BACKEND_WS_URL
        self.client = httpx.AsyncClient(timeout=API_TIMEOUT)
        self.ws_connection = None
        self._ws_reconnect_attempts = 0
        
    async def close(self):
        """Close HTTP client and WebSocket connection"""
        await self.client.aclose()
        if self.ws_connection:
            await self.ws_connection.close()
    
    # ========================================================================
    # MEETINGS API
    # ========================================================================
    
    async def start_recording(self) -> Dict:
        """
        Start a new recording.
        
        Returns:
            {
                "session_id": str,
                "status": "recording",
                "start_time": str (ISO format)
            }
        """
        try:
            response = await self.client.post(f"{self.base_url}/api/meetings/start")
            response.raise_for_status()
            data = response.json()
            logger.info(f"Started recording: {data['session_id']}")
            return data
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise
    
    async def stop_recording(self, session_id: str) -> Dict:
        """
        Stop an active recording.
        
        Args:
            session_id: The session ID returned from start_recording()
        
        Returns:
            {
                "status": "processing",
                "session_id": str,
                "duration": int (seconds)
            }
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/meetings/{session_id}/stop"
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"Stopped recording: {session_id}")
            return data
        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            raise
    
    async def pause_recording(self, session_id: str) -> Dict:
        """Pause an active recording"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/meetings/{session_id}/pause"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to pause recording: {e}")
            raise
    
    async def resume_recording(self, session_id: str) -> Dict:
        """Resume a paused recording"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/meetings/{session_id}/resume"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to resume recording: {e}")
            raise
    
    async def get_meetings(self, limit: int = 20, offset: int = 0) -> List[Dict]:
        """
        Get list of recent meetings.
        
        Args:
            limit: Maximum number of meetings to return
            offset: Skip this many meetings (for pagination)
        
        Returns:
            List of meeting objects:
            [
                {
                    "id": str,
                    "title": str,
                    "start_time": str (ISO),
                    "end_time": str | None,
                    "duration": int | None (seconds),
                    "status": "recording" | "transcribing" | "completed",
                    "pending_actions": int
                },
                ...
            ]
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/meetings/",
                params={"limit": limit, "offset": offset}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch meetings: {e}")
            raise
    
    async def get_meeting_detail(self, meeting_id: str) -> Dict:
        """
        Get detailed information about a single meeting.
        
        Args:
            meeting_id: The meeting ID
        
        Returns:
            {
                "id": str,
                "title": str,
                "start_time": str,
                "duration": int,
                "status": str,
                "summary": {
                    "summary": str,
                    "action_items": [...],
                    "decisions": [...],
                    "topics": [...],
                    "sentiment": str
                },
                "segments": [...]  # Transcript segments
            }
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/meetings/{meeting_id}"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch meeting {meeting_id}: {e}")
            raise
    
    async def delete_meeting(self, meeting_id: str) -> None:
        """Delete a meeting"""
        try:
            response = await self.client.delete(
                f"{self.base_url}/api/meetings/{meeting_id}"
            )
            response.raise_for_status()
            logger.info(f"Deleted meeting: {meeting_id}")
        except Exception as e:
            logger.error(f"Failed to delete meeting {meeting_id}: {e}")
            raise
    
    # ========================================================================
    # SETTINGS API
    # ========================================================================
    
    async def get_settings(self) -> Dict:
        """Get current device settings"""
        try:
            response = await self.client.get(f"{self.base_url}/api/settings")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch settings: {e}")
            raise
    
    async def update_settings(self, settings: Dict) -> Dict:
        """
        Update device settings.
        
        Args:
            settings: Dictionary of settings to update
                {
                    "device_name": str,
                    "timezone": str,
                    ...
                }
        """
        try:
            response = await self.client.patch(
                f"{self.base_url}/api/settings",
                json=settings
            )
            response.raise_for_status()
            logger.info(f"Updated settings: {settings}")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            raise
    
    # ========================================================================
    # INTEGRATIONS API
    # ========================================================================
    
    async def get_integrations(self) -> List[Dict]:
        """Get list of available integrations and their status"""
        try:
            response = await self.client.get(f"{self.base_url}/api/integrations")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch integrations: {e}")
            raise
    
    async def get_integration_auth_url(self, integration_id: str) -> str:
        """
        Get OAuth authorization URL for an integration.
        
        Returns:
            URL string to redirect user to for OAuth flow
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/integrations/{integration_id}/auth-url"
            )
            response.raise_for_status()
            return response.json()['url']
        except Exception as e:
            logger.error(f"Failed to get auth URL for {integration_id}: {e}")
            raise
    
    async def disconnect_integration(self, integration_id: str) -> None:
        """Disconnect an integration"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/integrations/{integration_id}/disconnect"
            )
            response.raise_for_status()
            logger.info(f"Disconnected integration: {integration_id}")
        except Exception as e:
            logger.error(f"Failed to disconnect {integration_id}: {e}")
            raise
    
    # ========================================================================
    # SYSTEM API
    # ========================================================================
    
    async def get_system_info(self) -> Dict:
        """
        Get system information.
        
        Returns:
            {
                "device_name": str,
                "firmware_version": str,
                "ip_address": str,
                "wifi_ssid": str,
                "wifi_signal": int,
                "storage_used": int (bytes),
                "storage_total": int (bytes),
                "uptime": int (seconds),
                "meetings_count": int
            }
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/system/info")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch system info: {e}")
            raise
    
    async def check_for_updates(self) -> Dict:
        """
        Check for firmware updates.
        
        Returns:
            {
                "update_available": bool,
                "current_version": str,
                "latest_version": str | None,
                "release_notes": str | None
            }
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/system/check-updates"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to check for updates: {e}")
            raise
    
    async def install_update(self) -> Dict:
        """Trigger firmware update installation"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/system/install-update"
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to install update: {e}")
            raise
    
    # ========================================================================
    # WIFI API
    # ========================================================================
    
    async def get_wifi_networks(self) -> List[Dict]:
        """
        Get list of available WiFi networks.
        
        Returns:
            [
                {
                    "ssid": str,
                    "signal_strength": int (0-100),
                    "security": str ("open" | "wpa" | "wpa2"),
                    "connected": bool
                },
                ...
            ]
        """
        try:
            response = await self.client.get(f"{self.base_url}/api/wifi/scan")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to scan WiFi networks: {e}")
            raise
    
    async def connect_wifi(self, ssid: str, password: str = None) -> Dict:
        """
        Connect to a WiFi network.
        
        Args:
            ssid: Network SSID
            password: Network password (None for open networks)
        
        Returns:
            {
                "status": "connected" | "failed",
                "message": str
            }
        """
        try:
            response = await self.client.post(
                f"{self.base_url}/api/wifi/connect",
                json={"ssid": ssid, "password": password}
            )
            response.raise_for_status()
            logger.info(f"Connected to WiFi: {ssid}")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to connect to WiFi {ssid}: {e}")
            raise
    
    async def disconnect_wifi(self) -> None:
        """Disconnect from current WiFi network"""
        try:
            response = await self.client.post(f"{self.base_url}/api/wifi/disconnect")
            response.raise_for_status()
            logger.info("Disconnected from WiFi")
        except Exception as e:
            logger.error(f"Failed to disconnect WiFi: {e}")
            raise
    
    # ========================================================================
    # WEBSOCKET (Real-time events)
    # ========================================================================
    
    async def subscribe_events(self) -> AsyncIterator[Dict]:
        """
        Subscribe to real-time events from backend via WebSocket.
        
        Yields event dictionaries:
            {
                "type": "recording_started" | "recording_stopped" | 
                        "transcription_update" | "processing_complete" | ...,
                "data": { ... }
            }
        
        Automatically reconnects on connection loss.
        """
        while True:
            try:
                async with websockets.connect(self.ws_url) as websocket:
                    logger.info("WebSocket connected")
                    self._ws_reconnect_attempts = 0
                    self.ws_connection = websocket
                    
                    async for message in websocket:
                        try:
                            event = json.loads(message)
                            yield event
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse WebSocket message: {e}")
                            continue
                            
            except ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                self.ws_connection = None
                await self._handle_ws_reconnect()
                
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.ws_connection = None
                await self._handle_ws_reconnect()
    
    async def _handle_ws_reconnect(self):
        """Handle WebSocket reconnection with exponential backoff"""
        self._ws_reconnect_attempts += 1
        
        if self._ws_reconnect_attempts > WS_MAX_RECONNECT_ATTEMPTS:
            logger.error("Max WebSocket reconnection attempts reached")
            raise ConnectionError("Failed to reconnect to backend WebSocket")
        
        delay = min(WS_RECONNECT_DELAY * (2 ** self._ws_reconnect_attempts), 60)
        logger.info(f"Reconnecting WebSocket in {delay}s (attempt {self._ws_reconnect_attempts})")
        await asyncio.sleep(delay)
    
    # ========================================================================
    # HEALTH CHECK
    # ========================================================================
    
    async def health_check(self) -> bool:
        """
        Check if backend is reachable and healthy.
        
        Returns:
            True if backend is healthy, False otherwise
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/api/health",
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
