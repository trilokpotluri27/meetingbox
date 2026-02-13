import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

interface Meeting {
  id: string;
  title: string;
  start_time: string;
  end_time: string | null;
  status: string;
  created_at: string;
}

type RecordingState = "idle" | "recording" | "processing";
type MicState = "idle" | "recording" | "uploading";

// Browser live speech-to-text (Chrome/Edge); not available in all browsers
interface SpeechResultEvent {
  results: Array<Array<{ transcript: string }>>;
}
function createSpeechRecognition(): {
  start: (onTranscript: (text: string) => void) => void;
  stop: () => void;
} | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as { SpeechRecognition?: unknown; webkitSpeechRecognition?: unknown };
  const API = (w.SpeechRecognition || w.webkitSpeechRecognition) as (new () => {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start: () => void;
    stop: () => void;
    onresult: ((e: SpeechResultEvent) => void) | null;
  }) | undefined;
  if (!API) return null;
  const rec = new API();
  rec.continuous = true;
  rec.interimResults = true;
  rec.lang = "en-US";
  return {
    start: (onTranscript) => {
      rec.onresult = (e: SpeechResultEvent) => {
        const last = e.results.length - 1;
        const item = e.results[last]?.[0];
        if (item?.transcript) onTranscript(item.transcript);
      };
      rec.start();
    },
    stop: () => rec.stop(),
  };
}

