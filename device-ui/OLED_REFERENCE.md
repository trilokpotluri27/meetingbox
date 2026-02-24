# OLED Device UI -- Diagnostic Reference

## Overview

The MeetingBox device UI is a **Kivy 2.3+** touchscreen application running on a Raspberry Pi 5 with a 3.5" OLED display (480x320, landscape). It communicates with the FastAPI backend (`services/web/`) over HTTP REST and WebSocket.

## Architecture

```
Device UI (Kivy)  --HTTP-->  FastAPI backend (port 8000)  --Redis-->  Audio/Transcription/AI services
                  <--WS---   WebSocket relay (/ws)        <--Redis--
```

- **Rendering**: Kivy + SDL2 over X11 (not low-level I2C/SPI OLED driver)
- **Backend URL**: `http://web:8000` (Docker) or `http://localhost:8000` (dev)
- **WebSocket URL**: `ws://web:8000/ws`
- **Auth**: Device UI sends NO JWT token. All backend routes it calls must use `get_optional_user`.

## Key Files

### Device UI (`device-ui/src/`)

| File | Purpose |
|---|---|
| `main.py` | Kivy app entry, screen manager, WebSocket listener, recording actions |
| `config.py` | Colors, fonts, sizes, backend URLs, display settings |
| `api_client.py` | Async HTTP client (`httpx`) for backend API |
| `async_helper.py` | Bridges Kivy main thread with asyncio event loop |
| `mock_backend.py` | Mock backend for dev/testing |
| `screens/base_screen.py` | Base class: dark bg, navigation, footer |
| `screens/home.py` | Ready state, START RECORDING button |
| `screens/recording.py` | Timer, waveform, captions, PAUSE/STOP buttons |
| `screens/processing.py` | Progress bar during transcription/summary |
| `screens/complete.py` | Meeting saved confirmation, auto-return to home |
| `screens/summary_review.py` | Summary + Actions tabs, Execute Selected button |
| `screens/settings.py` | Scrollable settings list (privacy, brightness, restart, etc.) |
| `screens/picker_base.py` | Base for radio-button pickers |
| `screens/brightness_picker.py` | Screen brightness picker |
| `screens/timeout_picker.py` | Screen timeout picker |
| `screens/auto_delete_picker.py` | Auto-delete old meetings picker |
| `screens/wifi_setup.py` | First-boot WiFi setup (QR code + instructions) |
| `screens/wifi.py` | WiFi network list |
| `screens/meetings.py` | Past meetings list |
| `screens/meeting_detail.py` | Single meeting detail |
| `screens/mic_test.py` | Microphone test waveform |
| `screens/update_check.py` | Check for firmware updates |
| `screens/update_install.py` | Install firmware update |
| `screens/error.py` | Error display with recovery action |
| `components/button.py` | PrimaryButton, SecondaryButton, DangerButton |
| `components/status_bar.py` | Top bar with status dot, device name, gear icon |
| `components/settings_item.py` | Settings row (arrow / toggle / info modes) |
| `components/modal_dialog.py` | Centered modal dialog with confirm/cancel |
| `components/toggle_switch.py` | iOS-style toggle switch |

### Backend Routes (`services/web/routes/`)

| File | Prefix | Purpose |
|---|---|---|
| `meetings.py` | `/api/meetings` | Recording control, meeting CRUD, summarization |
| `device.py` | `/api/device` | Settings, WiFi, updates, integrations |
| `system.py` | `/api/system` | System status, device-info (no auth) |
| `actions.py` | `/api` | Action items CRUD + execution |
| `auth.py` | `/api/auth` | User registration, login, JWT |
| `integrations.py` | `/api` | Google OAuth device flow |

### Other Key Files

| File | Purpose |
|---|---|
| `services/web/main.py` | FastAPI app, WebSocket endpoint, Redis event relay |
| `services/web/auth.py` | JWT auth: `get_current_user` (401) vs `get_optional_user` (None) |
| `services/web/database.py` | SQLite schema (meetings, segments, summaries, users, actions, integrations) |
| `docker-compose.yml` | Service orchestration (redis, audio, transcription, ai, web, device-ui) |

## Screen Flow

```
Splash -> Welcome -> WiFi Setup -> Setup Progress -> All Set -> Home
Home -> Recording -> Processing -> Summary Review -> Home
Home -> Settings -> Brightness/Timeout/AutoDelete Pickers
Home -> Settings -> Mic Test / Update Check / WiFi
Home -> Meetings -> Meeting Detail
```

## Button-to-API Mapping

