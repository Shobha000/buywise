'use client';

import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts';

interface SourceStat {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  fake: number;
  avg_rating: number;
}

interface TopicItem { topic: string; count: number }
interface SentDist { source: string; positive: number; negative: number; neutral: number }

interface Analytics {
  total: number;
  positive: number;
  negative: number;
  neutral: number;
  fake_count: number;
  fake_percent: number;
  avg_rating: number;
  avg_sentiment_score: number;
  by_source_stats: Record<string, SourceStat>;
  top_topics: TopicItem[];
  sentiment_distribution: SentDist[];
}

interface SearchAnalyticsProps {
  analytics: Analytics;
  product: string;
}

const SOURCE_COLORS: Record<string, string> = {
  Amazon: '#ff9900',
  Flipkart: '#2874f0',
  Trustpilot: '#00b67a',
  G2: '#ff492c',
};

const SENTIMENT_COLORS = { positive: '#22c55e', negative: '#f43f5e', neutral: '#f59e0b' };

const CustomPieTooltip = ({ active, payload }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border)',
        borderRadius: 10, padding: '10px 14px', fontSize: 12,
        boxShadow: 'var(--shadow-hover)'
      }}>
        <p style={{ color: payload[0].payload.fill, fontWeight: 700 }}>{payload[0].name}</p>
        <p style={{ color: 'var(--text-primary)' }}>{payload[0].value} reviews</p>
      </div>
    );
  }
  return null;
};

