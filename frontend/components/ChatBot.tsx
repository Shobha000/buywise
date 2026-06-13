'use client';

import { useState, useRef, useEffect } from 'react';

interface AnalysisResult {
  review: string;
  sentiment: string;
  fake_review_prediction: string;
  fake_probability: number;
  trust_score: number;
}

interface RecommendationResult {
  product: string;
  rating: number;
  review_count: number;
  trust_score: number;
  reason: string;
  buy_links?: Record<string, string>;
}

type Message = {
  role: 'user' | 'assistant';
  content: string;
  analysis?: AnalysisResult;
  recommendation?: RecommendationResult;
  buy_links?: Record<string, string>;
};

const SOURCE_ICONS: Record<string, string> = {
  Amazon: '🛒', Flipkart: '🛍️', G2: '⭐',
  Trustpilot: '✅', Google: '🔍', Yelp: '📍',
};

const SUGGESTIONS = [
  'Best Samsung phone to buy?',
  'Is this review fake? [paste it]',
  'How many reviews do you have?',
];

export default function ChatBot() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: "👋 Hey! I'm BuyWise.\n\nAsk me anything:\n• \"Which iPhone should I buy?\"\n• Paste any review → fake detection\n• \"Show me top rated laptops\"",
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [unread, setUnread] = useState(0);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (open) {
      setUnread(0);
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [open]);

  const handleSend = async (text?: string) => {
    const userMsg = (text || input).trim();
    if (!userMsg || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chatbot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: userMsg }),
      });
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.content,
        analysis: data.type === 'analysis' ? data.data : undefined,
        recommendation: data.type === 'recommendation' ? data.data : undefined,
        buy_links: data.buy_links || data.data?.buy_links,
      }]);
      if (!open) setUnread(u => u + 1);
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Could not reach the backend. Make sure it\'s running on port 8000.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* ── Floating Panel ── */}
      <div
        style={{
          position: 'fixed',
          bottom: '90px',
          right: '24px',
          width: '380px',
          height: '560px',
          zIndex: 9000,
          display: 'flex',
          flexDirection: 'column',
          background: '#1a1814',
          border: '1px solid rgba(245,158,11,0.2)',
          borderRadius: '20px',
          boxShadow: '0 24px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(255,255,255,0.05)',
          overflow: 'hidden',
          transformOrigin: 'bottom right',
          transition: 'transform 0.3s cubic-bezier(0.34,1.56,0.64,1), opacity 0.25s ease',
          transform: open ? 'scale(1) translateY(0)' : 'scale(0.85) translateY(20px)',
          opacity: open ? 1 : 0,
          pointerEvents: open ? 'all' : 'none',
        }}
      >
        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: '10px',
          padding: '14px 16px',
          background: 'rgba(245,158,11,0.08)',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
          flexShrink: 0,
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            background: 'linear-gradient(135deg, #f59e0b, #d97706)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '16px', flexShrink: 0,
            boxShadow: '0 0 12px rgba(245,158,11,0.4)',
          }}>🤖</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: '14px', color: '#f5f0e8' }}>BuyWise</div>
            <div style={{ fontSize: '11px', color: '#6b6456', display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#34d399', display: 'inline-block', boxShadow: '0 0 6px #34d399' }} />
              Online · Review intelligence
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            style={{
              width: 28, height: 28, borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#7a7265', fontSize: '16px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.07)',
              transition: 'all 0.15s',
              flexShrink: 0,
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; e.currentTarget.style.color = '#f5f0e8'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.05)'; e.currentTarget.style.color = '#7a7265'; }}
          >✕</button>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          style={{
            flex: 1, overflowY: 'auto', padding: '16px',
            display: 'flex', flexDirection: 'column', gap: '12px',
          }}
        >
          {messages.map((m, i) => (
            <div key={i} style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '90%', display: 'flex', flexDirection: 'column', gap: '8px',
            }}>
              {/* Bubble */}
              <div style={{
                padding: '10px 14px',
                borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                background: m.role === 'user'
                  ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                  : 'rgba(255,255,255,0.06)',
                color: m.role === 'user' ? '#000' : '#c9c0b0',
                fontSize: '13.5px', lineHeight: 1.6,
                whiteSpace: 'pre-wrap',
                border: m.role === 'assistant' ? '1px solid rgba(255,255,255,0.07)' : 'none',
                fontWeight: m.role === 'user' ? 600 : 400,
              }}>
                {m.content}
              </div>

              {/* Analysis card */}
              {m.analysis && (
                <div style={{
                  padding: '12px', background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.08)', borderRadius: '12px',
                  display: 'flex', flexDirection: 'column', gap: '10px',
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '10px', color: '#6b6456', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.5px' }}>Authenticity Check</span>
                    <span style={{
                      fontSize: '11px', fontWeight: 700,
                      color: m.analysis.fake_review_prediction === 'Likely Genuine' ? '#34d399' : '#f87171',
                      padding: '2px 8px', borderRadius: '99px',
                      background: m.analysis.fake_review_prediction === 'Likely Genuine' ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.12)',
                    }}>
                      {m.analysis.fake_review_prediction}
                    </span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                    {[
                      { label: 'Trust Score', value: `${m.analysis.trust_score}%`, color: '#f59e0b' },
                      { label: 'Sentiment', value: m.analysis.sentiment, color: m.analysis.sentiment === 'Positive' ? '#34d399' : m.analysis.sentiment === 'Negative' ? '#f87171' : '#f59e0b' },
                    ].map(({ label, value, color }) => (
                      <div key={label} style={{ background: 'rgba(0,0,0,0.3)', padding: '8px', borderRadius: '8px', textAlign: 'center' }}>
                        <div style={{ fontSize: '15px', fontWeight: 800, color }}>{value}</div>
                        <div style={{ fontSize: '9px', color: '#6b6456', textTransform: 'uppercase', marginTop: '2px' }}>{label}</div>
                      </div>
                    ))}
                  </div>
                  <div style={{ height: '3px', background: 'rgba(255,255,255,0.07)', borderRadius: '2px', overflow: 'hidden' }}>
                    <div style={{ width: `${m.analysis.trust_score}%`, height: '100%', background: 'linear-gradient(90deg, #f87171, #f59e0b, #34d399)', transition: 'width 1s ease-out' }} />
                  </div>
                </div>
              )}

              {/* Recommendation card */}
              {m.recommendation && (
                <div style={{
                  padding: '14px', borderRadius: '12px',
                  background: 'rgba(245,158,11,0.06)',
                  border: '1px solid rgba(245,158,11,0.2)',
                  display: 'flex', flexDirection: 'column', gap: '10px',
                }}>
                  <div style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 700 }}>🏆 TOP RECOMMENDATION</div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: '#f5f0e8', lineHeight: 1.4 }}>{m.recommendation.product}</div>
                  <div style={{ display: 'flex', gap: '12px' }}>
                    {[
                      { label: 'Rating', value: `⭐ ${m.recommendation.rating}` },
                      { label: 'Reviews', value: String(m.recommendation.review_count) },
                      { label: 'Trust', value: `${m.recommendation.trust_score}` },
                    ].map(({ label, value }) => (
                      <div key={label} style={{ textAlign: 'center', flex: 1 }}>
                        <div style={{ fontSize: '14px', fontWeight: 800, color: '#f5f0e8' }}>{value}</div>
                        <div style={{ fontSize: '9px', color: '#6b6456', textTransform: 'uppercase' }}>{label}</div>
                      </div>
                    ))}
                  </div>
                  {m.buy_links && Object.keys(m.buy_links).length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {Object.entries(m.buy_links).map(([src, url]) => (
                        <a key={src} href={url} target="_blank" rel="noopener noreferrer" style={{
                          display: 'inline-flex', alignItems: 'center', gap: '5px',
                          padding: '5px 10px', borderRadius: '7px',
                          background: src === 'Amazon' ? 'rgba(255,153,0,0.15)' : src === 'Flipkart' ? 'rgba(40,116,240,0.15)' : 'rgba(255,255,255,0.06)',
                          border: `1px solid ${src === 'Amazon' ? 'rgba(255,153,0,0.3)' : src === 'Flipkart' ? 'rgba(40,116,240,0.3)' : 'rgba(255,255,255,0.1)'}`,
                          color: '#f5f0e8', fontSize: '11px', fontWeight: 600, textDecoration: 'none',
                        }}>
                          {SOURCE_ICONS[src] || '🛒'} {src}
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Standalone buy links */}
              {!m.recommendation && m.buy_links && Object.keys(m.buy_links).length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {Object.entries(m.buy_links).map(([src, url]) => (
                    <a key={src} href={url} target="_blank" rel="noopener noreferrer" style={{
                      display: 'inline-flex', alignItems: 'center', gap: '5px',
                      padding: '5px 10px', borderRadius: '7px',
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: '#c9c0b0', fontSize: '11px', fontWeight: 600, textDecoration: 'none',
                    }}>
                      {SOURCE_ICONS[src] || '🔗'} {src}
                    </a>
                  ))}
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={{
              alignSelf: 'flex-start', padding: '10px 14px',
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid rgba(255,255,255,0.07)',
              borderRadius: '16px 16px 16px 4px',
              color: '#6b6456', fontSize: '13px',
              display: 'flex', alignItems: 'center', gap: '8px',
            }}>
              <span style={{ display: 'flex', gap: '3px' }}>
                {[0,1,2].map(j => (
                  <span key={j} style={{
                    width: 5, height: 5, borderRadius: '50%',
                    background: '#f59e0b', display: 'inline-block',
                    animation: `bounce 1.2s ${j * 0.2}s infinite`,
                  }} />
                ))}
              </span>
              Analysing…
            </div>
          )}
        </div>

        {/* Quick suggestions (only when ≤1 message) */}
        {messages.length <= 1 && (
          <div style={{ padding: '0 12px 8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {SUGGESTIONS.map(s => (
              <button key={s} onClick={() => handleSend(s)} style={{
                padding: '5px 10px', borderRadius: '99px', fontSize: '11.5px',
                background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)',
                color: '#c9c0b0', cursor: 'pointer', fontFamily: 'inherit',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.15)'; e.currentTarget.style.color = '#f5f0e8'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'rgba(245,158,11,0.08)'; e.currentTarget.style.color = '#c9c0b0'; }}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{
          padding: '12px', borderTop: '1px solid rgba(255,255,255,0.07)',
          background: 'rgba(0,0,0,0.2)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Ask me anything…"
              style={{
                flex: 1, padding: '10px 14px',
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.08)',
                borderRadius: '10px',
                color: '#f5f0e8', fontSize: '13.5px',
                outline: 'none', fontFamily: 'inherit',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = 'rgba(245,158,11,0.4)'}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
            />
            <button
              onClick={() => handleSend()}
              disabled={loading || !input.trim()}
              style={{
                width: 38, height: 38, borderRadius: '10px', flexShrink: 0,
                background: loading || !input.trim() ? 'rgba(245,158,11,0.3)' : 'linear-gradient(135deg, #f59e0b, #d97706)',
                border: 'none', color: '#000', fontSize: '16px',
                cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                transition: 'all 0.2s', fontWeight: 700,
              }}
            >
              ↑
            </button>
          </div>
        </div>
      </div>

      {/* ── Floating Trigger Button ── */}
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          position: 'fixed', bottom: '24px', right: '24px',
          width: 56, height: 56, borderRadius: '50%', zIndex: 9001,
          background: open
            ? 'rgba(245,158,11,0.15)'
            : 'linear-gradient(135deg, #f59e0b, #d97706)',
          border: open ? '2px solid rgba(245,158,11,0.4)' : 'none',
          color: open ? '#f59e0b' : '#000',
          fontSize: open ? '20px' : '24px',
          cursor: 'pointer',
          boxShadow: open
            ? '0 0 0 6px rgba(245,158,11,0.12)'
            : '0 8px 32px rgba(245,158,11,0.4), 0 2px 8px rgba(0,0,0,0.4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'all 0.3s cubic-bezier(0.34,1.56,0.64,1)',
          transform: open ? 'rotate(0deg) scale(1)' : 'scale(1)',
        }}
        onMouseEnter={e => !open && (e.currentTarget.style.transform = 'scale(1.1)')}
        onMouseLeave={e => !open && (e.currentTarget.style.transform = 'scale(1)')}
        title="BuyWise"
      >
        {open ? '✕' : '🤖'}
        {/* Unread badge */}
        {unread > 0 && !open && (
          <span style={{
            position: 'absolute', top: -4, right: -4,
            width: 20, height: 20, borderRadius: '50%',
            background: '#f87171', color: '#fff',
            fontSize: '11px', fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            border: '2px solid #0f0e0e',
          }}>
            {unread}
          </span>
        )}
      </button>

      {/* Bounce keyframe */}
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); }
          30% { transform: translateY(-5px); }
        }
      `}</style>
    </>
  );
}
