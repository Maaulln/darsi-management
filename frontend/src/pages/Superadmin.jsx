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
  
  // Dynamic API states
  const [incomingApis, setIncomingApis] = useState([]);
  const [apiName, setApiName] = useState('');
  const [apiEndpoint, setApiEndpoint] = useState('');
  const [apiMetabase, setApiMetabase] = useState('');
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

    if (!apiName || !apiEndpoint || !apiMetabase) {
      setApiError('Harap isi semua field formulir API Masuk.');
      return;
    }

    fetch('/api/settings/incoming-apis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: apiName,
        endpoint: apiEndpoint,
        metabase_url: apiMetabase
      })
    })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          setApiSuccess(`Sukses menambahkan integrasi API "${apiName}"!`);
          setApiName('');
          setApiEndpoint('');
          setApiMetabase('');
          fetchIncomingApis();
          if (refreshSidebar) refreshSidebar();
        } else {
          setApiError(data.detail || 'Gagal menyimpan integrasi.');
        }
      })
      .catch(err => setApiError(`Error: ${err}`));
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
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '24px' }}>
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
                  placeholder="Contoh: Metrik Laundry"
                  value={apiName}
                  onChange={e => setApiName(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  Endpoint Data Masuk (Ingestion)
                </label>
                <input
                  type="text"
                  placeholder="Contoh: /api/incoming/laundry"
                  value={apiEndpoint}
                  onChange={e => setApiEndpoint(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: '600', marginBottom: '6px', color: 'var(--text)' }}>
                  Metabase Iframe / Public Embed Link
                </label>
                <input
                  type="text"
                  placeholder="http://localhost:3001/public/dashboard/..."
                  value={apiMetabase}
                  onChange={e => setApiMetabase(e.target.value)}
                  style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', outline: 'none' }}
                />
              </div>

              {apiError && <div className="error-box" style={{ margin: '0', padding: '10px' }}>{apiError}</div>}
              {apiSuccess && <div style={{ color: '#059669', background: '#ecfdf5', padding: '10px', borderRadius: '6px', fontSize: '12px', border: '1px solid #a7f3d0' }}>{apiSuccess}</div>}

              <button type="submit" className="chat-send" style={{ width: '100%', margin: '0' }}>
                Simpan & Daftarkan Menu
              </button>
            </form>
          </div>

          {/* Ingestion API List */}
          <div className="chart-card">
            <h3 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '16px' }}>Daftar Integrasi API Masuk Aktif</h3>
            
            {incomingApis.length === 0 ? (
              <div className="empty-state">
                <span>Belum ada API masuk yang terintegrasi.</span>
                <span style={{ fontSize: '11px', color: 'var(--muted)' }}>Gunakan form di sebelah kiri untuk menambah menu dynamic Metabase baru.</span>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Nama Menu</th>
                    <th>Ingress Endpoint</th>
                    <th>Target Metabase Embed</th>
                    <th style={{ textAlign: 'center' }}>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {incomingApis.map(api => (
                    <tr key={api.id}>
                      <td style={{ fontWeight: '600' }}>{api.name}</td>
                      <td>
                        <span className="tag tag-teal" style={{ fontFamily: 'monospace' }}>{api.endpoint}</span>
                      </td>
                      <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '11px', color: 'var(--muted)' }}>
                        {api.metabase_url}
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
    </div>
  );
}
