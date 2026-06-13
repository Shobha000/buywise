'use client';

interface StatCardProps {
  icon: string;
  label: string;
  value: number | string;
  color?: string;
  trend?: string;
  trendDir?: 'up' | 'down';
}

const ACCENT: Record<string, string> = {
  violet: '#a78bfa',
  green:  '#34d399',
  red:    '#f87171',
  orange: '#fb923c',
  blue:   '#60a5fa',
};

export default function StatCard({ icon, label, value, color = 'violet', trend, trendDir }: StatCardProps) {
  const accent = ACCENT[color] || ACCENT.violet;
  const formatted = typeof value === 'number' ? value.toLocaleString() : value;

  return (
    <div
      className="stat-card"
      style={{ '--card-accent': accent } as React.CSSProperties}
    >
      <div className="stat-icon">{icon}</div>
      <div className="stat-value">{formatted}</div>
      <div className="stat-label">{label}</div>
      {trend && (
        <div
          className="stat-trend"
          style={{ color: trendDir === 'up' ? '#34d399' : trendDir === 'down' ? '#fb923c' : '#94a3b8' }}
        >
          {trendDir === 'up' ? '↑' : trendDir === 'down' ? '↓' : '→'} {trend}
        </div>
      )}
    </div>
  );
}