const Dashboard: React.FC = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [recordingState, setRecordingState] = useState<RecordingState>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [startStopLoading, setStartStopLoading] = useState(false);
  const [micState, setMicState] = useState<MicState>("idle");
  const [micError, setMicError] = useState<string | null>(null);
  const [backendReachable, setBackendReachable] = useState<boolean | null>(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [liveTranscriptSupported, setLiveTranscriptSupported] = useState<boolean | null>(null);
  const mediaRecorderRef = React.useRef<MediaRecorder | null>(null);
  const streamRef = React.useRef<MediaStream | null>(null);
  const chunksRef = React.useRef<Blob[]>([]);
  const speechRecognitionRef = React.useRef<ReturnType<typeof createSpeechRecognition>>(null);

  const loadMeetings = async () => {
    try {
      const res = await axios.get<Meeting[]>("/api/meetings/");
      setMeetings(res.data);
      setBackendReachable(true);
    } catch (err) {
      console.error("Failed to load meetings", err);
      setBackendReachable(false);
    } finally {
      setLoading(false);
    }
  };

  const loadRecordingStatus = async () => {
    try {
      const res = await axios.get<{ state: RecordingState; session_id: string | null }>(
        "/api/meetings/recording-status"
      );
      setRecordingState(res.data.state as RecordingState);
      setSessionId(res.data.session_id ?? null);
      setBackendReachable(true);
    } catch {
      setRecordingState("idle");
      setBackendReachable(false);
    }
  };

  useEffect(() => {
    loadMeetings();
    loadRecordingStatus();
    const t = setInterval(() => {
      loadRecordingStatus();
      if (recordingState === "processing") loadMeetings();
    }, 2000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (recordingState === "processing") loadMeetings();
  }, [recordingState]);

  const startMeeting = async () => {
    setStartStopLoading(true);
    try {
      await axios.post("/api/meetings/start");
      await loadRecordingStatus();
    } catch (err) {
      console.error("Start meeting failed", err);
    } finally {
      setStartStopLoading(false);
    }
  };

  const stopMeeting = async () => {
    setStartStopLoading(true);
    try {
      await axios.post("/api/meetings/stop");
      await loadRecordingStatus();
      setTimeout(loadMeetings, 1000);
    } catch (err) {
      console.error("Stop meeting failed", err);
    } finally {
      setStartStopLoading(false);
    }
  };

  const startMicRecording = async () => {
    setMicError(null);
    setLiveTranscript("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.start(200);
      setMicState("recording");

      const sr = createSpeechRecognition();
      speechRecognitionRef.current = sr;
      setLiveTranscriptSupported(!!sr);
      if (sr) {
        sr.start((text) => {
          setLiveTranscript((prev) => (prev ? `${prev} ${text}` : text));
        });
      }
    } catch (err) {
      setMicError(err instanceof Error ? err.message : "Could not access microphone");
    }
  };

  const stopMicRecording = async () => {
    const recorder = mediaRecorderRef.current;
    const stream = streamRef.current;
    const sr = speechRecognitionRef.current;
    if (!recorder || recorder.state === "inactive") {
      setMicState("idle");
      return;
    }
    try {
      sr?.stop();
    } catch {
      // ignore if already stopped
    }
    speechRecognitionRef.current = null;
    recorder.stop();
    stream?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    mediaRecorderRef.current = null;

    return new Promise<void>((resolve) => {
      recorder.onstop = async () => {
        setMicState("uploading");
        try {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" });
          const form = new FormData();
          form.append("file", blob, "recording.webm");
          await axios.post("/api/meetings/upload-audio", form, {
            headers: { "Content-Type": "multipart/form-data" },
          });
          setMicError(null);
          await loadRecordingStatus();
          await loadMeetings();
        } catch (err) {
          console.error("Upload failed", err);
          setMicError("Upload failed. Try again.");
        } finally {
          setMicState("idle");
          resolve();
        }
      };
    });
  };

  if (loading) {
    return <div className="text-gray-600">Loading meetings…</div>;
  }

  return (
    <div className="space-y-4">
      {backendReachable === false && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-800">
          <strong>Backend not reachable.</strong> Start the API so recording and upload work: run{" "}
          <code className="bg-amber-100 px-1 rounded">docker compose up</code> in the project root, then refresh.
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h2 className="text-lg font-semibold text-gray-900">Recent meetings</h2>
        <div className="flex flex-wrap items-center gap-2">
          {recordingState === "idle" && micState === "idle" && (
            <>
              <button
                type="button"
                onClick={startMeeting}
                disabled={startStopLoading}
                title="Uses appliance/device mic (in Docker, no mic is available)"
                className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50"
              >
                Start meeting
              </button>
              <button
                type="button"
                onClick={startMicRecording}
                disabled={startStopLoading}
                title="Use this computer's microphone — recommended for testing"
                className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                Record with my mic
              </button>
            </>
          )}
          {micState === "recording" && (
            <button
              type="button"
              onClick={stopMicRecording}
              className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700"
            >
              Stop & send
            </button>
          )}
          {micState === "uploading" && (
            <span className="text-sm text-gray-500">Uploading…</span>
          )}
          {recordingState === "recording" && (
            <button
              type="button"
              onClick={stopMeeting}
              disabled={startStopLoading}
              className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50"
            >
              Stop & process
            </button>
          )}
          {(recordingState === "recording" || recordingState === "processing") && (
            <>
              <span className="text-sm text-gray-500">
                {recordingState === "recording" && "Recording…"}
                {recordingState === "processing" && "Processing…"}
                {sessionId && ` (${sessionId})`}
              </span>
              {recordingState === "processing" && (
                <button
                  type="button"
                  onClick={async () => {
                    try {
                      await axios.post("/api/meetings/reset-recording-state");
                      await loadRecordingStatus();
                    } catch (e) {
                      console.error("Reset failed", e);
                    }
                  }}
                  className="text-sm text-blue-600 hover:underline"
                >
                  Stuck? Reset
                </button>
              )}
            </>
          )}
          {micError && (
            <span className="text-sm text-red-600">{micError}</span>
          )}
        </div>
      </div>

      {(micState === "recording" || micState === "uploading") && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="text-sm font-semibold text-gray-700 mb-2">
            {micState === "recording" ? "Live transcript (you should see words as you speak)" : "Uploading…"}
          </div>
          <div className="min-h-[4rem] max-h-48 overflow-y-auto text-sm text-gray-800 bg-gray-50 rounded p-3">
            {liveTranscript || (
              <span className="text-gray-400">
                {liveTranscriptSupported === false
                  ? "Live captions not supported in this browser (Chrome/Edge recommended). Recording is still saving."
                  : "Speak now…"}
              </span>
            )}
          </div>
        </div>
      )}

      {!meetings.length ? (
        <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-600">
          <p className="mb-2">No meetings recorded yet.</p>
          <p className="text-sm text-gray-500 mb-4">
            Use <strong>&quot;Record with my mic&quot;</strong> to capture from this computer (recommended). &quot;Start meeting&quot; uses the appliance mic and does not work in Docker on Windows.
          </p>
          <code className="block text-left bg-gray-100 p-3 rounded text-xs overflow-x-auto">
            python scripts/ingest_test_wav.py path/to/audio.wav
          </code>
        </div>
      ) : (
        <div className="bg-white shadow-sm rounded-lg divide-y divide-gray-100">
          {meetings.map((m) => (
            <Link
              key={m.id}
              to={`/meeting/${m.id}`}
              className="flex justify-between items-center px-4 py-3 hover:bg-gray-50"
            >
              <div>
                <div className="text-sm font-medium text-gray-900">{m.title}</div>
                <div className="text-xs text-gray-500">
                  Started {new Date(m.start_time).toLocaleString()}
                </div>
              </div>
              <span className="text-xs uppercase tracking-wide text-gray-500">{m.status}</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
};

export default Dashboard;