const CustomBarTooltip = ({ active, payload, label }: any) => {
  if (active && payload?.length) {
    return (
      <div style={{
        background: '#ffffff',
        border: '1px solid var(--border)',
        borderRadius: 10, padding: '10px 14px', fontSize: 12,
        boxShadow: 'var(--shadow-hover)'
      }}>
        <p style={{ color: 'var(--text-secondary)', fontWeight: 600, marginBottom: 4 }}>{label}</p>
        {payload.map((p: any) => (
          <div key={p.name} style={{ color: p.fill, fontWeight: 600 }}>
            {p.name}: {p.value}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function SearchAnalytics({ analytics, product }: SearchAnalyticsProps) {
  const positiveRate = analytics.total > 0
    ? Math.round((analytics.positive / analytics.total) * 100)
    : 0;

  const health =
    positiveRate >= 70 ? { label: 'Excellent', color: '#22c55e', icon: '🟢' }
    : positiveRate >= 50 ? { label: 'Good', color: '#f59e0b', icon: '🟡' }
    : positiveRate >= 30 ? { label: 'Fair', color: '#ff6b35', icon: '🟠' }
    : { label: 'Poor', color: '#f43f5e', icon: '🔴' };

  const sentimentPieData = [
    { name: 'Positive', value: analytics.positive, fill: '#22c55e' },
    { name: 'Negative', value: analytics.negative, fill: '#f43f5e' },
    { name: 'Neutral', value: analytics.neutral, fill: '#f59e0b' },
  ].filter(d => d.value > 0);

  const topicData = analytics.top_topics.slice(0, 8);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* ── Header ── */}
      <div style={{
        padding: '18px 20px',
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '12px',
      }}>
        <div>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '3px' }}>
            🤖 AI Analysis for
          </div>
          <div style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>
            {product}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {[
            { label: 'Total Reviews', value: analytics.total, color: 'var(--zillow-blue)' },
            { label: 'Avg Rating', value: `⭐ ${analytics.avg_rating.toFixed(1)}`, color: '#f59e0b' },
            { label: 'Positive', value: `${positiveRate}%`, color: '#22c55e' },
            { label: 'Suspicious', value: `${analytics.fake_percent}%`, color: '#ff6b35' },
          ].map(s => (
            <div key={s.label} style={{
              padding: '10px 16px',
              background: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              borderRadius: '12px',
              textAlign: 'center',
              minWidth: '90px',
            }}>
              <div style={{ fontSize: '20px', fontWeight: 800, color: s.color }}>{s.value}</div>
              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '2px' }}>{s.label}</div>
            </div>
          ))}
          <div style={{
            padding: '10px 16px',
            background: `${health.color}18`,
            border: `1px solid ${health.color}40`,
            borderRadius: '12px',
            textAlign: 'center',
            minWidth: '90px',
          }}>
            <div style={{ fontSize: '20px' }}>{health.icon}</div>
            <div style={{ fontSize: '13px', fontWeight: 700, color: health.color }}>{health.label}</div>
            <div style={{ fontSize: '10px', color: '#8892a4' }}>Health</div>
          </div>
        </div>
      </div>

      {/* ── Charts Row ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px' }}>

        {/* Sentiment Donut */}
        <div className="glass-card">
          <div className="card-header">
            <span className="card-title">😊 Sentiment Split</span>
          </div>
          <div style={{ padding: '8px 16px 16px' }}>
            <ResponsiveContainer width="100%" height={160}>
              <PieChart>
                <Pie data={sentimentPieData} cx="50%" cy="50%" innerRadius={40} outerRadius={60}
                  paddingAngle={3} dataKey="value" strokeWidth={0} isAnimationActive={false}>
                  {sentimentPieData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                </Pie>
                <Tooltip content={<CustomPieTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '-8px' }}>
              {sentimentPieData.map(d => (
                <div key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '11px' }}>
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: d.fill, display: 'inline-block' }} />
                  <span style={{ color: d.fill, fontWeight: 600 }}>{d.name}</span>
                  <span style={{ color: '#4a5568' }}>({d.value})</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Per-Source Sentiment Bar */}
        <div className="glass-card" style={{ gridColumn: 'span 2' }}>
          <div className="card-header">
            <span className="card-title">🏪 Sentiment by Source</span>
          </div>
          <div style={{ padding: '0 16px 16px' }}>
            {analytics.sentiment_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={analytics.sentiment_distribution} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="source" tick={{ fill: '#8892a4', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#8892a4', fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomBarTooltip />} />
                  <Bar dataKey="positive" fill="#22c55e" radius={[3,3,0,0]} name="Positive" isAnimationActive={false} />
                  <Bar dataKey="negative" fill="#f43f5e" radius={[3,3,0,0]} name="Negative" isAnimationActive={false} />
                  <Bar dataKey="neutral" fill="#f59e0b" radius={[3,3,0,0]} name="Neutral" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state" style={{ paddingTop: '30px' }}><p>No data</p></div>
            )}
          </div>
        </div>
      </div>

      {/* ── Top Topics + Source Cards Row ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: '16px' }}>

        {/* Top Topics */}
        <div className="glass-card">
          <div className="card-header">
            <span className="card-title">🏷️ Top Discussed Topics</span>
          </div>
          <div style={{ padding: '8px 16px 16px' }}>
            {topicData.length > 0 ? (
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={topicData} layout="vertical" margin={{ top: 0, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#8892a4', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="topic" tick={{ fill: '#8892a4', fontSize: 10 }} axisLine={false} tickLine={false} width={72} />
                  <Tooltip content={<CustomBarTooltip />} />
                  <Bar dataKey="count" radius={[0, 5, 5, 0]} name="Mentions" isAnimationActive={false}>
                    {topicData.map((_, i) => (
                      <Cell key={i} fill={['#6c63ff','#00d4ff','#22c55e','#f59e0b','#f43f5e','#8b5cf6','#06b6d4','#10b981'][i % 8]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state"><p>No topics extracted.</p></div>
            )}
          </div>
        </div>

        {/* Per-Source stat cards */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {Object.entries(analytics.by_source_stats).map(([src, stat]) => {
            const color = SOURCE_COLORS[src] || '#6c63ff';
            return (
              <div key={src} style={{
                padding: '12px 16px',
                background: `${color}0f`,
                border: `1px solid ${color}30`,
                borderRadius: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px',
              }}>
                <div>
                  <div style={{ fontSize: '13px', fontWeight: 700, color, marginBottom: '3px' }}>
                    {src}
                  </div>
                  <div style={{ fontSize: '11px', color: '#8892a4' }}>
                    {stat.total} reviews · ⭐ {stat.avg_rating.toFixed(1)}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '6px', fontSize: '11px' }}>
                  <span style={{ color: '#22c55e', fontWeight: 700 }}>+{stat.positive}</span>
                  <span style={{ color: '#f43f5e', fontWeight: 700 }}>-{stat.negative}</span>
                  {stat.fake > 0 && <span style={{ color: '#ff6b35', fontWeight: 700 }}>⚠️{stat.fake}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
