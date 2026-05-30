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
  
  // AI Models states
  const [aiModels, setAiModels] = useState([]);
  const [detectMode, setDetectMode] = useState('key'); // 'url' untuk Ollama, 'key' untuk Gemini/OpenAI
  const [detectApiUrl, setDetectApiUrl] = useState('');
  const [detectApiKey, setDetectApiKey] = useState('');
  const [detectedModels, setDetectedModels] = useState([]);
  const [aiModelDetecting, setAiModelDetecting] = useState(false);
  const [aiModelName, setAiModelName] = useState('');
  const [aiModelApiUrl, setAiModelApiUrl] = useState('');
  const [aiModelApiKey, setAiModelApiKey] = useState('');
  const [aiModelModelName, setAiModelModelName] = useState('');
  const [aiModelDescription, setAiModelDescription] = useState('');
  const [aiModelLoading, setAiModelLoading] = useState(false);
  const [aiModelError, setAiModelError] = useState('');
  const [aiModelSuccess, setAiModelSuccess] = useState('');
  const [editingModelId, setEditingModelId] = useState(null);
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
      
    fetchAiModels();
  }, []);

  // Fetch incoming APIs
  const fetchIncomingApis = () => {
    fetch('/api/settings/incoming-apis')
      .then(r => r.json())
      .then(data => setIncomingApis(data.apis || []))
      .catch(err => console.error('Gagal fetch API masuk:', err));
  };

  // Fetch AI Models
  const fetchAiModels = () => {
    fetch('/api/settings/ai-models')
      .then(r => r.json())
      .then(data => setAiModels(data.models || []))
      .catch(err => console.error('Gagal fetch AI models:', err));
  };

  useEffect(() => {
    fetchIncomingApis();
  }, []);

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

  // Handle Detect AI Models
  const handleDetectModels = (e) => {
    e.preventDefault();
    setAiModelError('');
    setDetectedModels([]);

    // Option 1: Flexible - salah satu saja
    if (!detectApiUrl && !detectApiKey) {
      setAiModelError('Harap isi API URL (Ollama) atau API Key (Gemini/OpenAI) minimal salah satu.');
      return;
    }

    setAiModelDetecting(true);
    fetch('/api/settings/ai-models/detect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_url: detectApiUrl || null,
        api_key: detectApiKey || null
      })
    })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => {
            throw new Error(data.detail || 'Gagal mendeteksi models');
          });
        }
        return r.json();
      })
      .then(data => {
        if (data.status === 'ok') {
          setDetectedModels(data.models || []);
          setAiModelApiUrl(data.api_url || '');
          setAiModelApiKey(data.api_key || '');
          setAiModelSuccess(`Berhasil mendeteksi ${data.models.length} model! Pilih salah satu di bawah.`);
        }
        setAiModelDetecting(false);
      })
      .catch(err => {
        console.error(err);
        setAiModelError(err.message);
        setAiModelDetecting(false);
      });
  };

  // Handle Select Model from detected list
  const handleSelectDetectedModel = (model) => {
    setAiModelModelName(model.name);
    setAiModelDescription(model.description || '');
    // Auto-generate name if not set
    if (!aiModelName) {
      setAiModelName(model.display_name || model.name);
    }
  };

  // Handle Save AI Model
  const handleSaveAiModel = (e) => {
    e.preventDefault();
    setAiModelError('');
    setAiModelSuccess('');

    // Flexible validation - either URL or Key, but not both empty
    if (!aiModelName || !aiModelModelName) {
      setAiModelError('Harap isi Nama Model dan Nama Model Provider.');
      return;
    }

    if (!aiModelApiUrl && !aiModelApiKey) {
      setAiModelError('Harap isi API URL (Ollama) atau API Key (Gemini/OpenAI) minimal salah satu.');
      return;
    }

    setAiModelLoading(true);

    const method = editingModelId ? 'PUT' : 'POST';
    const url = editingModelId 
      ? `/api/settings/ai-models/${editingModelId}`
      : '/api/settings/ai-models';

    fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: aiModelName,
        api_url: aiModelApiUrl || null,
        api_key: aiModelApiKey || null,
        model_name: aiModelModelName,
        description: aiModelDescription
      })
    })
      .then(r => {
        if (!r.ok) {
          return r.json().then(data => {
            throw new Error(data.detail || 'Gagal menyimpan model AI');
          });
        }
        return r.json();
      })
      .then(data => {
        if (data.status === 'ok') {
          setAiModelSuccess(data.message);
          resetAiModelForm();
          fetchAiModels();
        }
        setAiModelLoading(false);
      })
      .catch(err => {
        console.error(err);
        setAiModelError(err.message);
        setAiModelLoading(false);
      });
  };

  // Handle delete AI Model
  const handleDeleteAiModel = (id, name) => {
    if (!window.confirm(`Hapus AI Model "${name}"? Ini tidak dapat dibatalkan.`)) {
      return;
    }

    fetch(`/api/settings/ai-models/${id}`, { method: 'DELETE' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          setAiModelSuccess(data.message);
          fetchAiModels();
        }
      })
      .catch(err => console.error('Gagal menghapus AI Model:', err));
  };

  // Handle activate AI Model
  const handleActivateAiModel = (id) => {
    fetch(`/api/settings/ai-models/${id}/activate`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          setAiModelSuccess(data.message);
          fetchAiModels();
          // Update saved config
          if (data.active_model) {
            setSavedAiUrl(data.active_model.api_url);
            setSavedAiModel(data.active_model.model_name);
          }
        }
      })
      .catch(err => console.error('Gagal mengaktifkan AI Model:', err));
  };

  // Handle edit AI Model
  const handleEditAiModel = (model) => {
    setEditingModelId(model.id);
    setAiModelName(model.name);
    setAiModelApiUrl(model.api_url);
    setAiModelApiKey(model.api_key || '');
    setAiModelModelName(model.model_name);
    setAiModelDescription(model.description);
    setDetectedModels([]);
  };

  // Reset AI Model Form
  const resetAiModelForm = () => {
    setEditingModelId(null);
    setDetectApiUrl('');
    setDetectApiKey('');
    setDetectedModels([]);
    setAiModelName('');
    setAiModelApiUrl('');
    setAiModelApiKey('');
    setAiModelModelName('');
    setAiModelDescription('');
    setAiModelError('');
    setAiModelSuccess('');
  };

  // Handle cancel edit
  const handleCancelEdit = () => {
    resetAiModelForm();
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
            borderBottom: activeTab === 'ai-models' ? '2px solid var(--primary)' : 'none',
            borderRadius: '0',
            padding: '12px 16px',
            color: activeTab === 'ai-models' ? 'var(--primary)' : 'var(--muted)',
            fontWeight: activeTab === 'ai-models' ? '600' : 'normal',
            background: 'none'
          }}
          onClick={() => setActiveTab('ai-models')}
        >
          Manajemen Model AI
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

      {/* Tab 4: AI Models Management */}
      {activeTab === 'ai-models' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.8fr', gap: '24px' }}>
          {/* Add/Edit AI Model Form */}
          <div className="chart-card">
            <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px' }}>
              {editingModelId ? 'Edit Model AI' : 'Tambah Model AI Baru'}
            </h3>
            
            {!editingModelId && detectedModels.length === 0 && (
              <>
                <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '12px' }}>
                  <strong>Opsi 1: Flexible</strong> - Masukkan salah satu saja:
                </p>
                <ul style={{ fontSize: '11px', color: 'var(--muted)', marginBottom: '16px', paddingLeft: '20px' }}>
                  <li><strong>Ollama:</strong> Cukup API URL saja (contoh: http://localhost:11434)</li>
                  <li><strong>Gemini/OpenAI:</strong> Cukup API Key saja (URL sudah default)</li>
                </ul>
                
                <form onSubmit={handleDetectModels} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                      API URL (Ollama) <span style={{ color: 'var(--muted)', fontSize: '11px', fontWeight: 'normal' }}>opsional</span>
                    </label>
                    <input
                      type="text"
                      placeholder="Contoh: http://localhost:11434"
                      value={detectApiUrl}
                      onChange={e => setDetectApiUrl(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                    />
                    <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                      Kosongkan jika menggunakan Gemini/OpenAI
                    </span>
                  </div>

                  <div style={{ borderTop: '1px dashed var(--border)', paddingTop: '12px' }}>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                      API Key (Gemini/OpenAI) <span style={{ color: 'var(--muted)', fontSize: '11px', fontWeight: 'normal' }}>opsional</span>
                    </label>
                    <input
                      type="password"
                      placeholder="Contoh: AIzaSyD88evpukX7zPjDKybcKK1CKdkBB2N2xpI"
                      value={detectApiKey}
                      onChange={e => setDetectApiKey(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                    />
                    <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                      Kosongkan jika menggunakan Ollama API URL
                    </span>
                  </div>

                  {aiModelError && <div className="error-box" style={{ margin: '0', padding: '10px' }}>{aiModelError}</div>}
                  {aiModelSuccess && <div style={{ color: '#059669', background: '#ecfdf5', padding: '10px', borderRadius: '6px', fontSize: '12px', border: '1px solid #a7f3d0' }}>{aiModelSuccess}</div>}

                  <button type="submit" className="chat-send" style={{ width: '100%', margin: '0', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px' }} disabled={aiModelDetecting}>
                    {aiModelDetecting ? (
                      <>
                        <div className="spinner" style={{ width: '14px', height: '14px' }} />
                        Deteksi Model...
                      </>
                    ) : (
                      '🔍 Deteksi Model Tersedia'
                    )}
                  </button>
                </form>
              </>
            )}

            {detectedModels.length > 0 && (
              <>
                <p style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '12px' }}>
                  Pilih salah satu model dari list di bawah:
                </p>
                
                <div style={{ maxHeight: '250px', overflowY: 'auto', marginBottom: '16px', border: '1px solid var(--border)', borderRadius: '6px' }}>
                  {detectedModels.map((model, idx) => (
                    <div key={idx} style={{ padding: '10px 12px', borderBottom: idx < detectedModels.length - 1 ? '1px solid #f1f5f9' : 'none', cursor: 'pointer', background: aiModelModelName === model.name ? '#ecfdf5' : 'transparent' }} onClick={() => handleSelectDetectedModel(model)}>
                      <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text)' }}>{model.display_name}</div>
                      <div style={{ fontSize: '10px', color: 'var(--muted)' }}>{model.description}</div>
                    </div>
                  ))}
                </div>
              </>
            )}

            <form onSubmit={handleSaveAiModel} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  Nama Konfigurasi Model *
                </label>
                <input
                  type="text"
                  placeholder="Contoh: Gemini Pro v1, GPT-4 Production"
                  value={aiModelName}
                  onChange={e => setAiModelName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
                <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                  Nama unik untuk identifikasi konfigurasi di DARSI.
                </span>
              </div>

              {(aiModelApiUrl || aiModelApiKey || detectedModels.length > 0) && (
                <>
                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                      Nama Model Provider *
                    </label>
                    <input
                      type="text"
                      placeholder="Contoh: gemini-pro, gpt-4, llama2"
                      value={aiModelModelName}
                      onChange={e => setAiModelModelName(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                    />
                    <span style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '4px', display: 'block' }}>
                      {detectedModels.length > 0 ? 'Sudah dipilih dari list deteksi.' : 'ID model sesuai dokumentasi provider.'}
                    </span>
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                      Deskripsi (Opsional)
                    </label>
                    <textarea
                      placeholder="Catatan tentang model, contoh: Model cepat untuk response real-time, biaya lebih rendah, dll"
                      value={aiModelDescription}
                      onChange={e => setAiModelDescription(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none', minHeight: '60px', fontFamily: 'inherit', fontSize: '12px' }}
                    />
                  </div>
                </>
              )}

              {aiModelError && <div className="error-box" style={{ margin: '0', padding: '10px' }}>{aiModelError}</div>}
              {aiModelSuccess && <div style={{ color: '#059669', background: '#ecfdf5', padding: '10px', borderRadius: '6px', fontSize: '12px', border: '1px solid #a7f3d0' }}>{aiModelSuccess}</div>}

              {(aiModelApiUrl || aiModelApiKey || detectedModels.length > 0) && (
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button type="submit" className="chat-send" style={{ flex: 1, margin: '0' }} disabled={aiModelLoading}>
                    {aiModelLoading ? <div className="spinner" style={{ width: '16px', height: '16px' }} /> : (editingModelId ? 'Perbarui Model' : 'Simpan Model')}
                  </button>
                  {(editingModelId || detectedModels.length > 0) && (
                    <button type="button" className="btn" onClick={handleCancelEdit} style={{ flex: 1, borderColor: '#64748b', color: '#64748b', background: '#fff' }}>
                      Batal
                    </button>
                  )}
                </div>
              )}
            </form>
          </div>

          {/* AI Models List */}
          <div className="chart-card" style={{ overflowX: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3 style={{ fontSize: '14px', fontWeight: '600' }}>Daftar Model AI Tersedia</h3>
              {savedAiUrl && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', padding: '4px 8px', background: '#ecfdf5', borderRadius: '4px', color: '#059669' }}>
                  🟢 Model Aktif: <strong>{savedAiModel}</strong>
                </div>
              )}
            </div>
            
            {aiModels.length === 0 ? (
              <div className="empty-state">
                <span>Belum ada model AI yang didaftarkan.</span>
                <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Gunakan form di sebelah kiri untuk mendeteksi dan menambahkan model baru.</span>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nama Model</th>
                    <th>Provider</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'center' }}>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {aiModels.map(model => (
                    <tr key={model.id} style={{ background: model.is_active ? '#ecfdf5' : 'transparent' }}>
                      <td style={{ fontWeight: '600' }}>
                        {model.name}
                        {model.is_active && <span className="tag tag-green" style={{ marginLeft: '8px', fontSize: '10px' }}>AKTIF</span>}
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span style={{ fontSize: '11px', fontFamily: 'monospace', color: '#666' }}>{model.model_name}</span>
                          <span style={{ fontSize: '10px', color: 'var(--muted)', fontFamily: 'monospace', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {model.api_url}
                          </span>
                        </div>
                      </td>
                      <td>
                        {model.is_active ? (
                          <span className="tag tag-green">🟢 Digunakan</span>
                        ) : (
                          <span className="tag" style={{ background: '#f1f5f9', color: '#64748b' }}>⚪ Standby</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: '6px', justifyContent: 'center', flexWrap: 'wrap' }}>
                          {!model.is_active && (
                            <button
                              className="btn"
                              style={{ borderColor: '#10b981', color: '#10b981', padding: '4px 8px', fontSize: '11px' }}
                              onClick={() => handleActivateAiModel(model.id)}
                            >
                              Aktifkan
                            </button>
                          )}
                          <button
                            className="btn"
                            style={{ borderColor: '#3b82f6', color: '#3b82f6', padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => handleEditAiModel(model)}
                          >
                            Edit
                          </button>
                          <button
                            className="btn"
                            style={{ borderColor: '#fecaca', color: '#ef4444', padding: '4px 8px', fontSize: '11px' }}
                            onClick={() => handleDeleteAiModel(model.id, model.name)}
                          >
                            Hapus
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
