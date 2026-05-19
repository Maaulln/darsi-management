import { useEffect, useState } from 'react';

const OUTGOING_DOMAINS = [
  { id: 'pasien_aktif', name: 'Pasien Aktif', table: 'refined_pasien_aktif', desc: 'Data rekam medis pasien rawat inap aktif.' },
  { id: 'okupansi_kamar', name: 'Okupansi Kamar', table: 'refined_okupansi_kamar', desc: 'Indikator keterisian tempat tidur (BOR) per unit.' },
  { id: 'meter_listrik', name: 'Konsumsi Listrik', table: 'refined_meter_listrik', desc: 'Pembacaan kWh meter listrik gedung per jam.' },
  { id: 'konsumsi_air', name: 'Konsumsi Air', table: 'refined_konsumsi_air', desc: 'Volume pemakaian air bersih PDAM rumah sakit.' },
  { id: 'biaya_operasional', name: 'Biaya Operasional', table: 'refined_biaya_operasional_unit', desc: 'Pengeluaran bulanan aktual vs anggaran belanja.' },
  { id: 'konsumsi_obat_alkes', name: 'Obat & Alkes', table: 'refined_konsumsi_obat_alkes', desc: 'Log pemakaian obat-obatan dan alat kesehatan steril.' },
  { id: 'lembur_staf', name: 'Lembur Staf', table: 'refined_lembur_staf', desc: 'Rekap jam lembur perawat, dokter, dan staf penunjang.' },
  { id: 'jadwal_alat_berat', name: 'Jadwal Alat', table: 'refined_jadwal_alat_berat', desc: 'Jadwal pemakaian peralatan diagnostik MRI/CT-Scan.' }
];