### Home Screen (`home.py`)
| Button | Handler | API Call | Auth |
|---|---|---|---|
| START RECORDING | `_on_start_recording()` -> `app.start_recording()` | `POST /api/meetings/start` | optional |
| Gear icon (status bar) | `_on_gear_pressed()` | Navigation only | N/A |
| On enter: load last meeting | `_load_last_meeting()` | `GET /api/meetings/?limit=1` | optional |
| On enter: load system status | `_load_system_status()` | `GET /api/system/device-info` | none |

### Recording Screen (`recording.py`)
| Button | Handler | API Call | Auth |
|---|---|---|---|
| PAUSE / RESUME | `_on_pause()` -> `app.pause_recording()` / `app.resume_recording()` | `POST /api/meetings/pause` or `/resume` | optional |
| STOP | `_on_stop()` -> modal -> `_do_stop()` -> `app.stop_recording()` | `POST /api/meetings/stop` | optional |

### Settings Screen (`settings.py`)
| Button | Handler | API Call | Auth |
|---|---|---|---|
| Privacy toggle | `_on_privacy_toggled()` | `PATCH /api/device/settings` | optional |
| Brightness -> picker | Navigation | `PATCH /api/device/settings` (in picker) | optional |
| Timeout -> picker | Navigation | `PATCH /api/device/settings` (in picker) | optional |
| Auto-delete -> picker | Navigation | `PATCH /api/device/settings` (in picker) | optional |
| Restart | `_show_restart_dialog()` -> `_do_restart()` | `PATCH /api/device/settings` (action: restart) | optional |
| Factory Reset | `_show_factory_reset_dialog()` -> `_execute_factory_reset()` | `PATCH /api/device/settings` (action: factory_reset) | optional |
| Back button | `go_back()` | Navigation only | N/A |
| On enter: load info | `_load_system_info()` | `GET /api/system/device-info` | none |

### Summary Review Screen (`summary_review.py`)
| Button | Handler | API Call | Auth |
|---|---|---|---|
| Close | `_on_close()` | Navigation only | N/A |
| Execute Selected | `_on_execute()` | `POST /api/actions/{id}/execute` (per selected) | optional |
| On load: fetch actions | `_load_actions()` | `GET /api/meetings/{id}/actions` | optional |

### Update Check Screen (`update_check.py`)
| Button | Handler | API Call | Auth |
|---|---|---|---|
| INSTALL UPDATE | `_on_install()` | Navigation to update_install | N/A |
| On enter: check | `_check_updates()` | `GET /api/device/check-updates` | optional |

## Authentication Design

The device-ui has NO user login. It calls the backend without JWT tokens.

- `get_optional_user` (in `auth.py`): Returns `None` if no token -- **safe for device-ui**
- `get_current_user` (in `auth.py`): Raises 401 if no token -- **breaks device-ui**

All routes called by the device-ui must use `get_optional_user`.

Routes that are NOT called by the device-ui (e.g., auth routes, upload-audio) can safely require `get_current_user`.

## Known Issues / History

### 2026-02-24: Auth-Blocked Button Responses (FIXED)
**Problem**: Most backend routes required JWT auth (`get_current_user`), but the device-ui sends no token. Only recording start/stop/pause/resume worked (they used `get_optional_user`). Everything else failed silently with 401.

**Fix**: Changed all device-facing routes in `device.py`, `meetings.py`, and `actions.py` to use `get_optional_user` instead of `get_current_user`.

**Files changed**:
- `services/web/routes/device.py` -- all endpoints to `get_optional_user`
- `services/web/routes/meetings.py` -- list, detail, delete, summarize endpoints
- `services/web/routes/actions.py` -- list, update, approve, dismiss, execute endpoints

## Error Handling Pattern

The device-ui swallows most API errors silently:
```python
except Exception:
    pass  # or logger.error(...)
```
This means failed API calls don't show any user-visible feedback. The UI just doesn't update. If debugging, always check backend logs for 401/500 errors.

## WebSocket Events

The device-ui subscribes to `ws://web:8000/ws` and dispatches these event types:

| Event Type | Handler | Effect |
|---|---|---|
| `recording_started` | `on_recording_started()` | Navigate to recording screen |
| `recording_stopped` | `on_recording_stopped()` | Navigate to processing screen |
| `recording_paused` | `on_recording_paused()` | Update recording screen to paused |
| `recording_resumed` | `on_recording_resumed()` | Resume recording screen |
| `transcription_update` | `on_transcription_update()` | Update live captions |
| `processing_started` | `on_processing_started()` | Show meeting info on processing screen |
| `processing_progress` | `on_processing_progress()` | Update progress bar |
| `processing_complete` | `on_processing_complete()` | Trigger auto-summarize |
| `summary_complete` | `on_summary_complete()` | Show summary review screen |
| `setup_complete` | `on_setup_complete()` | Advance from onboarding to all_set |
| `update_progress` | `on_update_progress()` | Update firmware install progress |
| `error` | `on_error_event()` | Show error screen |
