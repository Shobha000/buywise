'use client';

import { Stats } from '@/lib/types';

interface FakeGaugeProps {
  stats: Stats | null;
}

// Pure SVG donut — no recharts hack needed for a simple 2-segment gauge
function DonutChart({ genuine, suspicious, total }: { genuine: number; suspicious: number; total: number }) {
  const RADIUS = 64;
  const STROKE = 14;
  const cx = 90;
  const cy = 90;
  const circumference = 2 * Math.PI * RADIUS;

  const genuineRatio  = total > 0 ? genuine  / total : 1;
  const suspiciousRatio = total > 0 ? suspicious / total : 0;

  const genuineDash    = genuineRatio    * circumference;
  const suspiciousDash = suspiciousRatio * circumference;

  // Start from top (−90°)
  const genuineOffset    = circumference * 0.25; // 0° = right, shift -90°
  const suspiciousOffset = circumference - genuineDash + circumference * 0.25;

  return (
    <svg width={180} height={180} viewBox="0 0 180 180">
      {/* Track */}
      <circle
        cx={cx} cy={cy} r={RADIUS}
        fill="none"
        stroke="rgba(255,255,255,0.05)"
        strokeWidth={STROKE}
      />
      {/* Genuine arc */}
      {genuine > 0 && (
        <circle
          cx={cx} cy={cy} r={RADIUS}
          fill="none"
          stroke="#34d399"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${genuineDash - 3} ${circumference - genuineDash + 3}`}
          strokeDashoffset={genuineOffset}
          style={{ transform: 'rotate(-90deg)', transformOrigin: `${cx}px ${cy}px`, transition: 'stroke-dasharray 1s ease' }}
        />
      )}
      {/* Suspicious arc */}
      {suspicious > 0 && (
        <circle
          cx={cx} cy={cy} r={RADIUS}
          fill="none"
          stroke="#fb923c"
          strokeWidth={STROKE}
          strokeLinecap="round"
          strokeDasharray={`${suspiciousDash - 3} ${circumference - suspiciousDash + 3}`}
          strokeDashoffset={suspiciousOffset}
          style={{ transform: 'rotate(-90deg)', transformOrigin: `${cx}px ${cy}px`, transition: 'stroke-dasharray 1s ease' }}
        />
      )}
    </svg>
  );
}

export default function FakeGauge({ stats }: FakeGaugeProps) {
  if (!stats || stats.total === 0) {
    return (
      <div className="empty-state" style={{ padding: '40px 0' }}>
        <div className="empty-icon">🛡️</div>
        <p>No review data yet.</p>
      </div>
    );
  }

  const genuine   = stats.total - stats.fake_count;
  const fake      = stats.fake_count;
  const fakeRate  = stats.fake_percent ?? 0;

  // Health label
  let healthLabel = 'Excellent';
  let healthColor = '#34d399';
  if (fakeRate > 30) { healthLabel = 'Poor';    healthColor = '#f87171'; }
  else if (fakeRate > 15) { healthLabel = 'Fair'; healthColor = '#fb923c'; }
  else if (fakeRate > 5)  { healthLabel = 'Good'; healthColor = '#fbbf24'; }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Main metric row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>

        {/* SVG Donut */}
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <DonutChart genuine={genuine} suspicious={fake} total={stats.total} />
          {/* Center label — absolutely positioned over SVG */}
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            pointerEvents: 'none',
          }}>
            <div style={{
              fontSize: '22px', fontWeight: 800, lineHeight: 1,
              color: fakeRate > 5 ? '#fb923c' : '#34d399',
            }}>
              {fakeRate}%
            </div>
            <div style={{
              fontSize: '10px', fontWeight: 600, marginTop: '4px',
              color: 'var(--cream-muted)',
              textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>
              suspicious
            </div>
          </div>
        </div>

        {/* Right side stats */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '12px' }}>

          {/* Health badge */}
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: '7px',
            padding: '6px 12px', borderRadius: '99px',
            background: `${healthColor}18`,
            border: `1px solid ${healthColor}40`,
            alignSelf: 'flex-start',
          }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: healthColor, display: 'inline-block', boxShadow: `0 0 8px ${healthColor}` }} />
            <span style={{ fontSize: '12px', fontWeight: 700, color: healthColor }}>{healthLabel} Health</span>
          </div>

          {/* Genuine row */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#34d399', display: 'inline-block' }} />
                <span style={{ fontSize: '12px', color: 'var(--cream-muted)', fontWeight: 500 }}>Genuine</span>
              </div>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#34d399' }}>
                {genuine.toLocaleString()} <span style={{ fontSize: '10px', fontWeight: 400, color: 'var(--cream-muted)' }}>({(100 - fakeRate).toFixed(1)}%)</span>
              </span>
            </div>
            <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%', background: '#34d399', borderRadius: 4,
                width: `${100 - fakeRate}%`,
                transition: 'width 1s ease',
                boxShadow: '0 0 8px rgba(52,211,153,0.4)',
              }} />
            </div>
          </div>

          {/* Suspicious row */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#fb923c', display: 'inline-block' }} />
                <span style={{ fontSize: '12px', color: 'var(--cream-muted)', fontWeight: 500 }}>Suspicious</span>
              </div>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#fb923c' }}>
                {fake.toLocaleString()} <span style={{ fontSize: '10px', fontWeight: 400, color: 'var(--cream-muted)' }}>({fakeRate}%)</span>
              </span>
            </div>
            <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                height: '100%', background: '#fb923c', borderRadius: 4,
                width: `${Math.max(fakeRate, fake > 0 ? 3 : 0)}%`,
                transition: 'width 1s ease',
                boxShadow: '0 0 8px rgba(251,146,60,0.4)',
              }} />
            </div>
          </div>
        </div>
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'rgba(255,255,255,0.05)' }} />

      {/* Total reviewed */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: 'var(--cream-muted)' }}>Total reviewed</span>
        <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--cream)' }}>{stats.total.toLocaleString()} reviews</span>
      </div>
    </div>
  );
}
