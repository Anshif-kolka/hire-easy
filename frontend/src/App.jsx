import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Jobs from './pages/Jobs';
import Candidates from './pages/Candidates';
import Compare from './pages/Compare';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/jobs" element={<Jobs />} />
        <Route path="/candidates" element={<Candidates />} />
        <Route path="/compare" element={<Compare />} />
      </Routes>
    </Router>
  );
}

export default App;
