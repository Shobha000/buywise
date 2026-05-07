'use client';

import { useState } from 'react';
import { Review } from '@/lib/types';

function ReviewImages({ images }: { images: string | null }) {
  const [lightbox, setLightbox] = useState<string | null>(null);
  if (!images) return null;
  let urls: string[] = [];
  try { urls = JSON.parse(images); } catch { return null; }
  if (!urls.length) return null;
  return (
    <>
      <div style={{ display: 'flex', gap: '6px', overflowX: 'auto', paddingBottom: '2px', marginBottom: '6px' }}>
        {urls.map((url, i) => (
          <button key={i} onClick={() => setLightbox(url)} style={{
            flexShrink: 0, padding: 0, border: 'none', background: 'rgba(255,255,255,0.05)',
            borderRadius: '8px', overflow: 'hidden', cursor: 'zoom-in', width: 72, height: 72,
            transition: 'transform 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.05)')}
          onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={url} alt={`Photo ${i + 1}`}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </button>
        ))}
      </div>
      {lightbox && (
        <div onClick={() => setLightbox(null)} style={{
          position: 'fixed', inset: 0, zIndex: 99999, background: 'rgba(0,0,0,0.85)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'zoom-out',
        }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={lightbox} alt="Review photo" style={{
            maxWidth: '90vw', maxHeight: '90vh', borderRadius: '12px',
            boxShadow: '0 24px 80px rgba(0,0,0,0.8)', objectFit: 'contain',
          }} />
          <button onClick={() => setLightbox(null)} style={{
            position: 'absolute', top: 20, right: 24, background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.2)', borderRadius: '50%',
            width: 36, height: 36, color: '#fff', fontSize: 18, cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>✕</button>
        </div>
      )}
    </>
  );
}

interface SearchResultsProps {
  reviews: Review[];
  searchedProduct: string;
  bySource: Record<string, number>;
  isSearching: boolean;
}

const SOURCE_META: Record<string, { icon: string; color: string }> = {
  Amazon:     { icon: '🛒', color: '#ff9900' },
  Flipkart:   { icon: '🛍️', color: '#2874f0' },
  Trustpilot: { icon: '⭐', color: '#00b67a' },
  G2:         { icon: '💻', color: '#ff492c' },
};

function Stars({ rating }: { rating: number | null }) {
  if (!rating) return null;
  return (
    <div className="stars">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} style={{ color: i <= Math.round(rating) ? '#f59e0b' : '#2d3748' }}>★</span>
      ))}
      <span style={{ marginLeft: 4, fontSize: '11px', color: '#8892a4' }}>{rating.toFixed(1)}</span>
    </div>
  );
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export default function SearchResults({ reviews, searchedProduct, bySource, isSearching }: SearchResultsProps) {
  if (isSearching && reviews.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🔄</div>
        <p style={{ color: 'var(--text-primary)', fontWeight: 600, fontSize: '18px', marginBottom: '8px' }}>
          Searching for {searchedProduct}
        </p>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Fetching properties from Amazon, Flipkart, Trustpilot, G2...
        </p>
      </div>
    );
  }

  if (!isSearching && reviews.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">🔎</div>
        <p>Search for a product above to see real reviews across the web.</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {reviews.map((r) => {
        const meta = SOURCE_META[r.source] || { icon: '🌐', color: 'var(--zillow-blue)' };
        
        return (
          <div key={r.id} className="list-card">
            <div className="list-card-header">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '16px' }}>{meta.icon}</span>
                <span className="list-card-author">{r.author}</span>
                <span className="list-card-meta">on {r.source}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                <Stars rating={r.rating} />
                <span className="list-card-meta">{timeAgo(r.scraped_at)}</span>
              </div>
            </div>
            
            <div className="list-card-text">{r.text}</div>

            <ReviewImages images={r.images ?? null} />

            <div className="list-card-badges">
              {r.sentiment && (
                <span className={`badge badge-${r.sentiment.toLowerCase()}`}>
                  {r.sentiment === 'POSITIVE' ? '😊' : r.sentiment === 'NEGATIVE' ? '😞' : '😐'} {r.sentiment}
                </span>
              )}
              {r.is_fake && <span className="badge badge-fake">⚠️ Suspicious</span>}
            </div>

            {r.summary && r.summary !== r.text && (
              <div style={{
                marginTop: '12px',
                padding: '10px 14px',
                background: 'var(--bg-primary)',
                borderLeft: '3px solid var(--zillow-blue)',
                borderRadius: 'var(--radius-sm)',
                fontSize: '13px', color: 'var(--text-secondary)', fontStyle: 'italic',
              }}>
                🤖 {r.summary}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
