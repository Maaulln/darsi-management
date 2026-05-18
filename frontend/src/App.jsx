import { Routes, Route, NavLink, useLocation, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import Chat from './pages/Chat';
import Summary from './pages/Summary';
import MetabasePage from './pages/MetabasePage';
import StatusPage from './pages/StatusPage';
import Superadmin from './pages/Superadmin';

const NAV = [
  {
    path: '/', label: 'Dashboard', exact: true,
    d: 'M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM11 13a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z',
  },
  {
    path: '/analytics', label: 'Analitik',
    d: 'M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z',
  },
  {
    path: '/chat', label: 'Chat AI',
    d: 'M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z',
    fr: true,
  },
  {
    path: '/summary', label: 'Ringkasan',
    d: 'M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z',
    fr: true,
  },
  {
    path: '/metabase', label: 'Metabase',
    d: 'M2 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1H3a1 1 0 01-1-1V4zM8 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1H9a1 1 0 01-1-1V4zM15 3a1 1 0 00-1 1v12a1 1 0 001 1h2a1 1 0 001-1V4a1 1 0 00-1-1h-2z',
  },
  {
    path: '/status', label: 'Status Sistem',
    d: 'M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z',
    fr: true,
  },
];

export default function App() {
  const [sysStatus, setSysStatus] = useState('checking');
  const [clock, setClock] = useState('');
  const [dynamicNavs, setDynamicNavs] = useState([]);
  const location = useLocation();

  const loadDynamicNavs = () => {
    fetch('/api/settings/incoming-apis')
      .then(r => r.json())
      .then(data => {
        if (data.apis) {
          setDynamicNavs(data.apis.map(api => ({
            path: `/dynamic-api/${api.id}`,
            label: api.name,
            metabase_url: api.metabase_url,
            d: 'M2 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1H3a1 1 0 01-1-1V4zM8 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1H9a1 1 0 01-1-1V4zM15 3a1 1 0 00-1 1v12a1 1 0 001 1h2a1 1 0 001-1V4a1 1 0 00-1-1h-2z',
            isDynamic: true
          })));
        }
      })
      .catch(err => console.error("Gagal load API dinamis:", err));
  };

  useEffect(() => {
    loadDynamicNavs();
  }, []);

  useEffect(() => {
    const tick = () =>
      setClock(new Date().toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const check = () =>
      fetch('/api/health')
        .then(r => setSysStatus(r.ok ? 'ok' : 'error'))
        .catch(() => setSysStatus('error'));
    check();
    const t = setInterval(check, 30000);
    return () => clearInterval(t);
  }, []);

  const allNavs = [
    ...NAV,
    ...dynamicNavs,
    {
      path: '/superadmin', label: 'Superadmin',
      d: 'M9.243 3.03a1 1 0 01.727.293l2.4 2.4a1 1 0 01.293.727v2.4a1 1 0 01-.293.727l-2.4 2.4a1 1 0 01-.727.293H6.843a1 1 0 01-.727-.293l-2.4-2.4A1 1 0 013.42 6.86V4.46a1 1 0 01.293-.727l2.4-2.4a1 1 0 01.727-.293h2.4z',
      fr: true
    }
  ];

  const currentNav = allNavs.find(n =>
    n.exact ? location.pathname === n.path : location.pathname.startsWith(n.path) && n.path !== '/'
  ) ?? allNavs[0];

  const noPad = ['/chat', '/metabase'].includes(location.pathname) || location.pathname.startsWith('/dynamic-api');

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">D</div>
          <div>
            <div className="brand-name">DARSI</div>
            <div className="brand-sub">RSI A. Yani Surabaya</div>
          </div>
        </div>

        <nav className="nav">
          {allNavs.map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.exact}
              className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            >
              <svg className="nav-icon" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule={item.fr ? 'evenodd' : 'nonzero'} clipRule={item.fr ? 'evenodd' : undefined} d={item.d} />
              </svg>
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-foot">
          <div className="sys-pill">
            <span className={`sys-dot${sysStatus === 'ok' ? ' ok' : sysStatus === 'error' ? ' error' : ''}`} />
            <span>
              {sysStatus === 'ok' ? 'Sistem aktif' : sysStatus === 'error' ? 'Sistem error' : 'Memeriksa…'}
            </span>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <h1 className="page-title">{currentNav.label}</h1>
          <div className="topbar-right">
            <span className="clock">{clock}</span>
            <span className="ai-badge">● AI Generatif</span>
          </div>
        </header>

        <div className={`content-area${noPad ? ' no-pad' : ''}`}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/summary" element={<Summary />} />
            <Route path="/metabase" element={<MetabasePage />} />
            <Route path="/status" element={<StatusPage />} />
            <Route path="/superadmin" element={<Superadmin refreshSidebar={loadDynamicNavs} />} />
            {dynamicNavs.map(api => (
              <Route
                key={api.path}
                path={api.path}
                element={
                  <div className="metabase-wrap" style={{ height: '100%' }}>
                    <iframe src={api.metabase_url} title={api.label} />
                  </div>
                }
              />
            ))}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </div>
    </div>
  );
}
