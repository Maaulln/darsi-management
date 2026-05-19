import { useState, useRef, useEffect } from 'react';
import { apiPost } from '../api';

const SUGGESTIONS = [
  'Berapa pasien aktif hari ini?',
  'Bagaimana tren konsumsi listrik per unit?',
  'Unit mana yang tingkat huniannya tertinggi?',
  'Rangkum biaya operasional secara keseluruhan',
];

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [activeModel, setActiveModel] = useState('Memuat...');
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    fetch('/api/settings/ai')
      .then(r => r.json())
      .then(data => {
        setActiveModel(data.model || 'qwen3.5:2b (Lokal)');
      })
      .catch(() => {
        setActiveModel('qwen3.5:2b (Lokal)');
      });
  }, []);

  const handleSend = async (text = input) => {
    const msg = text.trim();
    if (!msg || sending) return;

    setInput('');
    setSending(true);
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    setMessages(prev => [...prev, { role: 'user', content: msg }]);

    try {
      const res = await apiPost('/api/chat', { message: msg, use_rag: useRag });
      setMessages(prev => [
        ...prev,
        {
          role: 'ai',
          content: res.response || '(Tidak ada respons)',
          source: res.source,
          domains: res.matched_domains ?? [],
        },
      ]);
    } catch (e) {
      setMessages(prev => [
        ...prev,
        { role: 'ai', content: `Terjadi kesalahan: ${e.message}`, isError: true },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = (e) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
  };

  return (
    <div className="chat-layout">
      {/* Toolbar */}
      <div className="chat-toolbar">
        <span className="chat-toolbar-label">Mode:</span>
        <label className="toggle-wrap">
          <input
            type="checkbox"
            className="toggle"
            checked={useRag}
            onChange={e => setUseRag(e.target.checked)}
          />
          RAG (konteks data operasional)
        </label>
        <span style={{ marginLeft: '12px', fontSize: '12px', color: 'var(--muted)', background: '#f1f5f9', padding: '4px 8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
          Model: <strong>{activeModel}</strong>
        </span>
        <span style={{ flex: 1 }} />
        {messages.length > 0 && (
          <button
            className="btn"
            onClick={() => setMessages([])}
            style={{ fontSize: '11px', padding: '4px 10px' }}
          >
            Hapus riwayat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="chat-welcome-icon">🏥</div>
            <div className="chat-welcome-title">Chat dengan DARSI AI</div>
            <div className="chat-welcome-sub">
              Tanyakan apa saja tentang data operasional rumah sakit.
            </div>
            <div className="suggestions">
              {SUGGESTIONS.map(s => (
                <button key={s} className="suggestion-btn" onClick={() => handleSend(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`msg ${msg.role}`}>
              <div className="msg-bubble">{msg.content}</div>
              {msg.role === 'ai' && (msg.source || msg.domains?.length > 0 || msg.isError) && (
                <div className="msg-meta">
                  {msg.isError && <span className="meta-tag error-tag">error</span>}
                  {msg.source && <span className="meta-tag source">{msg.source}</span>}
                  {msg.domains?.map(d => (
                    <span key={d} className="meta-tag domain">{d}</span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}

        {/* Typing indicator */}
        {sending && (
          <div className="msg ai">
            <div className="msg-bubble typing-bubble">
              <div className="typing-dot" />
              <div className="typing-dot" />
              <div className="typing-dot" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="chat-input-area">
        <textarea
          ref={inputRef}
          className="chat-input"
          rows={1}
          placeholder="Ketik pertanyaan Anda… (Enter untuk kirim)"
          value={input}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          disabled={sending}
        />
        <button
          className="chat-send"
          onClick={() => handleSend()}
          disabled={sending || !input.trim()}
        >
          {sending ? '…' : 'Kirim'}
        </button>
      </div>
    </div>
  );
}
