import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { LayoutDashboard, Ticket, Users, Upload, Bot, FlaskConical } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import TicketsPage from './pages/TicketsPage';
import ManagersPage from './pages/ManagersPage';
import UploadPage from './pages/UploadPage';
import DistributionPage from './pages/DistributionPage';
import AIAssistant from './components/AIAssistant';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        {/* Navbar */}
        <header className="top-navbar">
          <div className="navbar-logo">
            <div className="logo-icon" style={{ background: 'var(--accent-primary)', color: 'var(--bg-primary)' }}>F</div>
            <h1>FIRE</h1>
          </div>
          <nav className="navbar-nav">
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <LayoutDashboard /> Home
            </NavLink>
            <NavLink to="/tickets" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Ticket /> Tickets
            </NavLink>
            <NavLink to="/managers" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Users /> Managers
            </NavLink>
            <NavLink to="/upload" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Upload /> Upload Data
            </NavLink>
            <NavLink to="/distribution" className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <FlaskConical /> Playground
            </NavLink>
          </nav>

          <div className="navbar-actions" style={{ display: 'flex', gap: '16px' }}>
            <button className="btn btn-primary" style={{ padding: '8px 20px' }}>Explore now</button>
          </div>
        </header>

        {/* Main */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tickets" element={<TicketsPage />} />
            <Route path="/managers" element={<ManagersPage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/distribution" element={<DistributionPage />} />
          </Routes>
        </main>

        {/* AI Assistant Widget */}
        <AIAssistant />
      </div>
    </BrowserRouter>
  );
}

export default App;