export default function Superadmin({ refreshSidebar }) {
  const [activeTab, setActiveTab] = useState('outgoing');
  
  // Simulator states
  const [simulatorEnabled, setSimulatorEnabled] = useState(true);
  const [simulatorLoading, setSimulatorLoading] = useState(false);
  
  // AI Config states
  const [aiUrl, setAiUrl] = useState('');
  const [aiModel, setAiModel] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiMessage, setAiMessage] = useState('');
  const [savedAiUrl, setSavedAiUrl] = useState('');
  const [savedAiModel, setSavedAiModel] = useState('');
  
  // Dynamic API states
  const [incomingApis, setIncomingApis] = useState([]);
  const [apiName, setApiName] = useState('');
  const [apiEndpoint, setApiEndpoint] = useState('');
  const [apiError, setApiError] = useState('');
  const [apiSuccess, setApiSuccess] = useState('');
  
  // JSON Preview states
  const [previewData, setPreviewData] = useState(null);
  const [previewTitle, setPreviewTitle] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);

  // Fetch simulator status
  useEffect(() => {
    fetch('/api/settings/simulator')
      .then(r => r.json())
      .then(data => setSimulatorEnabled(data.enabled))
      .catch(err => console.error('Gagal fetch status simulator:', err));
      
    fetch('/api/settings/ai')
      .then(r => r.json())
      .then(data => {
        if (data.url) {
          setAiUrl(data.url);
          setSavedAiUrl(data.url);
        }
        if (data.model) {
          setAiModel(data.model);
          setSavedAiModel(data.model);
        }
      })
      .catch(err => console.error('Gagal fetch konfigurasi AI:', err));
  }, []);

  // Fetch incoming APIs
  const fetchIncomingApis = () => {
    fetch('/api/settings/incoming-apis')
      .then(r => r.json())
      .then(data => setIncomingApis(data.apis || []))
      .catch(err => console.error('Gagal fetch API masuk:', err));
  };

  useEffect(() => {
    fetchIncomingApis();
  }, []);

  // Handle simulator toggle
  const toggleSimulator = (e) => {
    const enabled = e.target.checked;
    setSimulatorLoading(true);
    fetch('/api/settings/simulator', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled })
    })
      .then(r => r.json())
      .then(data => {
        setSimulatorEnabled(data.enabled);
        setSimulatorLoading(false);
      })
      .catch(err => {
        console.error('Gagal simpan status simulator:', err);
        setSimulatorLoading(false);
      });
  };

  // Handle AI Config save
  const handleSaveAiConfig = (e) => {
    e.preventDefault();
    setAiLoading(true);
    setAiMessage('');
    fetch('/api/settings/ai', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: aiUrl, model: aiModel })
    })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          setAiMessage('Konfigurasi AI berhasil disimpan. Jika URL eksternal, docker ollama lokal dimatikan.');
          setSavedAiUrl(data.url || '');
          setSavedAiModel(data.model || '');
          setAiUrl(data.url || '');
          setAiModel(data.model || '');
        }
        setAiLoading(false);
      })
      .catch(err => {
        console.error('Gagal simpan konfigurasi AI:', err);
        setAiMessage('Gagal menyimpan konfigurasi AI.');
        setAiLoading(false);
      });
  };

  // Handle AI Config reset
  const handleResetAiConfig = () => {
    setAiLoading(true);
    setAiMessage('');
    fetch('/api/settings/ai', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: '', model: '' })
    })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          setAiMessage('Konfigurasi berhasil dihapus. Sistem kembali menggunakan Ollama Lokal default dan docker ollama dinyalakan.');
          setSavedAiUrl('');
          setSavedAiModel('');
          setAiUrl('');
          setAiModel('');
        }
        setAiLoading(false);
      })
      .catch(err => {
        console.error('Gagal mereset konfigurasi AI:', err);
        setAiMessage('Gagal menghapus konfigurasi AI.');
        setAiLoading(false);
      });
  };

  // Handle preview example data
  const handlePreview = (domain) => {
    setPreviewLoading(true);
    setPreviewTitle(domain.name);
    setPreviewData(null);
    fetch(`/api/data/domain/${domain.id}?limit=3`)
      .then(r => r.json())
      .then(data => {
        setPreviewData(data.records || []);
        setPreviewLoading(false);
      })
      .catch(err => {
        console.error('Gagal preview data:', err);
        setPreviewLoading(false);
      });
  };

  // Add new dynamic API
  const handleAddApi = (e) => {
    e.preventDefault();
    setApiError('');
    setApiSuccess('');

    if (!apiName || !apiEndpoint) {
      setApiError('Harap isi Nama Menu dan Endpoint/URL Data Masuk.');
      return;
    }

    fetch('/api/settings/incoming-apis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: apiName,
        endpoint: apiEndpoint,
        external_url: null,
        metabase_url: null
      })
    })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => {
            throw new Error(
              Array.isArray(data.detail)
                ? data.detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ')
                : (data.detail || 'Gagal menyimpan integrasi.')
            );
          });
        }
        return r.json();
      })
      .then(data => {
        if (data.status === 'ok') {
          setApiSuccess(`Sukses menambahkan integrasi API "${apiName}"!`);
          setApiName('');
          setApiEndpoint('');
          fetchIncomingApis();
          if (refreshSidebar) refreshSidebar();
        } else {
          setApiError(data.detail || 'Gagal menyimpan integrasi.');
        }
      })
      .catch(err => {
        console.error(err);
        setApiError(err.message || 'Error koneksi ke server.');
      });
  };

  // Delete dynamic API
  const handleDeleteApi = (id, name) => {
    if (!window.confirm(`Hapus integrasi API "${name}"? Ini akan menghapus menu dashboard dinamis terkait.`)) {
      return;
    }

    fetch(`/api/settings/incoming-apis/${id}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          fetchIncomingApis();
          if (refreshSidebar) refreshSidebar();
        }
      })
      .catch(err => console.error('Gagal menghapus API:', err));
  };

  return (
    <div style={{ paddingBottom: '40px' }}>
      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border)', marginBottom: '24px' }}>
        <button
          className="btn"
          style={{
            borderBottom: activeTab === 'outgoing' ? '2px solid var(--primary)' : 'none',
            borderRadius: '0',
            padding: '12px 16px',
            color: activeTab === 'outgoing' ? 'var(--primary)' : 'var(--muted)',
            fontWeight: activeTab === 'outgoing' ? '600' : 'normal',
            background: 'none'
          }}
          onClick={() => setActiveTab('outgoing')}
        >
          API Keluar (Data Darsi)
        </button>
        <button
          className="btn"
          style={{
            borderBottom: activeTab === 'incoming' ? '2px solid var(--primary)' : 'none',
            borderRadius: '0',
            padding: '12px 16px',
            color: activeTab === 'incoming' ? 'var(--primary)' : 'var(--muted)',
            fontWeight: activeTab === 'incoming' ? '600' : 'normal',
            background: 'none'
          }}
          onClick={() => setActiveTab('incoming')}
        >
          API Masuk (Integrasi Metabase)
        </button>
        <button
          className="btn"
          style={{
            borderBottom: activeTab === 'simulator' ? '2px solid var(--primary)' : 'none',
            borderRadius: '0',
            padding: '12px 16px',
            color: activeTab === 'simulator' ? 'var(--primary)' : 'var(--muted)',
            fontWeight: activeTab === 'simulator' ? '600' : 'normal',
            background: 'none'
          }}
          onClick={() => setActiveTab('simulator')}
        >
          Simulator Data
        </button>
        <button
          className="btn"
          style={{
            borderBottom: activeTab === 'ai' ? '2px solid var(--primary)' : 'none',
            borderRadius: '0',
            padding: '12px 16px',
            color: activeTab === 'ai' ? 'var(--primary)' : 'var(--muted)',
            fontWeight: activeTab === 'ai' ? '600' : 'normal',
            background: 'none'
          }}
          onClick={() => setActiveTab('ai')}
        >
          Konfigurasi AI
        </button>
      </div>

      {/* Tab 1: Outgoing APIs */}
      {activeTab === 'outgoing' && (
        <div>
          <div className="section-head">
            <h2 className="section-title">Daftar API Keluar DARSI</h2>
            <span className="tag tag-blue">Pembersihan Otomatis Aktif</span>
          </div>
          <p style={{ color: 'var(--muted)', marginBottom: '20px', fontSize: '13px' }}>
            Data operasional DARSI yang telah dibersihkan secara real-time dapat diakses secara eksternal melalui endpoint HTTP GET per domain berikut.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px' }}>
            {OUTGOING_DOMAINS.map(domain => (
              <div key={domain.id} className="chart-card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', minHeight: '180px' }}>
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <h3 style={{ fontSize: '14px', fontWeight: '600' }}>{domain.name}</h3>
                    <span className="tag tag-purple">{domain.table}</span>
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '12px' }}>{domain.desc}</p>
                  
                  <div style={{ background: '#f8fafc', padding: '8px 12px', borderRadius: '6px', fontSize: '11px', fontFamily: 'monospace', color: '#475569', wordBreak: 'break-all', border: '1px solid var(--border)' }}>
                    GET http://localhost:8000/api/data/domain/{domain.id}
                  </div>
                </div>
                
                <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
                  <button className="btn" style={{ flex: '1', padding: '6px' }} onClick={() => {
                    navigator.clipboard.writeText(`http://localhost:8000/api/data/domain/${domain.id}`);
                    alert('Endpoint API Keluar disalin!');
                  }}>
                    Salin Endpoint
                  </button>
                  <button className="btn" style={{ flex: '1', padding: '6px' }} onClick={() => handlePreview(domain)}>
                    Pratinjau JSON
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* JSON Preview Modal/Box */}
          {previewTitle && (
            <div className="chart-card mt-16" style={{ borderLeft: '4px solid var(--primary)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h4 style={{ fontWeight: '600', fontSize: '13px' }}>Contoh Data Refined: {previewTitle}</h4>
                <button className="btn" style={{ padding: '2px 8px', fontSize: '11px' }} onClick={() => setPreviewTitle('')}>Tutup</button>
              </div>
              {previewLoading ? (
                <div className="loader" style={{ minHeight: '120px' }}>
                  <div className="spinner" />
                </div>
              ) : (
                <pre className="raw-json">
                  {previewData ? JSON.stringify(previewData, null, 2) : 'Data kosong.'}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Incoming APIs */}
      {activeTab === 'incoming' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '24px' }}>
          {/* Add Integration Form */}
          <div className="chart-card">
            <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px' }}>Tambah Integrasi Menu Dinamis</h3>
            
            <form onSubmit={handleAddApi} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  Nama Dashboard / Menu
                </label>
                <input
                  type="text"
                  placeholder="Contoh: Covid-19 Global"
                  value={apiName}
                  onChange={e => setApiName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  Endpoint / URL Sumber Data
                </label>
                <input
                  type="text"
                  placeholder="e.g. https://coronavirus.m.pipedream.net/  ATAU  /api/incoming/covid"
                  value={apiEndpoint}
                  onChange={e => setApiEndpoint(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
                <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                  Bisa berupa URL API eksternal (Auto-Pull) ATAU path lokal push webhook (e.g. /api/incoming/covid).
                </span>
              </div>

              {apiError && <div className="error-box" style={{ margin: '0', padding: '10px' }}>{apiError}</div>}
              {apiSuccess && <div style={{ color: '#059669', background: '#ecfdf5', padding: '10px', borderRadius: '6px', fontSize: '12px', border: '1px solid #a7f3d0' }}>{apiSuccess}</div>}

              <button type="submit" className="chat-send" style={{ width: '100%', margin: '0' }}>
                Simpan & Daftarkan Menu
              </button>
            </form>
          </div>

          {/* Ingestion API List */}
          <div className="chart-card" style={{ overflowX: 'auto' }}>
            <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px' }}>Daftar Integrasi API Masuk Aktif</h3>
            
            {incomingApis.length === 0 ? (
              <div className="empty-state">
                <span>Belum ada API masuk yang terintegrasi.</span>
                <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Gunakan form di sebelah kiri untuk menambahkan menu dynamic baru.</span>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nama Menu</th>
                    <th>Metode / Sumber Data</th>
                    <th style={{ textAlign: 'center' }}>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {incomingApis.map(api => (
                    <tr key={api.id}>
                      <td style={{ fontWeight: '600' }}>{api.name}</td>
                      <td>
                        {api.external_url ? (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 'bold', color: '#10b981' }}>🔄 AUTO-PULL GET</span>
                            <span style={{ fontSize: '10px', color: 'var(--muted)', fontFamily: 'monospace', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {api.external_url}
                            </span>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--primary)' }}>📥 CLIENT-PUSH POST</span>
                            <span style={{ fontSize: '10px', color: 'var(--muted)', fontFamily: 'monospace' }}>
                              POST {api.endpoint}
                            </span>
                          </div>
                        )}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <button
                          className="btn"
                          style={{ borderColor: '#fecaca', color: '#ef4444', padding: '4px 8px', fontSize: '11px' }}
                          onClick={() => handleDeleteApi(api.id, api.name)}
                        >
                          Hapus
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Simulator Control */}
      {activeTab === 'simulator' && (
        <div style={{ maxWidth: '600px', margin: 'auto' }}>
          <div className="kpi-card" style={{ borderTopColor: simulatorEnabled ? '#22c55e' : '#64748b', padding: '30px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--text)' }}>
                  Simulator Aliran Data SIMRS
                </h3>
                <p style={{ color: 'var(--muted)', fontSize: '12px', marginTop: '4px' }}>
                  Mensimulasikan injeksi data rekam medis dan sensor rumah sakit ke PostgreSQL setiap 10 detik.
                </p>
              </div>
              <span className={`tag ${simulatorEnabled ? 'tag-green' : 'tag-blue'}`} style={{ padding: '6px 12px', fontSize: '12px' }}>
                {simulatorEnabled ? 'SIMULATOR AKTIF' : 'NONAKTIF'}
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid var(--border)', marginBottom: '24px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                <span style={{ fontWeight: '600', fontSize: '13px' }}>Sakelar Status Simulator</span>
                <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Aktifkan untuk menghasilkan data dummy operasional baru secara otomatis.</span>
              </div>
              
              <div className="toggle-wrap">
                {simulatorLoading ? (
                  <div className="spinner" style={{ width: '20px', height: '20px', borderWidth: '2px' }} />
                ) : (
                  <input
                    type="checkbox"
                    className="toggle"
                    checked={simulatorEnabled}
                    onChange={toggleSimulator}
                  />
                )}
              </div>
            </div>

            <div style={{ fontSize: '12px', color: 'var(--muted)', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
              <strong>Catatan Sistem:</strong> Menonaktifkan simulator akan membekukan penambahan data baru ke tabel PostgreSQL raw_*. Namun, data yang sudah ada akan tetap utuh dan pembersihan (Refinement/Sync) tetap dapat dijalankan secara manual atau via cronjob n8n.
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: AI Configuration */}
      {activeTab === 'ai' && (
        <div style={{ maxWidth: '600px', margin: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Active AI Config Status Card */}
          <div className="kpi-card" style={{ borderTopColor: savedAiUrl ? '#10b981' : '#3b82f6', padding: '24px' }}>
            <h3 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text)', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ display: 'inline-block', width: '10px', height: '10px', borderRadius: '50%', background: savedAiUrl ? '#10b981' : '#3b82f6' }} />
              Layanan AI Aktif Saat Ini
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
                <span style={{ width: '120px', fontSize: '12px', color: 'var(--muted)', fontWeight: '500' }}>Tipe Koneksi:</span>
                <span style={{ fontSize: '12px', fontWeight: 'bold', color: savedAiUrl ? '#10b981' : '#3b82f6' }}>
                  {savedAiUrl ? '🔄 Eksternal (API Remote)' : '🏠 Lokal (Default Ollama Internal)'}
                </span>
              </div>
              
              <div style={{ display: 'flex', borderBottom: '1px solid #f1f5f9', paddingBottom: '8px' }}>
                <span style={{ width: '120px', fontSize: '12px', color: 'var(--muted)', fontWeight: '500' }}>Host / Endpoint:</span>
                <span style={{ fontSize: '12px', fontFamily: 'monospace', color: 'var(--text)' }}>
                  {savedAiUrl || 'http://ollama:11434'}
                </span>
              </div>
              
              <div style={{ display: 'flex', paddingBottom: '4px' }}>
                <span style={{ width: '120px', fontSize: '12px', color: 'var(--muted)', fontWeight: '500' }}>Model Aktif:</span>
                <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text)' }}>
                  {savedAiModel || 'qwen3.5:2b'}
                </span>
              </div>
            </div>
          </div>

          <div className="chart-card">
            <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '8px' }}>Atur Konfigurasi AI Baru</h3>
            <p style={{ color: 'var(--muted)', fontSize: '12px', marginBottom: '20px' }}>
              Ganti endpoint Ollama lokal dengan API eksternal (contoh: medlama2 via Cloudflare tunnel). Kosongkan URL untuk kembali menggunakan default lokal.
            </p>
            
            <form onSubmit={handleSaveAiConfig} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  AI API URL
                </label>
                <input
                  type="text"
                  placeholder="Contoh: https://auburn-absence-channels-accounting.trycloudflare.com"
                  value={aiUrl}
                  onChange={e => setAiUrl(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
                <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                  Kosongkan untuk menggunakan default internal (http://ollama:11434).
                </span>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  Model AI
                </label>
                <input
                  type="text"
                  placeholder="Contoh: qwen3.5:2b atau medlama2"
                  value={aiModel}
                  onChange={e => setAiModel(e.target.value)}
                  style={{ width: '100%', padding: '10px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
              </div>

              {aiMessage && (
                <div style={{ color: aiMessage.includes('Gagal') ? '#ef4444' : '#059669', background: aiMessage.includes('Gagal') ? '#fef2f2' : '#ecfdf5', padding: '10px', borderRadius: '6px', fontSize: '12px', border: `1px solid ${aiMessage.includes('Gagal') ? '#fecaca' : '#a7f3d0'}` }}>
                  {aiMessage}
                </div>
              )}

              <div style={{ display: 'flex', gap: '10px', marginTop: '4px' }}>
                <button type="submit" className="chat-send" style={{ flex: 2, margin: '0', display: 'flex', justifyContent: 'center' }} disabled={aiLoading}>
                  {aiLoading ? <div className="spinner" style={{ width: '16px', height: '16px' }} /> : 'Simpan Konfigurasi'}
                </button>
                {savedAiUrl && (
                  <button type="button" className="btn" onClick={handleResetAiConfig} style={{ flex: 1, borderColor: '#ef4444', color: '#ef4444', background: '#fff', fontSize: '13px', padding: '10px 16px', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0' }} disabled={aiLoading}>
                    Hapus
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
