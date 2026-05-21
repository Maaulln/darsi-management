import { useState, useMemo } from 'react';
import { Bar, Doughnut } from 'react-chartjs-2';
import { useApi } from '../api';
import { PALETTE, fmtNum, fmtRp, fmtPct } from '../utils';

// ── Helpers ──────────────────────────────────────────────────────────────────

const MONTHS_ID = ['Januari','Februari','Maret','April','Mei','Juni',
                   'Juli','Agustus','September','Oktober','November','Desember'];
const DAYS_ID   = ['Min','Sen','Sel','Rab','Kam','Jum','Sab'];

function padDate(n) { return String(n).padStart(2, '0'); }

function modeRange(mode, selDate) {
  const y = selDate.year, m = selDate.month, d = selDate.day;
  if (mode === 'hari') {
    const ds = `${y}-${padDate(m)}-${padDate(d)}`;
    return { date_from: ds, date_to: ds };
  }
  if (mode === 'bulan') {
    const lastDay = new Date(y, m, 0).getDate();
    return { date_from: `${y}-${padDate(m)}-01`, date_to: `${y}-${padDate(m)}-${lastDay}` };
  }
  // tahun
  return { date_from: `${y}-01-01`, date_to: `${y}-12-31` };
}

// ── Sub-components ────────────────────────────────────────────────────────────

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

// ── Calendar ─────────────────────────────────────────────────────────────────

