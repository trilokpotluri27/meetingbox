import React, { useEffect, useState } from "react";
import axios from "axios";

interface SystemInfo {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb: number;
  memory_total_gb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
}

interface ApiResponse {
  system: SystemInfo;
}

const SystemStatus: React.FC = () => {
  const [info, setInfo] = useState<SystemInfo | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const res = await axios.get<ApiResponse>("/api/system/status");
        setInfo(res.data.system);
      } catch (err) {
        console.error("Failed to load system status", err);
      }
    };
    load();
  }, []);

  if (!info) {
    return <div className="text-gray-600">Loading system status…</div>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-900">System status</h2>
      <div className="bg-white rounded-lg shadow-sm p-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-xs text-gray-500 uppercase mb-1">CPU</div>
          <div className="text-gray-900">{info.cpu_percent.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase mb-1">Memory</div>
          <div className="text-gray-900">
            {info.memory_percent.toFixed(1)}% (
            {info.memory_used_gb.toFixed(1)} /{" "}
            {info.memory_total_gb.toFixed(1)} GB)
          </div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase mb-1">Disk</div>
          <div className="text-gray-900">
            {info.disk_percent.toFixed(1)}% (
            {info.disk_used_gb.toFixed(1)} /{" "}
            {info.disk_total_gb.toFixed(1)} GB)
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;

