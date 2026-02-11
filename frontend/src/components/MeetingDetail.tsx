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

interface MeetingDetailResponse {
  meeting: Meeting;
  segments: Segment[];
  summary: Summary | null;
}

const MeetingDetail: React.FC = () => {
  const { id } = useParams();
  const [data, setData] = useState<MeetingDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get<MeetingDetailResponse>(`/api/meetings/${id}`);
        setData(res.data);
      } catch (err) {
        console.error("Failed to load meeting", err);
      } finally {
        setLoading(false);
      }
    };
    if (id) {
      load();
    }
  }, [id]);

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

  const { meeting, segments, summary } = data;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">{meeting.title}</h2>
        <Link to="/" className="text-sm text-blue-600">
          Back
        </Link>
      </div>

      {summary && (
        <div className="bg-white shadow-sm rounded-lg p-4 space-y-2">
          <div className="text-sm font-semibold text-gray-900">AI Summary</div>
          <p className="text-sm text-gray-800">{summary.summary}</p>
          {summary.decisions.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-500 uppercase mt-2">
                Decisions
              </div>
              <ul className="list-disc list-inside text-sm text-gray-800">
                {summary.decisions.map((d, idx) => (
                  <li key={idx}>{d}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.action_items.length > 0 && (
            <div>
              <div className="text-xs font-semibold text-gray-500 uppercase mt-2">
                Action items
              </div>
              <ul className="list-disc list-inside text-sm text-gray-800">
                {summary.action_items.map((a, idx) => (
                  <li key={idx}>
                    {a.task}
                    {a.assignee && ` – ${a.assignee}`}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {summary.topics.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {summary.topics.map((t, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700"
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

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

