import { Bar, Doughnut } from 'react-chartjs-2';
import { useApi } from '../api';
import { PALETTE, fmtNum, fmtRp, fmtPct, budgetColor } from '../utils';

const CHART_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: true, labels: { font: { size: 11 }, padding: 10 } } },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 11 } } },
    y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } } },
  },
};

export default function Analytics() {
  const { data: costData, loading: l1, error: e1 } = useApi('/api/analytics/cost-by-category');
  const { data: occData, loading: l2, error: e2 } = useApi('/api/analytics/occupancy-by-unit');
  const { data: utilData, loading: l3 } = useApi('/api/analytics/utility-trend');
  const { data: mcpData, loading: l4 } = useApi('/api/analytics/mcp-status');

  if (l1 || l2 || l3 || l4) {
    return <div className="loader"><div className="spinner" /><p>Memuat data analitik…</p></div>;
  }

  const domains = mcpData?.domains ?? [];

  // Cost chart
  const cats = costData?.categories ?? [];
  const costChartData = {
    labels: cats.map(c => c.cost_category),
    datasets: [{
      data: cats.map(c => c.total_cost),
      backgroundColor: PALETTE,
      borderWidth: 0,
    }],
  };

  // Occupancy chart
  const units = occData?.units ?? [];
  const occChartData = {
    labels: units.map(u => u.unit_code),
    datasets: [
      {
        label: 'Terisi',
        data: units.map(u => u.occupied ?? 0),
        backgroundColor: '#2563eb',
        borderRadius: 4,
      },
      {
        label: 'Kosong',
        data: units.map(u => Math.max(0, (u.capacity ?? 0) - (u.occupied ?? 0))),
        backgroundColor: '#e2e8f0',
        borderRadius: 4,
      },
    ],
  };

  const listrik = utilData?.listrik ?? [];
  const air = utilData?.air ?? [];
  const utilUnits = [...new Set([...listrik.map(u => u.unit_code), ...air.map(u => u.unit_code)])];
  const utilChartData = {
    labels: utilUnits,
    datasets: [
      {
        label: 'Listrik (kWh)',
        data: utilUnits.map(u => listrik.find(l => l.unit_code === u)?.kwh ?? 0),
        backgroundColor: '#d97706',
        borderRadius: 3,
      },
      {
        label: 'Air (m³)',
        data: utilUnits.map(u => air.find(a => a.unit_code === u)?.volume ?? 0),
        backgroundColor: '#0694a2',
        borderRadius: 3,
      },
    ],
  };

  return (
    <div>
      {/* Domain list */}
      {domains.length > 0 && (
        <div className="chart-card mb-16">
          <div className="chart-title">Domain Data Tersedia (MCP Server)</div>
          <div className="gap-tags">
            {domains.map(d => (
              <span key={d.name} className="tag tag-purple" title={d.keywords?.join(', ')}>
                {d.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="chart-grid">
        <div className="chart-card">
          <div className="chart-title">Biaya Operasional per Kategori</div>
          <div className="chart-wrap">
            {cats.length > 0
              ? (
                <Doughnut
                  data={costChartData}
                  options={{ responsive: true, maintainAspectRatio: false, cutout: '60%', plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10 } } } }}
                />
              )
              : <div className="empty-state"><span>⚠</span><span>Data tidak tersedia</span></div>}
          </div>
        </div>

        <div className="chart-card">
          <div className="chart-title">Okupansi Bed per Unit</div>
          <div className="chart-wrap">
            {units.length > 0
              ? (
                <Bar
                  data={occChartData}
                  options={{ ...CHART_OPTS, scales: { x: { stacked: true, grid: { display: false }, ticks: { font: { size: 11 } } }, y: { stacked: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } } } } }}
                />
              )
              : <div className="empty-state"><span>⚠</span><span>Data tidak tersedia</span></div>}
          </div>
        </div>

        <div className="chart-card full">
          <div className="chart-title">Konsumsi Utilitas per Unit</div>
          <div className="chart-wrap">
            {utilUnits.length > 0
              ? <Bar data={utilChartData} options={CHART_OPTS} />
              : <div className="empty-state"><span>⚠</span><span>Data tidak tersedia</span></div>}
          </div>
        </div>
      </div>

      {/* Cost breakdown table */}
      {cats.length > 0 && (
        <div className="chart-card mt-16">
          <div className="chart-title">Detail Biaya per Kategori</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Kategori</th>
                <th>Total Biaya</th>
                <th>Anggaran</th>
                <th>Realisasi</th>
                <th style={{ width: '160px' }}>Progress</th>
              </tr>
            </thead>
            <tbody>
              {cats.map(c => {
                const pct = c.total_budget > 0 ? (c.total_cost / c.total_budget) * 100 : 0;
                return (
                  <tr key={c.cost_category}>
                    <td><strong>{c.cost_category}</strong></td>
                    <td>{fmtRp(c.total_cost)}</td>
                    <td>{fmtRp(c.total_budget)}</td>
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
        </div>
      )}

      {/* Occupancy table */}
      {units.length > 0 && (
        <div className="chart-card mt-16">
          <div className="chart-title">Detail Okupansi per Unit</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Unit</th>
                <th>Terisi</th>
                <th>Kapasitas</th>
                <th>BOR</th>
                <th style={{ width: '160px' }}>Progress</th>
              </tr>
            </thead>
            <tbody>
              {units.map(u => {
                const pct = u.capacity > 0 ? (u.occupied / u.capacity) * 100 : 0;
                return (
                  <tr key={u.unit_code}>
                    <td><strong>{u.unit_code}</strong></td>
                    <td>{fmtNum(u.occupied)}</td>
                    <td>{fmtNum(u.capacity)}</td>
                    <td>{fmtPct(pct)}</td>
                    <td>
                      <div className="progress-bar">
                        <div
                          className="progress-fill"
                          style={{ width: `${Math.min(pct, 100)}%`, background: '#2563eb' }}
                        />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
