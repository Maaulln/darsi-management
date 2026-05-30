import { useState, useRef, useEffect } from 'react';
import { apiPostStream } from '../api';

const SUGGESTIONS = [
  'Berapa pasien aktif hari ini?',
  'Bagaimana tren konsumsi listrik per unit?',
  'Unit mana yang tingkat huniannya tertinggi?',
  'Rangkum biaya operasional secara keseluruhan',
];

const STORAGE_KEY = 'darsi_chat_messages';

function loadMessages() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMessages(msgs) {
  try {
    const toSave = msgs
      .filter(m => !m.streaming)
      .map(({ role, content, isError }) => ({ role, content, isError }));
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
  } catch {}
}

export default function Chat() {
  const [messages, setMessages] = useState(loadMessages);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [useRag, setUseRag] = useState(true);
  const [activeModel, setActiveModel] = useState('Memuat...');
  const [availableModels, setAvailableModels] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [showModelSelector, setShowModelSelector] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    saveMessages(messages);
  }, [messages]);

  useEffect(() => {
    // Fetch available models and get active one
    fetch('/api/settings/ai-models')
      .then(r => r.json())
      .then(data => {
        if (data.models && data.models.length > 0) {
          setAvailableModels(data.models);
          const activeModel = data.models.find(m => m.is_active);
          if (activeModel) {
            setSelectedModelId(activeModel.id);
            setActiveModel(activeModel.name);
          } else {
            // Jika tidak ada model aktif, tampilkan yang pertama
            setActiveModel(data.models[0].name);
          }
        } else {
          setActiveModel('Default (Ollama Lokal)');
        }
      })
      .catch(() => {
        setActiveModel('Default (Ollama Lokal)');
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
    // Tambahkan placeholder AI message yang akan diisi token per token
    setMessages(prev => [...prev, { role: 'ai', content: '', streaming: true }]);

    try {
      await apiPostStream(
        '/api/chat/stream',
        { message: msg, use_rag: useRag },
        (chunk) => {
          setMessages(prev => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            updated[updated.length - 1] = { ...last, content: last.content + chunk };
            return updated;
          });
        }
      );
      // Tandai streaming selesai
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { ...updated[updated.length - 1], streaming: false };
        return updated;
      });
    } catch (e) {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = {
          role: 'ai',
          content: `Terjadi kesalahan: ${e.message}`,
          isError: true,
        };
        return updated;
      });
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

  const handleSelectModel = (model) => {
    // Activate the selected model
    fetch(`/api/settings/ai-models/${model.id}/activate`, { method: 'POST' })
      .then(r => r.json())
      .then(data => {
        if (data.status === 'ok') {
          setSelectedModelId(model.id);
          setActiveModel(model.name);
          setShowModelSelector(false);
        }
      })
      .catch(err => console.error('Gagal mengaktifkan model:', err));
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
        
        {/* Model Selector */}
        <div style={{ position: 'relative', marginLeft: '12px' }}>
          <button
            onClick={() => setShowModelSelector(!showModelSelector)}
            style={{
              fontSize: '12px',
              color: '#475569',
              background: '#f1f5f9',
              padding: '4px 8px',
              borderRadius: '4px',
              border: '1px solid var(--border)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontWeight: '500'
            }}
          >
            📦 <strong>{activeModel}</strong>
            <span style={{ fontSize: '10px' }}>▼</span>
          </button>
          
          {showModelSelector && availableModels.length > 0 && (
            <div style={{
              position: 'absolute',
              top: '100%',
              left: 0,
              marginTop: '4px',
              background: '#fff',
              border: '1px solid var(--border)',
              borderRadius: '6px',
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
              minWidth: '200px',
              zIndex: 1000
            }}>
              {availableModels.map(model => (
                <button
                  key={model.id}
                  onClick={() => handleSelectModel(model)}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '10px 12px',
                    border: 'none',
                    background: model.is_active ? '#ecfdf5' : '#fff',
                    cursor: 'pointer',
                    fontSize: '12px',
                    borderBottom: model.id !== availableModels[availableModels.length - 1].id ? '1px solid #f1f5f9' : 'none',
                    color: 'var(--text)',
                    transition: 'background 0.2s'
                  }}
                  onMouseEnter={(e) => {
                    if (!model.is_active) e.target.style.background = '#f1f5f9';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.background = model.is_active ? '#ecfdf5' : '#fff';
                  }}
                >
                  <div style={{ fontWeight: model.is_active ? '600' : '500' }}>
                    {model.is_active && '✓ '} {model.name}
                  </div>
                  <div style={{ fontSize: '10px', color: 'var(--muted)', marginTop: '2px', fontFamily: 'monospace' }}>
                    {model.model_name}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        <span style={{ flex: 1 }} />
        {messages.length > 0 && (
          <button
            className="btn"
            onClick={() => {
              setMessages([]);
              try { sessionStorage.removeItem(STORAGE_KEY); } catch {}
            }}
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
              <div className="msg-bubble">
                {msg.content}
                {msg.streaming && <span className="streaming-cursor">▍</span>}
              </div>
              {msg.role === 'ai' && !msg.streaming && (msg.source || msg.domains?.length > 0 || msg.isError) && (
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

        {/* Typing indicator — hanya tampil sebelum token pertama datang */}
        {sending && !messages.some(m => m.streaming) && (
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
