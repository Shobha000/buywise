'use client';

import { useState } from 'react';
import { Review } from '@/lib/types';

function Stars({ rating }: { rating: number | null }) {
  if (!rating) return null;
  return (
    <div className="stars">
      {[1, 2, 3, 4, 5].map((i) => (
        <span key={i} className={i <= Math.round(rating) ? 'star-filled' : 'star-empty'}>★</span>
      ))}
    </div>
  );
}

function ReviewImages({ images }: { images: string | null }) {
  const [lightbox, setLightbox] = useState<string | null>(null);
  if (!images) return null;

  let urls: string[] = [];
  try { urls = JSON.parse(images); } catch { return null; }
  if (!urls.length) return null;

  return (
    <>
      <div style={{
        display: 'flex', gap: '6px', flexWrap: 'nowrap',
        overflowX: 'auto', paddingBottom: '2px', marginBottom: '6px',
      }}>
        {urls.map((url, i) => (
          <button
            key={i}
            onClick={() => setLightbox(url)}
            style={{
              flexShrink: 0, padding: 0, border: 'none',
              background: 'rgba(255,255,255,0.05)',
              borderRadius: '8px', overflow: 'hidden',
              cursor: 'zoom-in',
              width: 72, height: 72,
              transition: 'transform 0.15s, box-shadow 0.15s',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.05)';
              e.currentTarget.style.boxShadow = '0 4px 16px rgba(0,0,0,0.4)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.boxShadow = 'none';
            }}
            title="Click to enlarge"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={url}
              alt={`Review photo ${i + 1}`}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </button>
        ))}
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div
          onClick={() => setLightbox(null)}
          style={{
            position: 'fixed', inset: 0, zIndex: 99999,
            background: 'rgba(0,0,0,0.85)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'zoom-out',
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={lightbox}
            alt="Review photo"
            style={{
              maxWidth: '90vw', maxHeight: '90vh',
              borderRadius: '12px',
              boxShadow: '0 24px 80px rgba(0,0,0,0.8)',
              objectFit: 'contain',
            }}
          />
          <button
            onClick={() => setLightbox(null)}
            style={{
              position: 'absolute', top: 20, right: 24,
              background: 'rgba(255,255,255,0.1)', border: '1px solid rgba(255,255,255,0.2)',
              borderRadius: '50%', width: 36, height: 36,
              color: '#fff', fontSize: 18, cursor: 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >✕</button>
        </div>
      )}
    </>
  );
}

function SourceTag({ source }: { source: string }) {
  const key = source.toLowerCase();
  return (
    <span className={`source-tag ${key}`}>{source}</span>
  );
}

function SentimentBadge({ sentiment }: { sentiment: string | null }) {
  if (!sentiment) return null;
  const map: Record<string, string> = {
    POSITIVE: 'badge badge-positive',
    NEGATIVE: 'badge badge-negative',
    NEUTRAL:  'badge badge-neutral',
  };
  const icons: Record<string, string> = { POSITIVE: '✓', NEGATIVE: '✗', NEUTRAL: '–' };
  return (
    <span className={map[sentiment] ?? 'badge'}>
      {icons[sentiment]} {sentiment.charAt(0) + sentiment.slice(1).toLowerCase()}
    </span>
  );
}

function TopicBadges({ topics }: { topics: string | null }) {
  if (!topics) return null;
  try {
    const list: string[] = JSON.parse(topics);
    return (
      <>
        {list.slice(0, 2).map((t) => (
          <span key={t} className="badge badge-topic">{t}</span>
        ))}
      </>
    );
  } catch { return null; }
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function Avatar({ name }: { name: string }) {
  const hue = (name.charCodeAt(0) * 47 + name.charCodeAt(1 % name.length) * 13) % 360;
  return (
    <div style={{
      width: 30, height: 30, borderRadius: '50%', flexShrink: 0,
      background: `hsl(${hue}, 50%, 40%)`,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '12px', fontWeight: 700, color: '#fff',
    }}>
      {name.charAt(0).toUpperCase()}
    </div>
  );
}

export default function ReviewFeed({ reviews }: { reviews: Review[] }) {
  if (!reviews.length) {
    return (
      <div className="empty-state">
        <div className="empty-icon">💬</div>
        <p>No reviews yet. Search for a product to load live data.</p>
      </div>
    );
  }

  return (
    <div>
      {reviews.map((r) => (
        <div key={r.id} className="list-card">
          <div className="list-card-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '9px', minWidth: 0 }}>
              <Avatar name={r.author} />
              <div style={{ minWidth: 0 }}>
                <div className="list-card-author">{r.author}</div>
                <div className="list-card-meta" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <SourceTag source={r.source} />
                  <span style={{ opacity: 0.5 }}>·</span>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '140px' }}>
                    {r.product}
                  </span>
                </div>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '3px', flexShrink: 0, marginLeft: '8px' }}>
              <Stars rating={r.rating} />
              <span className="list-card-meta">{timeAgo(r.scraped_at)}</span>
            </div>
          </div>

          <div className="list-card-text">{r.text}</div>

          <ReviewImages images={r.images ?? null} />

          <div className="list-card-badges">
            <SentimentBadge sentiment={r.sentiment} />
            {r.is_fake && <span className="badge badge-fake">⚠️ Suspicious</span>}
            <TopicBadges topics={r.topics} />
          </div>
        </div>
      ))}
    </div>
  );
}
