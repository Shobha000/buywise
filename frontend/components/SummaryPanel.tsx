'use client';

import { Stats } from '@/lib/types';

interface SummaryPanelProps {
  stats: Stats | null;
}

export default function SummaryPanel({ stats }: SummaryPanelProps) {
  if (!stats || stats.total === 0) {
    return (
      <div className="summary-panel">
        <div className="empty-state">
          <div className="empty-icon"></div>
          <p>AI summary will appear after first scrape.</p>
        </div>
      </div>
    );
  }

  const positiveRate = stats.total > 0
    ? Math.round((stats.positive / stats.total) * 100)
    : 0;

  const health =
    positiveRate >= 70 ? { label: 'Excellent', color: '#22c55e', icon: '🟢' }
    : positiveRate >= 50 ? { label: 'Good', color: '#f59e0b', icon: '🟡' }
    : positiveRate >= 30 ? { label: 'Fair', color: '#ff6b35', icon: '🟠' }
    : { label: 'Poor', color: '#f43f5e', icon: '' };

  const summary = positiveRate >= 60
    ? `${positiveRate}% of collected reviews are positive. The top themes across reviews include product quality, performance, and value. ${stats.fake_count > 0 ? `${stats.fake_count} suspicious review(s) have been flagged for manual review.` : 'No suspicious reviews detected.'}`
    : `Only ${positiveRate}% of reviews are positive. Significant negative sentiment detected. ${stats.fake_count > 0 ? `${stats.fake_count} suspicious review(s) flagged.` : ''} Consider investigating product quality or service issues.`;

  return (
    <div className="summary-panel">
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '12px 16px',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.07)',
        borderRadius: '12px',
      }}>
        <span style={{ fontSize: '22px' }}>{health.icon}</span>
        <div>
          <div style={{ fontSize: '11px', color: '#8892a4', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: '2px' }}>
            Overall Health
          </div>
          <div style={{ fontSize: '16px', fontWeight: 700, color: health.color }}>
            {health.label}
          </div>
        </div>
      </div>

      <div style={{
        fontSize: '13px',
        color: '#8892a4',
        lineHeight: '1.65',
        padding: '10px 0',
        borderTop: '1px solid rgba(255,255,255,0.05)',
        borderBottom: '1px solid rgba(255,255,255,0.05)',
      }}>
         <strong style={{ color: '#6c63ff' }}>AI Insight: </strong>
        {summary}
      </div>

      <div className="summary-stat-grid">
        <div className="summary-mini-stat">
          <div className="summary-mini-label">Avg Rating</div>
          <div className="summary-mini-value cyan">⭐ {stats.avg_rating.toFixed(1)}</div>
        </div>
        <div className="summary-mini-stat">
          <div className="summary-mini-label">Sentiment Score</div>
          <div className="summary-mini-value violet">{(stats.avg_sentiment_score * 100).toFixed(0)}%</div>
        </div>
        <div className="summary-mini-stat">
          <div className="summary-mini-label">Positive</div>
          <div className="summary-mini-value green">{stats.positive}</div>
        </div>
        <div className="summary-mini-stat">
          <div className="summary-mini-label">Flagged</div>
          <div className="summary-mini-value orange">{stats.fake_count}</div>
        </div>
      </div>
    </div>
  );
}
