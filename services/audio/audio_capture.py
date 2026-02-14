import json
import os
import time
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import pyaudio
import redis
import webrtcvad
import yaml


class AudioCaptureService:
  """
  Capture audio from the USB mic array, segment it using VAD, and
  publish segment metadata + recording lifecycle events via Redis.
  """

  def __init__(self, config_path: str = "config.yaml") -> None:
    with open(config_path, "r") as f:
      self.config = yaml.safe_load(f)

    self.RATE = self.config["audio"]["sample_rate"]
    self.CHANNELS = self.config["audio"]["channels"]
    self.CHUNK = self.config["audio"]["chunk_size"]
    self.FORMAT = pyaudio.paInt16

    self.is_recording = False
    self.current_session_id: str | None = None
    self._recording_thread: object | None = None  # threading.Thread

    self.vad = webrtcvad.Vad(self.config["vad"]["aggressiveness"])

    self.redis_client = redis.Redis(host="redis", port=6379, decode_responses=True)

    storage_cfg = self.config.get("storage", {})
    self.temp_dir = Path(storage_cfg.get("temp_dir", "/data/audio/temp"))
    self.recordings_dir = Path(storage_cfg.get("recordings_dir", "/data/audio/recordings"))

    self.audio = pyaudio.PyAudio()
    self.stream: pyaudio.Stream | None = None

    print(f"[AudioCapture] Initialized - {self.RATE}Hz, {self.CHANNELS}ch")

  # --- Device handling -------------------------------------------------

  def find_mic_device(self) -> int | None:
    """Attempt to locate the ReSpeaker (or other USB mic) by name."""
    info = self.audio.get_host_api_info_by_index(0)
    num_devices = info.get("deviceCount", 0)

    for i in range(num_devices):
      device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
      name = device_info.get("name", "")
      if ("ReSpeaker" in name or "UAC" in name) and device_info.get("maxInputChannels", 0) > 0:
        print(f"[AudioCapture] Using input device {i}: {name}")
        return i

    print("[AudioCapture] ReSpeaker not found, using default input")
    return None

  # --- Recording lifecycle ---------------------------------------------

  def start_recording(self, session_id: str | None = None) -> bool:
    if self.is_recording:
      print("[AudioCapture] Already recording")
      return False

    if session_id is None:
      session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    self.current_session_id = session_id
    self.is_recording = True

    session_temp = self.temp_dir / session_id
    session_temp.mkdir(parents=True, exist_ok=True)

    mic_index = self.find_mic_device()
    self.stream = self.audio.open(
      format=self.FORMAT,
      channels=self.CHANNELS,
      rate=self.RATE,
      input=True,
      input_device_index=mic_index,
      frames_per_buffer=self.CHUNK,
    )

    self.redis_client.publish(
      "events",
      json.dumps(
        {
          "type": "recording_started",
          "session_id": session_id,
          "timestamp": datetime.now().isoformat(),
        }
      ),
    )

    # let hardware service know (stubbed for now)
    self.redis_client.publish(
      "hardware_commands",
      json.dumps(
        {
          "action": "update_display",
          "state": "recording",
          "session_id": session_id,
        }
      ),
    )

    print(f"[AudioCapture] Recording started - session {session_id}")
    return True

  def stop_recording(self, session_id_from_command: str | None = None) -> str | None:
    if not self.is_recording:
      print("[AudioCapture] Not recording")
      # Still publish so downstream can set recording_state back to idle
      sid = session_id_from_command or self.current_session_id
      self.redis_client.publish(
        "events",
        json.dumps(
          {
            "type": "recording_stopped",
            "session_id": sid,
            "path": None,
            "timestamp": datetime.now().isoformat(),
          }
        ),
      )
      return None

    print(f"[AudioCapture] Stopping recording - session {self.current_session_id}")
    self.is_recording = False

    # Wait for the recording thread to finish reading before closing the stream.
    # Without this, stream.close() races with stream.read() in the thread,
    # causing a segfault in the native ALSA/PortAudio code.
    if self._recording_thread is not None:
      import threading
      if isinstance(self._recording_thread, threading.Thread) and self._recording_thread.is_alive():
        print("[AudioCapture] Waiting for recording thread to finish...")
        self._recording_thread.join(timeout=5.0)
      self._recording_thread = None

    if self.stream:
      self.stream.stop_stream()
      self.stream.close()
      self.stream = None

    final_path = self.combine_segments()

    self.redis_client.publish(
      "events",
      json.dumps(
        {
          "type": "recording_stopped",
          "session_id": self.current_session_id,
          "path": str(final_path) if final_path else None,
          "timestamp": datetime.now().isoformat(),
        }
      ),
    )

    # update hardware state
    self.redis_client.publish(
      "hardware_commands",
      json.dumps(
        {
          "action": "update_display",
          "state": "processing",
          "session_id": self.current_session_id,
        }
      ),
    )

    session_id = self.current_session_id
    self.current_session_id = None
    return session_id

  # --- Segmentation helpers -------------------------------------------

  def process_audio_chunk(self, chunk: bytes) -> bool:
    """Return True if this chunk likely contains speech."""
    return self.vad.is_speech(chunk, self.RATE)

  def save_audio_segment(self, frames: list[bytes], segment_num: int) -> Path:
    assert self.current_session_id is not None
    session_dir = self.temp_dir / self.current_session_id
    segment_path = session_dir / f"segment_{segment_num:04d}.wav"

    audio_bytes = b"".join(frames)
    segment_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(segment_path), "wb") as wf:
      wf.setnchannels(self.CHANNELS)
      wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
      wf.setframerate(self.RATE)
      wf.writeframes(audio_bytes)

    self.redis_client.publish(
      "audio_segments",
      json.dumps(
        {
          "session_id": self.current_session_id,
          "segment_num": segment_num,
          "path": str(segment_path),
          "timestamp": time.time(),
        }
      ),
    )

    return segment_path

  def recording_loop(self) -> None:
    """
    Blocking loop that reads from the input stream, applies VAD, and
    saves segments when either:
    - a maximum number of chunks is reached, or
    - sufficient audio followed by a pause is detected.
    """
    segment_num = 0
    current_frames: list[bytes] = []
    silence_chunks = 0

    MIN_SEGMENT_CHUNKS = 50
    MAX_SEGMENT_CHUNKS = 500
    SILENCE_THRESHOLD = 10

    try:
      while self.is_recording:
        assert self.stream is not None
        chunk = self.stream.read(self.CHUNK, exception_on_overflow=False)
        is_speech = self.process_audio_chunk(chunk)

        current_frames.append(chunk)

        if is_speech:
          silence_chunks = 0
        else:
          silence_chunks += 1

        should_save = False
        if len(current_frames) >= MAX_SEGMENT_CHUNKS:
          should_save = True
        elif len(current_frames) >= MIN_SEGMENT_CHUNKS and silence_chunks >= SILENCE_THRESHOLD:
          should_save = True

        if should_save and current_frames:
          self.save_audio_segment(current_frames, segment_num)
          print(f"[AudioCapture] Saved segment {segment_num} ({len(current_frames)} chunks)")
          segment_num += 1
          current_frames = []
          silence_chunks = 0

    except Exception as exc:
      print(f"[AudioCapture] Error in recording loop: {exc}")

    finally:
      if current_frames:
        self.save_audio_segment(current_frames, segment_num)

  def combine_segments(self) -> Path | None:
    """Merge all segment WAVs into a single recording file."""
    if self.current_session_id is None:
      return None

    session_dir = self.temp_dir / self.current_session_id
    segment_files = sorted(session_dir.glob("segment_*.wav"))

    if not segment_files:
      print("[AudioCapture] No segments to combine")
      return None

    output_path = self.recordings_dir / f"{self.current_session_id}.wav"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(output_path), "wb") as out_wav:
      with wave.open(str(segment_files[0]), "rb") as first:
        out_wav.setparams(first.getparams())

      for seg in segment_files:
        with wave.open(str(seg), "rb") as src:
          out_wav.writeframes(src.readframes(src.getnframes()))

    for seg in segment_files:
      seg.unlink()
    try:
      session_dir.rmdir()
    except OSError:
      pass

    print(f"[AudioCapture] Combined {len(segment_files)} segments -> {output_path}")
    return output_path

  # --- Command listener -----------------------------------------------

  def run(self) -> None:
    """Listen for start/stop commands over Redis and manage recording."""
    print("[AudioCapture] Service started, waiting for commands...")
    pubsub = self.redis_client.pubsub()
    pubsub.subscribe("commands")

    for message in pubsub.listen():
      if message["type"] != "message":
        continue
      try:
        command = json.loads(message["data"])
      except json.JSONDecodeError:
        print(f"[AudioCapture] Invalid command payload: {message['data']}")
        continue

      action = command.get("action")
      if action == "start_recording":
        session_id = command.get("session_id")
        if self.start_recording(session_id):
          import threading

          thread = threading.Thread(target=self.recording_loop, daemon=True)
          thread.start()
          self._recording_thread = thread
      elif action == "stop_recording":
        self.stop_recording(session_id_from_command=command.get("session_id"))


if __name__ == "__main__":
  service = AudioCaptureService()
  service.run()

