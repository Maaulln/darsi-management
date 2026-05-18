import { useApi } from '../api';
import { fmtNum, fmtRp, fmtPct, budgetColor } from '../utils';

function SectionCard({ title, children, onRefresh }) {
  return (
    <div className="chart-card">
      <div className="section-head">
        <div className="section-title">{title}</div>
        {onRefresh && (
          <button className="btn" onClick={onRefresh}>↻ Refresh</button>
        )}
      </div>
      {children}
    </div>
  );
}

export default function Summary() {
  const { data: resData, loading: l1, error: e1, refetch: r1 } = useApi('/api/summary/resource');
  const { data: costData, loading: l2, error: e2, refetch: r2 } = useApi('/api/summary/cost');

  return (
    <div>
      {/* Resource summary */}
      <SectionCard title="Ringkasan Utilitas & Sumber Daya per Unit" onRefresh={r1}>
        {l1 && <div className="loader" style={{ minHeight: 120 }}><div className="spinner" /></div>}
        {e1 && <div className="error-box">{e1}</div>}
        {!l1 && !e1 && (
          <>
            {(resData?.units?.length ?? 0) === 0
              ? <div className="empty-state"><span>⚠</span><span>Data belum tersedia — pipeline perlu dijalankan terlebih dahulu</span></div>
              : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Unit</th>
                      <th>Listrik (kWh)</th>
                      <th>Air (m³)</th>
                      <th>Bed Terisi</th>
                      <th>Kapasitas</th>
                      <th>BOR</th>
                      <th style={{ width: '120px' }}>Progress Hunian</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resData.units.map(u => {
                      const bor = u.bed_capacity > 0 ? (u.bed_occupied / u.bed_capacity) * 100 : 0;
                      return (
                        <tr key={u.unit_code}>
                          <td><strong>{u.unit_code}</strong></td>
                          <td>{fmtNum(u.listrik_kwh, 1)}</td>
                          <td>{fmtNum(u.air_m3, 2)}</td>
                          <td>{fmtNum(u.bed_occupied)}</td>
                          <td>{fmtNum(u.bed_capacity)}</td>
                          <td>{fmtPct(bor)}</td>
                          <td>
                            <div className="progress-bar">
                              <div
                                className="progress-fill"
                                style={{ width: `${Math.min(bor, 100)}%`, background: '#2563eb' }}
                              />
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
          </>
        )}
      </SectionCard>

      {/* Cost summary */}
      <div className="mt-16">
        <SectionCard title="Ringkasan Biaya Operasional per Unit" onRefresh={r2}>
          {l2 && <div className="loader" style={{ minHeight: 120 }}><div className="spinner" /></div>}
          {e2 && <div className="error-box">{e2}</div>}
          {!l2 && !e2 && (
            <>
              {(costData?.units?.length ?? 0) === 0
                ? <div className="empty-state"><span>⚠</span><span>Data belum tersedia — pipeline perlu dijalankan terlebih dahulu</span></div>
                : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Unit</th>
                        <th>Total Biaya</th>
                        <th>Anggaran</th>
                        <th>Sisa Anggaran</th>
                        <th>Realisasi</th>
                        <th style={{ width: '140px' }}>Progress</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costData.units.map(u => {
                        const pct = u.total_budget_idr > 0
                          ? (u.total_cost_idr / u.total_budget_idr) * 100
                          : 0;
                        const sisa = (u.total_budget_idr ?? 0) - (u.total_cost_idr ?? 0);
                        return (
                          <tr key={u.unit_code}>
                            <td><strong>{u.unit_code}</strong></td>
                            <td>{fmtRp(u.total_cost_idr)}</td>
                            <td>{fmtRp(u.total_budget_idr)}</td>
                            <td style={{ color: sisa < 0 ? '#dc2626' : '#059669' }}>
                              {fmtRp(Math.abs(sisa))}{sisa < 0 ? ' (over)' : ''}
                            </td>
                            <td>{fmtPct(pct)}</td>
                            <td>
                              <div className="progress-bar">
                                <div
                                  className="progress-fill"
                                  style={{ width: `${Math.min(pct, 100)}%`, background: budgetColor(pct) }}
                                />
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                )}
            </>
          )}
        </SectionCard>
      </div>

      {/* Info */}
      <div className="chart-card mt-16">
        <div className="chart-title">Catatan</div>
        <p style={{ fontSize: '12px', color: '#64748b', lineHeight: 1.8 }}>
          Data diperbarui setiap <strong>1 menit</strong> oleh pipeline n8n (refine → sync → embed).
          Semua angka bersifat <strong>advisory</strong> — validasi diperlukan sebelum digunakan
          sebagai dasar keputusan operasional.
        </p>
      </div>
    </div>
  );
}
