// src/App.jsx
import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar        from './components/Sidebar';
import Navbar         from './components/Navbar';
import Dashboard      from './pages/Dashboard';
import Workloads      from './pages/Workloads';
import SubmitWorkload from './pages/SubmitWorkload';
import Reports        from './pages/Reports';
import Settings       from './pages/Settings';
import './App.css';

export default function App() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <BrowserRouter>
      <div className="app-shell" data-sidebar-collapsed={collapsed}>
        <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />
        <div className="app-content" id="main-content">
          <Navbar />
          <Routes>
            <Route path="/"          element={<Dashboard />} />
            <Route path="/workloads" element={<Workloads />} />
            <Route path="/submit"    element={<SubmitWorkload />} />
            <Route path="/reports"   element={<Reports />} />
            <Route path="/settings"  element={<Settings />} />
            {/* Fallback */}
            <Route path="*"          element={<Dashboard />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
