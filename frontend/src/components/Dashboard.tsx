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

const Dashboard: React.FC = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get<Meeting[]>("/api/meetings/");
        setMeetings(res.data);
      } catch (err) {
        console.error("Failed to load meetings", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return <div className="text-gray-600">Loading meetings…</div>;
  }

  if (!meetings.length) {
    return <div className="text-gray-600">No meetings recorded yet.</div>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">Recent meetings</h2>
      <div className="bg-white shadow-sm rounded-lg divide-y divide-gray-100">
        {meetings.map((m) => (
          <Link
            key={m.id}
            to={`/meeting/${m.id}`}
            className="flex justify-between items-center px-4 py-3 hover:bg-gray-50"
          >
            <div>
              <div className="text-sm font-medium text-gray-900">
                {m.title}
              </div>
              <div className="text-xs text-gray-500">
                Started {new Date(m.start_time).toLocaleString()}
              </div>
            </div>
            <span className="text-xs uppercase tracking-wide text-gray-500">
              {m.status}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;

