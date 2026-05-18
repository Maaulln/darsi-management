import { useApi } from '../api';
import { statusClass } from '../utils';

const STATUS_LABEL = {
  ok: 'Operasional',
  degraded: 'Degraded',
  down: 'Tidak dapat dijangkau',
  unknown: 'Tidak diketahui',
};

const SERVICES_INFO = [
  { name: 'nginx', port: '8080', desc: 'Reverse proxy — entry point utama' },
  { name: 'backend', port: '8000', desc: 'FastAPI REST API layer' },
  { name: 'mcp-server', port: '8100', desc: 'Data connector + SurrealDB vector RAG + LLM' },
  { name: 'pipeline-service', port: '8200', desc: 'Refine → Sync → Embed (dipanggil n8n)' },
  { name: 'ollama', port: '11434', desc: 'qwen3.5:2b (chat) + nomic-embed-text (embed)' },
  { name: 'surrealdb', port: '8001', desc: 'Clean data store + vector index HNSW' },
  { name: 'postgres', port: '5432', desc: 'Raw SIMRS data store (8 domain)' },
  { name: 'n8n', port: '5678', desc: 'Pipeline orchestration (cron 1 menit)' },
  { name: 'metabase', port: '3001', desc: 'Analytics dashboard (embedded)' },
  { name: 'simrs-simulator', port: '—', desc: 'Data simulator real-time (setiap 10 dtk)' },
];

function SvcCard({ name, statusVal, desc }) {
  const cls = statusClass(statusVal);
  return (
    <div className="svc-card">
      <div className={`svc-dot ${cls}`} />
      <div>
        <div className="svc-name">{name}</div>
        <div className={`svc-status-text ${cls}`}>{STATUS_LABEL[cls] ?? cls}</div>
        {desc && <div className="svc-desc">{desc}</div>}
      </div>
    </div>
  );
}

export default function StatusPage() {
  const { data: readiness, loading: l1, error: e1, refetch: r1 } = useApi('/api/readiness');
  const { data: mcpData, loading: l2 } = useApi('/api/analytics/mcp-status');

  const checkedAt = new Date().toLocaleString('id-ID', {
    weekday: 'short', year: 'numeric', month: 'short',
    day: 'numeric', hour: '2-digit', minute: '2-digit',
  });

  const domains = mcpData?.domains ?? [];
  const overall = readiness?.overall ?? (e1 ? 'down' : 'unknown');
  const overallCls = statusClass(overall);

  const svcEntries = readiness
    ? [
        ['FastAPI Backend', 'ok', 'Port 8000 — aktif (Anda sedang terhubung)'],
        ['MCP Server', readiness.mcp_server, 'Port 8100'],
        ['SurrealDB', readiness.surrealdb, 'Port 8001 — clean data + vector index HNSW'],
        ['Ollama', readiness.ollama, 'Port 11434 — LLM (qwen3.5:2b) + embed (nomic-embed-text)'],
      ]
    : [];

  return (
    <div>
      {/* Header */}
      <div className="status-header">
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: '#374151' }}>
            Status keseluruhan:{' '}
            <span className={`svc-status-text ${overallCls}`} style={{ fontSize: 13 }}>
              {overallCls === 'ok' ? '✓ Semua sistem operasional'
                : overallCls === 'down' ? '✗ Sistem tidak dapat dijangkau'
                : '⚠ Sistem degraded'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 12, color: '#94a3b8' }}>
            Dicek: {checkedAt}
          </span>
          <button className="btn" onClick={r1}>↻ Refresh</button>
        </div>
      </div>

      {/* Error */}
      {e1 && <div className="error-box">{e1}</div>}

      {/* Service cards */}
      {(l1 || l2)
        ? <div className="loader"><div className="spinner" /></div>
        : (
          <div className="svc-grid">
            {svcEntries.map(([name, val, desc]) => (
              <SvcCard key={name} name={name} statusVal={val} desc={desc} />
            ))}
          </div>
        )}

      {/* Domains */}
      {domains.length > 0 && (
        <div className="chart-card mb-16">
          <div className="chart-title">Domain Data Aktif (MCP Server)</div>
          <div className="gap-tags">
            {domains.map(d => (
              <span key={d.name} className="tag tag-purple" title={d.keywords?.join(', ')}>
                {d.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Services info table */}
      <div className="chart-card">
        <div className="chart-title">Daftar Layanan</div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Layanan</th>
              <th>Port</th>
              <th>Deskripsi</th>
            </tr>
          </thead>
          <tbody>
            {SERVICES_INFO.map(s => (
              <tr key={s.name}>
                <td><strong>{s.name}</strong></td>
                <td style={{ fontVariantNumeric: 'tabular-nums' }}>{s.port}</td>
                <td>{s.desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
