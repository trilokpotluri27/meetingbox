import React from "react";
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Dashboard from "./components/Dashboard";
import MeetingDetail from "./components/MeetingDetail";
import SystemStatus from "./components/SystemStatus";

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white shadow-sm">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16 items-center">
              <div className="flex items-center space-x-6">
                <span className="text-xl font-semibold text-gray-900">
                  MeetingBox
                </span>
                <Link to="/" className="text-sm text-gray-700 hover:text-black">
                  Dashboard
                </Link>
                <Link
                  to="/system"
                  className="text-sm text-gray-700 hover:text-black"
                >
                  System
                </Link>
              </div>
            </div>
          </div>
        </nav>

        <main className="max-w-6xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/meeting/:id" element={<MeetingDetail />} />
            <Route path="/system" element={<SystemStatus />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
};

export default App;