function MiniCalendar({ year, month, selected, onSelect, dailyData }) {
  const dataMap = useMemo(() => {
    const m = {};
    (dailyData || []).forEach(d => { m[d.date] = d; });
    return m;
  }, [dailyData]);

  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const cells = [];

  for (let i = 0; i < firstDay; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const today = new Date();
  const isToday = (d) =>
    d === today.getDate() && month === today.getMonth() + 1 && year === today.getFullYear();
  const isSelected = (d) =>
    d === selected.day && month === selected.month && year === selected.year;

  return (
    <div className="cal-grid">
      {DAYS_ID.map(d => <div key={d} className="cal-head">{d}</div>)}
      {cells.map((d, i) => {
        if (!d) return <div key={`e${i}`} />;
        const dateStr = `${year}-${padDate(month)}-${padDate(d)}`;
        const info = dataMap[dateStr];
        const hasPasien = info?.pasien > 0;
        const hasLembur = info?.lembur_hours > 0;
        return (
          <div
            key={d}
            className={`cal-day${isSelected(d) ? ' sel' : ''}${isToday(d) ? ' today' : ''}`}
            onClick={() => onSelect(d)}
            title={info ? `Pasien: ${info.pasien} | Lembur: ${info.lembur_hours} jam` : ''}
          >
            <span>{d}</span>
            {(hasPasien || hasLembur) && (
              <div className="cal-dots">
                {hasPasien && <span className="cal-dot blue" />}
                {hasLembur && <span className="cal-dot red" />}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function CalendarWidget({ mode, selDate, onDateChange }) {
  const { year, month } = selDate;

  const prevMonth = () => {
    const d = new Date(year, month - 2, 1);
    onDateChange({ year: d.getFullYear(), month: d.getMonth() + 1, day: 1 });
  };
  const nextMonth = () => {
    const d = new Date(year, month, 1);
    onDateChange({ year: d.getFullYear(), month: d.getMonth() + 1, day: 1 });
  };

  const { data: trendData } = useApi('/api/analytics/daily-trend', { year, month });
  const days = trendData?.days ?? [];

  const years = [];
  const curYear = new Date().getFullYear();
  for (let y = curYear - 3; y <= curYear + 1; y++) years.push(y);

  return (
    <div className="cal-widget">
      <div className="cal-nav">
        <button className="cal-nav-btn" onClick={prevMonth}>‹</button>
        <div className="cal-nav-title">
          <select
            value={month}
            onChange={e => onDateChange({ ...selDate, month: Number(e.target.value), day: 1 })}
          >
            {MONTHS_ID.map((m, i) => <option key={i} value={i + 1}>{m}</option>)}
          </select>
          <select
            value={year}
            onChange={e => onDateChange({ ...selDate, year: Number(e.target.value), day: 1 })}
          >
            {years.map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
        <button className="cal-nav-btn" onClick={nextMonth}>›</button>
      </div>

      <MiniCalendar
        year={year}
        month={month}
        selected={selDate}
        onSelect={d => onDateChange({ ...selDate, day: d })}
        dailyData={days}
      />

      {days.length > 0 && (
        <div className="cal-legend">
          <span><span className="cal-dot blue" /> Pasien aktif</span>
          <span><span className="cal-dot red" /> Ada lembur</span>
        </div>
      )}
    </div>
  );
}

// ── Filter Bar ────────────────────────────────────────────────────────────────

function FilterBar({ mode, setMode, selDate, onDateChange }) {
  const { year, month, day } = selDate;
  const today = new Date();

  return (
    <div className="dash-filter-bar">
      <div className="dash-filter-tabs">
        {['hari', 'bulan', 'tahun'].map(m => (
          <button
            key={m}
            className={`dash-tab${mode === m ? ' active' : ''}`}
            onClick={() => setMode(m)}
          >
            {m === 'hari' ? 'Per Hari' : m === 'bulan' ? 'Per Bulan' : 'Per Tahun'}
          </button>
        ))}
      </div>

      <div className="dash-filter-inputs">
        {mode === 'hari' && (
          <input
            type="date"
            className="dash-date-input"
            value={`${year}-${padDate(month)}-${padDate(day)}`}
            max={`${today.getFullYear()}-${padDate(today.getMonth()+1)}-${padDate(today.getDate())}`}
            onChange={e => {
              const [y, m, d] = e.target.value.split('-').map(Number);
              if (y && m && d) onDateChange({ year: y, month: m, day: d });
            }}
          />
        )}
        {mode === 'bulan' && (
          <input
            type="month"
            className="dash-date-input"
            value={`${year}-${padDate(month)}`}
            max={`${today.getFullYear()}-${padDate(today.getMonth()+1)}`}
            onChange={e => {
              const [y, m] = e.target.value.split('-').map(Number);
              if (y && m) onDateChange({ year: y, month: m, day: 1 });
            }}
          />
        )}
        {mode === 'tahun' && (
          <select
            className="dash-date-input"
            value={year}
            onChange={e => onDateChange({ ...selDate, year: Number(e.target.value) })}
          >
            {[today.getFullYear()-3, today.getFullYear()-2, today.getFullYear()-1, today.getFullYear()]
              .map(y => <option key={y} value={y}>{y}</option>)}
          </select>
        )}

        <span className="dash-filter-label">
          {mode === 'hari'
            ? `${day} ${MONTHS_ID[month-1]} ${year}`
            : mode === 'bulan'
            ? `${MONTHS_ID[month-1]} ${year}`
            : `Tahun ${year}`}
        </span>

        <button
          className="dash-today-btn"
          onClick={() => onDateChange({ year: today.getFullYear(), month: today.getMonth()+1, day: today.getDate() })}
        >
          Hari Ini
        </button>
      </div>
    </div>
  );
}

// ── Chart options ─────────────────────────────────────────────────────────────

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

const DOUGHNUT_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, padding: 10 } } },
};

// ── Main Dashboard ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const today = new Date();
  const [mode, setMode] = useState('bulan');
  const [selDate, setSelDate] = useState({
    year: today.getFullYear(),
    month: today.getMonth() + 1,
    day: today.getDate(),
  });

  const range = useMemo(() => modeRange(mode, selDate), [mode, selDate]);
  const params = useMemo(
    () => ({ date_from: range.date_from, date_to: range.date_to }),
    [range.date_from, range.date_to],
  );

  // Satu request untuk semua data dashboard — 6 analytics diambil paralel di backend
  const { data: dashData, loading, error: e1 } = useApi('/api/analytics/dashboard', params);

  const overview  = dashData?.overview;
  const costData  = dashData?.cost_by_category;
  const occData   = dashData?.occupancy_by_unit;
  const utilData  = dashData?.utility_trend;
  const effData   = dashData?.efficiency;
  const staffData = dashData?.staffing;

  const kpi = overview?.kpi ?? {};

  const effUnits   = useMemo(() => effData?.units ?? [],   [effData]);
  const staffUnits = useMemo(() => staffData?.units ?? [], [staffData]);

  const avgCostToRevenue = useMemo(() => {
    if (!effUnits.length) return null;
    const valid = effUnits.filter(u => u.cost_to_revenue_pct != null);
    return valid.length
      ? valid.reduce((s, u) => s + u.cost_to_revenue_pct, 0) / valid.length
      : null;
  }, [effUnits]);

  const avgOvertimeRatio = useMemo(() => {
    if (!staffUnits.length) return null;
    const valid = staffUnits.filter(u => u.overtime_ratio_pct != null);
    return valid.length
      ? valid.reduce((s, u) => s + u.overtime_ratio_pct, 0) / valid.length
      : null;
  }, [staffUnits]);

  const kpiCards = useMemo(() => [
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
    {
      label: 'Cost-to-Revenue Ratio',
      value: avgCostToRevenue != null ? fmtPct(avgCostToRevenue) : '—',
      sub: 'Rata-rata biaya vs pendapatan per unit',
      color: avgCostToRevenue > 100 ? '#dc2626' : '#16a34a',
    },
    {
      label: 'Overtime Ratio',
      value: avgOvertimeRatio != null ? fmtPct(avgOvertimeRatio) : '—',
      sub: 'Rata-rata lembur vs jam kerja reguler',
      color: avgOvertimeRatio > 20 ? '#d97706' : '#059669',
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [kpi.pasien_aktif, kpi.bor_pct, kpi.bed_occupied, kpi.bed_capacity,
      kpi.total_cost_idr, kpi.budget_usage_pct, kpi.kwh_total, kpi.air_m3_total,
      kpi.overtime_hours, kpi.overtime_cost_idr, avgCostToRevenue, avgOvertimeRatio]);

  // Cost doughnut
  const costCategories = useMemo(() => costData?.categories ?? [], [costData]);
  const costChartData = useMemo(() => ({
    labels: costCategories.map(c => c.cost_category),
    datasets: [{
      data: costCategories.map(c => c.total_cost),
      backgroundColor: PALETTE,
      borderWidth: 0,
    }],
  }), [costCategories]);

  // Occupancy stacked bar
  const occUnits = useMemo(() => occData?.units ?? [], [occData]);
  const occChartData = useMemo(() => ({
    labels: occUnits.map(u => u.unit_code),
    datasets: [
      { label: 'Terisi', data: occUnits.map(u => u.occupied ?? 0), backgroundColor: '#2563eb', borderRadius: 4 },
      { label: 'Kosong', data: occUnits.map(u => Math.max(0, (u.capacity ?? 0) - (u.occupied ?? 0))), backgroundColor: '#e2e8f0', borderRadius: 4 },
    ],
  }), [occUnits]);

  // Utility grouped bar
  const utilChartData = useMemo(() => {
    const listrik = utilData?.listrik ?? [];
    const air = utilData?.air ?? [];
    const utilUnits = [...new Set([...listrik.map(u => u.unit_code), ...air.map(u => u.unit_code)])];
    return {
      labels: utilUnits,
      datasets: [
        { label: 'Listrik (kWh)', data: utilUnits.map(u => listrik.find(l => l.unit_code === u)?.kwh ?? 0), backgroundColor: '#d97706', borderRadius: 3 },
        { label: 'Air (m³)', data: utilUnits.map(u => air.find(a => a.unit_code === u)?.volume ?? 0), backgroundColor: '#0694a2', borderRadius: 3 },
      ],
    };
  }, [utilData]);

  const utilUnits = utilChartData.labels;

  // Cost-to-Revenue bar
  const effChartData = useMemo(() => ({
    labels: effUnits.map(u => u.unit_code),
    datasets: [{
      label: 'Cost-to-Revenue (%)',
      data: effUnits.map(u => u.cost_to_revenue_pct ?? 0),
      backgroundColor: effUnits.map(u => (u.cost_to_revenue_pct ?? 0) > 100 ? '#dc2626' : '#16a34a'),
      borderRadius: 4,
    }],
  }), [effUnits]);

  // Staffing grouped bar
  const staffChartData = useMemo(() => ({
    labels: staffUnits.map(u => u.unit_code),
    datasets: [
      { label: 'Jam Reguler', data: staffUnits.map(u => u.actual_hours ?? 0), backgroundColor: '#2563eb', borderRadius: 3 },
      { label: 'Jam Lembur', data: staffUnits.map(u => u.overtime_hours ?? 0), backgroundColor: '#dc2626', borderRadius: 3 },
    ],
  }), [staffUnits]);

  const hasAnyData = kpi.pasien_aktif != null || costCategories.length > 0 || occUnits.length > 0;

  return (
    <div>
      <FilterBar mode={mode} setMode={setMode} selDate={selDate} onDateChange={setSelDate} />

      <div className="dash-body">
        {/* Kolom kalender */}
        <div className="dash-sidebar-cal">
          <CalendarWidget mode={mode} selDate={selDate} onDateChange={setSelDate} />
        </div>

        {/* Konten utama */}
        <div className="dash-main-content">
          {loading && (
            <div className="loader">
              <div className="spinner" />
              <p>Memuat data operasional…</p>
            </div>
          )}

          {!loading && e1 && (
            <div className="error-box">Gagal memuat data: {e1}</div>
          )}

          {!loading && !hasAnyData && !e1 && (
            <div className="dash-no-data">
              <div className="dash-no-data-icon">📭</div>
              <div className="dash-no-data-title">Tidak ada data untuk periode ini</div>
              <div className="dash-no-data-sub">Coba pilih periode lain atau pastikan pipeline sudah berjalan.</div>
            </div>
          )}

          {!loading && hasAnyData && (
            <>
              <div className="kpi-grid">
                {kpiCards.map(c => <KpiCard key={c.label} {...c} />)}
              </div>

              <div className="chart-grid">
                <ChartCard title="Biaya Operasional per Kategori">
                  {costCategories.length > 0
                    ? <Doughnut data={costChartData} options={DOUGHNUT_OPTS} />
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

                <ChartCard title="Cost-to-Revenue Ratio per Unit" className="full">
                  {effUnits.length > 0
                    ? <Bar data={effChartData} options={BAR_OPTS} />
                    : <EmptyChart />}
                </ChartCard>

                <ChartCard title="Jam Kerja vs Lembur per Unit" className="full">
                  {staffUnits.length > 0
                    ? <Bar data={staffChartData} options={STACKED_OPTS} />
                    : <EmptyChart />}
                </ChartCard>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
