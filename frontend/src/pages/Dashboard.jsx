import { Bar, Doughnut } from 'react-chartjs-2';
import { useApi } from '../api';
import { PALETTE, fmtNum, fmtRp, fmtPct } from '../utils';

function KpiCard({ label, value, sub, color }) {
  return (
    <div className="kpi-card" style={{ '--card-accent': color }}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

function ChartCard({ title, className, children }) {
  return (
    <div className={`chart-card${className ? ' ' + className : ''}`}>
      <div className="chart-title">{title}</div>
      <div className="chart-wrap">{children}</div>
    </div>
  );
}

function EmptyChart({ msg = 'Data tidak tersedia — pastikan pipeline sudah berjalan' }) {
  return (
    <div className="empty-state">
      <span>⚠</span>
      <span>{msg}</span>
    </div>
  );
}

const BAR_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: true, labels: { font: { size: 11 }, padding: 10 } } },
  scales: {
    x: { grid: { display: false }, ticks: { font: { size: 11 } } },
    y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } } },
  },
};

const STACKED_OPTS = {
  ...BAR_OPTS,
  scales: {
    x: { stacked: true, grid: { display: false }, ticks: { font: { size: 11 } } },
    y: { stacked: true, grid: { color: '#f1f5f9' }, ticks: { font: { size: 11 } } },
  },
};

export default function Dashboard() {
  const { data: overview, loading: l1 } = useApi('/api/analytics/overview');
  const { data: costData, loading: l2 } = useApi('/api/analytics/cost-by-category');
  const { data: occData, loading: l3 } = useApi('/api/analytics/occupancy-by-unit');
  const { data: utilData, loading: l4 } = useApi('/api/analytics/utility-trend');

  if (l1 || l2 || l3 || l4) {
    return (
      <div className="loader">
        <div className="spinner" />
        <p>Memuat data operasional…</p>
      </div>
    );
  }

  const kpi = overview?.kpi ?? {};

  const kpiCards = [
    { label: 'Pasien Aktif', value: fmtNum(kpi.pasien_aktif), color: '#2563eb' },
    {
      label: 'BOR (Tingkat Hunian)',
      value: fmtPct(kpi.bor_pct),
      sub: `${fmtNum(kpi.bed_occupied)} / ${fmtNum(kpi.bed_capacity)} bed`,
      color: '#0694a2',
    },
    {
      label: 'Total Biaya',
      value: fmtRp(kpi.total_cost_idr),
      sub: `${fmtPct(kpi.budget_usage_pct)} dari anggaran`,
      color: '#7c3aed',
    },
    { label: 'Konsumsi Listrik', value: `${fmtNum(kpi.kwh_total, 1)} kWh`, color: '#d97706' },
    { label: 'Konsumsi Air', value: `${fmtNum(kpi.air_m3_total, 1)} m³`, color: '#059669' },
    {
      label: 'Lembur Staf',
      value: `${fmtNum(kpi.overtime_hours, 1)} jam`,
      sub: fmtRp(kpi.overtime_cost_idr),
      color: '#dc2626',
    },
  ];

  // Cost doughnut
  const costCategories = costData?.categories ?? [];
  const costChartData = {
    labels: costCategories.map(c => c.cost_category),
    datasets: [{
      data: costCategories.map(c => c.total_cost),
      backgroundColor: PALETTE,
      borderWidth: 0,
    }],
  };

  // Occupancy stacked bar
  const occUnits = occData?.units ?? [];
  const occChartData = {
    labels: occUnits.map(u => u.unit_code),
    datasets: [
      {
        label: 'Terisi',
        data: occUnits.map(u => u.occupied ?? 0),
        backgroundColor: '#2563eb',
        borderRadius: 4,
      },
      {
        label: 'Kosong',
        data: occUnits.map(u => Math.max(0, (u.capacity ?? 0) - (u.occupied ?? 0))),
        backgroundColor: '#e2e8f0',
        borderRadius: 4,
      },
    ],
  };

  // Utility grouped bar
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
      <div className="kpi-grid">
        {kpiCards.map(c => <KpiCard key={c.label} {...c} />)}
      </div>

      <div className="chart-grid">
        <ChartCard title="Biaya Operasional per Kategori">
          {costCategories.length > 0
            ? (
              <Doughnut
                data={costChartData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  cutout: '65%',
                  plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10 } } },
                }}
              />
            )
            : <EmptyChart />}
        </ChartCard>

        <ChartCard title="Okupansi Bed per Unit">
          {occUnits.length > 0
            ? <Bar data={occChartData} options={STACKED_OPTS} />
            : <EmptyChart />}
        </ChartCard>

        <ChartCard title="Konsumsi Utilitas per Unit" className="full">
          {utilUnits.length > 0
            ? <Bar data={utilChartData} options={BAR_OPTS} />
            : <EmptyChart />}
        </ChartCard>
      </div>
    </div>
  );
}
