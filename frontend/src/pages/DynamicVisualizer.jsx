import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export default function DynamicVisualizer() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [apiInfo, setApiInfo] = useState(null);
  
  // Dynamic state extracted from payload
  const [metrics, setMetrics] = useState([]);
  const [tableData, setTableData] = useState([]);
  const [tableHeaders, setTableHeaders] = useState([]);
  const [chartData, setChartData] = useState([]); // Array of { name, value }
  
  // Search & pagination state
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const loadData = () => {
    setLoading(true);
    fetch(`/api/settings/incoming-apis/${id}/data`)
      .then(r => {
        if (!r.ok) throw new Error("Gagal mengambil data dari backend");
        return r.json();
      })
      .then(res => {
        setApiInfo({
          name: res.name,
          external_url: res.external_url,
          last_fetched: res.last_fetched,
          metabase_url: res.metabase_url
        });
        
        parsePayload(res.data);
        setError(null);
      })
      .catch(err => {
        console.error(err);
        setError(err.message);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [id]);

  // Dynamic Schema & Value Parser (The Auto-Visualizer Heart)
  const parsePayload = (payload) => {
    if (!payload || Object.keys(payload).length === 0) {
      setMetrics([]);
      setTableData([]);
      setTableHeaders([]);
      setChartData([]);
      return;
    }

    const detectedMetricsMap = {};
    let detectedList = [];
    
    // 1. Recursive finder to extract single key-value metric pairs
    const extractMetrics = (obj, prefix = '') => {
      if (typeof obj !== 'object' || obj === null) return;
      
      // Stop recursion if it looks like a list
      if (Array.isArray(obj)) return;

      for (const [key, val] of Object.entries(obj)) {
        const lowerKey = key.toLowerCase();
        
        // Skip metadata keys: timestamps, coordinates, fips, ids, rates, status codes
        if (
          lowerKey.includes('timestamp') ||
          lowerKey.includes('time') ||
          lowerKey.includes('date') ||
          lowerKey.includes('expire') ||
          lowerKey.includes('id') ||
          lowerKey.includes('lat') ||
          lowerKey.includes('long') ||
          lowerKey.includes('lng') ||
          lowerKey.includes('fips') ||
          lowerKey.includes('uid') ||
          lowerKey.includes('code') ||
          lowerKey.includes('status') ||
          lowerKey.includes('ratio') ||
          lowerKey.includes('rate') ||
          lowerKey.includes('percent')
        ) {
          continue;
        }

        let numVal = null;
        if (typeof val === 'number') {
          numVal = val;
        } else if (typeof val === 'string' && !isNaN(val) && val.trim() !== '') {
          numVal = Number(val);
        }

        if (numVal !== null) {
          const labelName = key.replace(/_/g, ' ').toUpperCase();
          // Keep only the highest value to capture global aggregates over subset zeros
          if (detectedMetricsMap[labelName] === undefined || numVal > detectedMetricsMap[labelName]) {
            detectedMetricsMap[labelName] = numVal;
          }
        } else if (typeof val === 'object' && val !== null) {
          extractMetrics(val, prefix);
        }
      }
    };

    extractMetrics(payload);
    
    const detectedMetrics = Object.entries(detectedMetricsMap).map(([label, value]) => ({
      label,
      value
    }));
    setMetrics(detectedMetrics.slice(0, 8)); // Limit to first 8 high-level counters

    // 2. Discover tabular array list inside payload
    if (Array.isArray(payload)) {
      detectedList = payload;
    } else {
      // Look for arrays inside object properties (e.g. rawData, records, data)
      for (const [key, val] of Object.entries(payload)) {
        if (Array.isArray(val)) {
          detectedList = val;
          break;
        }
      }
    }

    if (detectedList.length > 0) {
      setTableData(detectedList);
      
      // Extract columns
      const firstRow = detectedList[0];
      const headers = Object.keys(firstRow).filter(k => typeof firstRow[k] !== 'object');
      setTableHeaders(headers);

      // 3. Auto-chart generator (Categorical distributions)
      // Prioritize country/region/name over sub-province/states
      let categoryKey = headers.find(h => {
        const k = h.toLowerCase();
        return k.includes('country') || k.includes('region') || k.includes('name') || k.includes('label');
      });
      if (!categoryKey) {
        categoryKey = headers.find(h => {
          const k = h.toLowerCase();
          return k.includes('province') || k.includes('state');
        });
      }

      let valueKey = headers.find(h => {
        const k = h.toLowerCase();
        return (k.includes('confirmed') || k.includes('cases') || k.includes('active') || k.includes('nilai') || k.includes('amount') || k.includes('count') || k.includes('total')) && !k.includes('rate') && !k.includes('ratio');
      });

      // Fallback keys if not found explicitly
      if (!categoryKey) {
        categoryKey = headers.find(h => typeof firstRow[h] === 'string');
      }
      if (!valueKey) {
        valueKey = headers.find(h => {
          const val = firstRow[h];
          return typeof val === 'number' || (typeof val === 'string' && !isNaN(val) && val.trim() !== '');
        });
      }

      if (categoryKey && valueKey) {
        // Group and aggregate top values
        const groups = {};
        detectedList.forEach(item => {
          const cat = item[categoryKey] || 'Unknown';
          let rawVal = item[valueKey];
          let val = 0;
          if (typeof rawVal === 'number') {
            val = rawVal;
          } else if (typeof rawVal === 'string') {
            val = Number(rawVal.replace(/,/g, '')) || 0; // Strip formatting commas
          }
          groups[cat] = (groups[cat] || 0) + val;
        });

        const sortedChartData = Object.entries(groups)
          .map(([name, value]) => ({ name, value }))
          .filter(item => item.name.trim() !== '' && item.name !== 'Unknown')
          .sort((a, b) => b.value - a.value)
          .slice(0, 10); // Take top 10 categories
        
        setChartData(sortedChartData);
      }
    } else {
      setTableData([]);
      setTableHeaders([]);
      setChartData([]);
    }
  };

  // Sync manual fetch handler
  const handleSync = () => {
    setSyncing(true);
    fetch(`/api/settings/incoming-apis/${id}/fetch`, { method: 'POST' })
      .then(r => {
        if (!r.ok) throw new Error("Sinkronisasi gagal");
        return r.json();
      })
      .then(() => {
        loadData();
      })
      .catch(err => {
        alert("Gagal memperbarui data: " + err.message);
      })
      .finally(() => setSyncing(false));
  };

  // Filtering search query
  const filteredData = tableData.filter(row => {
    return tableHeaders.some(header => {
      const cellVal = String(row[header] || '').toLowerCase();
      return cellVal.includes(searchQuery.toLowerCase());
    });
  });

  // Pagination logic
  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const paginatedData = filteredData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  if (loading) {
    return (
      <div className="status-grid" style={{ height: 'calc(100vh - 120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="spinner" style={{ margin: '0 auto 15px auto', width: '40px', height: '40px', border: '3px solid rgba(var(--primary-rgb), 0.1)', borderTopColor: 'var(--primary)', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }}></div>
          <p style={{ color: 'var(--text-secondary)' }}>Menganalisis skema API & Mengolah grafik…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="status-grid" style={{ height: 'calc(100vh - 120px)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div className="status-card" style={{ maxWidth: '400px', textAlign: 'center', border: '1px solid rgba(239, 68, 68, 0.2)' }}>
          <div style={{ color: '#ef4444', fontSize: '32px', marginBottom: '10px' }}>⚠️</div>
          <h3 style={{ margin: '0 0 10px 0', color: 'var(--text)' }}>API Visualizer Gagal</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px' }}>{error}</p>
          <button className="btn" onClick={() => navigate('/superadmin')}>Kembali ke Superadmin</button>
        </div>
      </div>
    );
  }

  // Max value calculation for bar scaling
  const maxChartVal = chartData.reduce((max, item) => item.value > max ? item.value : max, 0) || 1;

  if (apiInfo?.metabase_url) {
    return (
      <div className="metabase-wrap" style={{ height: '100%', width: '100%', minHeight: 'calc(100vh - 120px)' }}>
        <iframe src={apiInfo.metabase_url} title={apiInfo.name} style={{ width: '100%', height: '100%', border: 'none' }} />
      </div>
    );
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      gap: '24px', 
      padding: '24px', 
      height: 'calc(100vh - var(--topbar-height))', 
      overflowY: 'auto', 
      animation: 'fadeIn 0.3s ease-out' 
    }}>
      
      {/* Upper Info Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: '12px', padding: '16px 24px', backdropFilter: 'blur(8px)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: '0 0 8px #10b981' }}></span>
            <span style={{ fontSize: '13px', fontWeight: '500', color: 'var(--primary)', letterSpacing: '0.05em' }}>AUTO-VISUALIZATION ACTIVE</span>
          </div>
          <h2 style={{ margin: '4px 0', fontSize: '20px', fontWeight: '600', color: 'var(--text)' }}>{apiInfo?.name}</h2>
          {apiInfo?.external_url && (
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-secondary)', fontFamily: 'monospace', wordBreak: 'break-all' }}>
              Source: {apiInfo.external_url}
            </p>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {apiInfo?.last_fetched && (
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Terakhir Diperbarui</div>
              <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text)' }}>
                {apiInfo.last_fetched.split('.')[0]}
              </div>
            </div>
          )}
          {apiInfo?.external_url && (
            <button 
              className={`btn${syncing ? ' disabled' : ''}`} 
              onClick={handleSync}
              disabled={syncing}
              style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              {syncing ? 'Menyinkronkan…' : 'Sinkronkan Sekarang'}
            </button>
          )}
        </div>
      </div>

      {/* Dynamic Metric Cards */}
      {metrics.length > 0 && (
        <div>
          <h3 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text)', marginBottom: '14px', letterSpacing: '0.02em' }}>
            METRIK KUNCI (AUTO-DETECTED)
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '16px' }}>
            {metrics.map((m, idx) => (
              <div 
                key={idx} 
                className="card" 
                style={{ 
                  padding: '20px', 
                  border: '1px solid var(--border)', 
                  position: 'relative', 
                  overflow: 'hidden',
                  background: 'linear-gradient(135deg, var(--card-bg), rgba(var(--primary-rgb), 0.02))'
                }}
              >
                <div style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: '8px' }}>
                  {m.label}
                </div>
                <div style={{ fontSize: '26px', fontWeight: '700', color: 'var(--text)', fontFamily: 'system-ui' }}>
                  {m.value.toLocaleString('id-ID')}
                </div>
                <div style={{ 
                  position: 'absolute', 
                  bottom: '-10px', 
                  right: '-10px', 
                  fontSize: '60px', 
                  fontWeight: '900', 
                  color: 'var(--primary)',
                  opacity: 0.04, 
                  userSelect: 'none',
                  pointerEvents: 'none'
                }}>
                  {idx + 1}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Auto Charts Panel */}
      {chartData.length > 0 && (
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '24px' }}>
          
          {/* Bar Chart Panel */}
          <div className="card" style={{ padding: '24px', border: '1px solid var(--border)' }}>
            <h3 style={{ margin: '0 0 20px 0', fontSize: '15px', fontWeight: '600', color: 'var(--text)' }}>
              DISTRIBUSI DISTRIBUTIF TERBESAR (TOP 10)
            </h3>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {chartData.map((item, idx) => {
                const percent = (item.value / maxChartVal) * 100;
                return (
                  <div key={idx} style={{ display: 'grid', gridTemplateColumns: '180px 1fr 100px', alignItems: 'center', gap: '16px' }}>
                    <div style={{ fontSize: '13px', color: 'var(--text)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', fontWeight: '500' }}>
                      {item.name}
                    </div>
                    <div style={{ height: '14px', background: 'rgba(var(--primary-rgb), 0.05)', borderRadius: '99px', overflow: 'hidden' }}>
                      <div 
                        style={{ 
                          height: '100%', 
                          width: `${percent}%`, 
                          background: 'linear-gradient(90deg, var(--primary), rgba(var(--primary-rgb), 0.6))',
                          borderRadius: '99px',
                          boxShadow: '0 0 10px rgba(var(--primary-rgb), 0.2)',
                          transition: 'width 1s cubic-bezier(0.1, 0.8, 0.2, 1)'
                        }}
                      ></div>
                    </div>
                    <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text)', textAlign: 'right', fontFamily: 'monospace' }}>
                      {item.value.toLocaleString('id-ID')}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Mini Donuts / Insights Card */}
          <div className="card" style={{ padding: '24px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <h3 style={{ margin: '0 0 16px 0', fontSize: '15px', fontWeight: '600', color: 'var(--text)' }}>
                INFORMASI SKEMA API
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', padding: '12px 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Format Response:</span>
                  <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text)', fontFamily: 'monospace' }}>JSON Payload</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Deteksi Array:</span>
                  <span style={{ fontSize: '13px', fontWeight: '600', color: '#10b981' }}>Tersedia ({tableData.length} baris)</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
                  <span style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Deteksi Grafik:</span>
                  <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--primary)' }}>Auto-Generated</span>
                </div>
              </div>
            </div>
            
            <div style={{ background: 'rgba(var(--primary-rgb), 0.02)', border: '1px dashed var(--primary)', borderRadius: '8px', padding: '14px', marginTop: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--primary)', marginBottom: '4px' }}>🛡️ Integrasi Pintar</div>
              <p style={{ margin: 0, fontSize: '11px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>
                Data ini diproses dan divisualisasikan secara dinamis menggunakan DARSI Native Analytics Engine. Grafik, metrik, dan tabel dihasilkan secara dinamis tanpa perlu Metabase.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Grid Table Data */}
      {tableData.length > 0 && (
        <div className="card" style={{ padding: '24px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: '600', color: 'var(--text)' }}>
              DATA INGESTION GRID ({filteredData.length} records)
            </h3>
            
            <input 
              type="text" 
              className="input-field" 
              placeholder="Cari dalam tabel data…" 
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
              style={{ maxWidth: '280px', padding: '8px 12px', fontSize: '13px', borderRadius: '8px' }}
            />
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ width: '100%', minWidth: '600px', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  {tableHeaders.map((header) => (
                    <th key={header} style={{ textAlign: 'left', padding: '12px 16px', fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                      {header.replace(/_/g, ' ')}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {paginatedData.length > 0 ? (
                  paginatedData.map((row, idx) => (
                    <tr 
                      key={idx} 
                      style={{ 
                        borderBottom: '1px solid var(--border)',
                        background: idx % 2 === 1 ? 'rgba(var(--primary-rgb), 0.01)' : 'transparent',
                        transition: 'background 0.2s'
                      }}
                    >
                      {tableHeaders.map((header) => {
                        const cell = row[header];
                        return (
                          <td key={header} style={{ padding: '12px 16px', fontSize: '13px', color: 'var(--text)' }}>
                            {typeof cell === 'number' ? cell.toLocaleString('id-ID') : String(cell || '-')}
                          </td>
                        );
                      })}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={tableHeaders.length} style={{ textAlign: 'center', padding: '30px', color: 'var(--text-secondary)' }}>
                      Tidak ada data yang cocok dengan kriteria pencarian Anda.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Table Pagination footer */}
          {totalPages > 1 && (
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '20px', borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Menampilkan {Math.min(filteredData.length, (currentPage - 1) * itemsPerPage + 1)}-
                {Math.min(filteredData.length, currentPage * itemsPerPage)} dari {filteredData.length} records
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  className={`btn${currentPage === 1 ? ' disabled' : ''}`}
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  style={{ padding: '6px 12px', fontSize: '12px' }}
                >
                  Sebelumnya
                </button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px', color: 'var(--text)', fontWeight: '500' }}>
                  Halaman {currentPage} dari {totalPages}
                </div>
                <button 
                  className={`btn${currentPage === totalPages ? ' disabled' : ''}`}
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  style={{ padding: '6px 12px', fontSize: '12px' }}
                >
                  Selanjutnya
                </button>
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
