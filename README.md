MeetingBox Core Software MVP
============================

This repository contains the core software stack for **MeetingBox**, a conference-room AI appliance that:

- Captures in-room audio
- Transcribes meetings with Whisper
- Generates AI summaries with Claude
- Serves a local web dashboard at `meetingbox.local`

This MVP focuses on a **single-device pipeline** (no external calendar/email/Slack integrations yet):

1. Start/stop a meeting recording
2. Capture audio from a USB mic array
3. Transcribe audio to text on-device
4. Generate an AI summary + action items
5. Store everything in SQLite
6. View meetings and summaries in a React dashboard

## Repository layout

- `services/audio` – Audio capture & VAD-based segmentation (PyAudio + webrtcvad)
- `services/transcription` – Whisper.cpp-based transcription service writing into SQLite
- `services/ai` – Claude integration for summaries + analysis
- `services/web` – FastAPI backend + WebSocket relay for events
- `frontend` – React + TypeScript + Tailwind dashboard
- `data` – Local data volume (audio, transcripts, exports, SQLite DB)
- `logs` – Service logs (optional, per-service)
- `scripts` – Helper scripts for setup and deployment
- `docker-compose.yml` – Local development / on-device orchestration
- `.env.example` – Example environment variables (API keys, config)

## Getting started (development)

1. Install Docker and Docker Compose.
2. Copy `.env.example` to `.env` and fill in secrets (e.g. `ANTHROPIC_API_KEY`).
3. Run:

```bash
docker compose up --build
```

4. Open `http://localhost:8000` (or `http://meetingbox.local:8000` on-device) to access the dashboard.

## On-device (Raspberry Pi 5) deployment

The `scripts/` directory will contain reproducible setup instructions for:

- Flashing Ubuntu Server 24.04 to NVMe
- Installing Docker & Docker Compose
- Configuring audio (ALSA/PulseAudio, ReSpeaker as default input)
- Enabling mDNS for `meetingbox.local`

Once the device is prepared, copy this repo to `/opt/meetingbox` and run:

```bash
cd /opt/meetingbox
docker compose -f docker-compose.prod.yml up -d
```

Details will be fleshed out as the services are implemented.

