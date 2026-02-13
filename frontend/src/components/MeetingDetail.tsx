import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import axios from "axios";

interface Segment {
  segment_num: number;
  start_time: number;
  end_time: number;
  text: string;
}

interface Meeting {
  id: string;
  title: string;
  start_time: string;
  end_time: string | null;
  status: string;
}

interface Summary {
  summary: string;
  action_items: { task: string; assignee?: string; due_date?: string }[];
  decisions: string[];
  topics: string[];
  sentiment: string;
}

interface LocalSummary extends Summary {
  model_name: string;
}

interface MeetingDetailResponse {
  meeting: Meeting;
  segments: Segment[];
  summary: Summary | null;
  local_summary: LocalSummary | null;
}

const MeetingDetail: React.FC = () => {
  const { id } = useParams();
  const [data, setData] = useState<MeetingDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [summarizing, setSummarizing] = useState(false);
  const [summarizeError, setSummarizeError] = useState<string | null>(null);
  const [summarizingLocal, setSummarizingLocal] = useState(false);
  const [summarizeLocalError, setSummarizeLocalError] = useState<string | null>(null);

  const loadMeeting = async () => {
    try {
      const res = await axios.get<MeetingDetailResponse>(`/api/meetings/${id}`);
      setData(res.data);
    } catch (err) {
      console.error("Failed to load meeting", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      loadMeeting();
    }
  }, [id]);

  const handleSummarize = async () => {
    if (!id) return;
    setSummarizing(true);
    setSummarizeError(null);
    try {
      await axios.post(`/api/meetings/${id}/summarize`);
      await loadMeeting();
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Summarization failed. Check API key.";
      setSummarizeError(msg);
    } finally {
      setSummarizing(false);
    }
  };

  const handleSummarizeLocal = async () => {
    if (!id) return;
    setSummarizingLocal(true);
    setSummarizeLocalError(null);
    try {
      await axios.post(`/api/meetings/${id}/summarize-local`);
      await loadMeeting();
    } catch (err: unknown) {
      const msg =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? err.response.data.detail
          : "Local summarization failed. Is Ollama running with a model pulled?";
      setSummarizeLocalError(msg);
    } finally {
      setSummarizingLocal(false);
    }
  };

  if (loading) {
    return <div className="text-gray-600">Loading meeting…</div>;
  }

  if (!data) {
    return (
      <div className="text-gray-600">
        Meeting not found. <Link to="/" className="text-blue-600">Back to dashboard</Link>
      </div>
    );
  }

  const { meeting, segments, summary, local_summary } = data;

  const renderSummaryCard = (
    s: Summary | LocalSummary,
    label: string,
    colorClass: string,
    badgeBg: string,
  ) => (
    <div className="bg-white shadow-sm rounded-lg p-4 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="text-sm font-semibold text-gray-900">{label}</div>
          {"model_name" in s && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 text-gray-500">
              {(s as LocalSummary).model_name}
            </span>
          )}
        </div>
        {s.sentiment && (
          <span className={`text-xs px-2 py-0.5 rounded-full ${badgeBg}`}>
            {s.sentiment}
          </span>
        )}
      </div>
      <p className="text-sm text-gray-800">{s.summary}</p>
      {s.decisions.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase mt-2">
            Decisions
          </div>
          <ul className="list-disc list-inside text-sm text-gray-800">
            {s.decisions.map((d, idx) => (
              <li key={idx}>{d}</li>
            ))}
          </ul>
        </div>
      )}
      {s.action_items.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-500 uppercase mt-2">
            Action items
          </div>
          <ul className="list-disc list-inside text-sm text-gray-800">
            {s.action_items.map((a, idx) => (
              <li key={idx}>
                {a.task}
                {a.assignee && ` – ${a.assignee}`}
              </li>
            ))}
          </ul>
        </div>
      )}
      {s.topics.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {s.topics.map((t, idx) => (
            <span
              key={idx}
              className={`px-2 py-0.5 text-xs rounded-full ${colorClass}`}
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">{meeting.title}</h2>
        <Link to="/" className="text-sm text-blue-600">
          Back
        </Link>
      </div>

      {/* Summarize buttons — show when transcript exists */}
      {segments.length > 0 && (!summary || !local_summary) && (
        <div className="bg-white shadow-sm rounded-lg p-4">
          <div className="flex flex-wrap items-start gap-3">
            {!summary && (
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  onClick={handleSummarize}
                  disabled={summarizing}
                  className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  {summarizing ? "Summarizing…" : "Summarize with API"}
                </button>
                <span className="text-xs text-gray-500">Claude API</span>
                {summarizeError && (
                  <span className="text-sm text-red-600">{summarizeError}</span>
                )}
              </div>
            )}
            {!local_summary && (
              <div className="flex flex-col gap-1">
                <button
                  type="button"
                  onClick={handleSummarizeLocal}
                  disabled={summarizingLocal}
                  className="px-4 py-2 bg-emerald-600 text-white text-sm font-medium rounded-lg hover:bg-emerald-700 disabled:opacity-50"
                >
                  {summarizingLocal ? "Summarizing…" : "Summarize Locally"}
                </button>
                <span className="text-xs text-gray-500">Local LLM (Ollama)</span>
                {summarizeLocalError && (
                  <span className="text-sm text-red-600">{summarizeLocalError}</span>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* No transcript yet */}
      {segments.length === 0 && !summary && !local_summary && (
        <div className="bg-white shadow-sm rounded-lg p-4">
          <div className="text-sm text-gray-500">
            No transcript yet — summary will be available after transcription.
          </div>
        </div>
      )}

      {/* API Summary */}
      {summary && renderSummaryCard(summary, "API Summary (Claude)", "bg-gray-100 text-gray-700", "bg-blue-50 text-blue-700")}

      {/* Local Summary */}
      {local_summary && renderSummaryCard(local_summary, "Local Summary", "bg-emerald-50 text-emerald-700", "bg-emerald-50 text-emerald-700")}

      <div className="bg-white shadow-sm rounded-lg p-4">
        <div className="text-sm font-semibold text-gray-900 mb-2">Transcript</div>
        <div className="space-y-2 max-h-96 overflow-y-auto text-sm text-gray-800">
          {segments.map((s) => (
            <div key={s.segment_num}>
              <span className="text-xs text-gray-500 mr-2">
                [{Math.floor(s.start_time / 60)
                  .toString()
                  .padStart(2, "0")}
                :
                {Math.floor(s.start_time % 60)
                  .toString()
                  .padStart(2, "0")}
                ]
              </span>
              <span>{s.text}</span>
            </div>
          ))}
          {segments.length === 0 && (
            <div className="text-gray-500 text-sm">No transcript segments yet.</div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MeetingDetail;

