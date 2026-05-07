'use client';

import {
  RadialBarChart, RadialBar, ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from 'recharts';

// ─── Types ────────────────────────────────────────────────────────────────────
interface FakeAnalysis  { fake_count: number; fake_percent: number; risk: string }
interface SourceStat    { total: number; positive: number; negative: number; neutral: number; fake: number; avg_rating: number }
interface ModelInfo     { trained: boolean; accuracy: number | null; review_count: number; version: string }

interface Report {
  product: string; score: number; verdict: string; verdict_emoji: string; verdict_color: string;
  total_reviews_analyzed: number; positive_count: number; negative_count: number; neutral_count: number;
  avg_rating: number; confidence: string;
  pros: string[]; cons: string[];
  what_customers_love: string; what_customers_dislike: string;
  key_themes: string[];
  fake_analysis: FakeAnalysis;
  // ML Model fields
  aspect_sentiment: Record<string, number | null>;
  review_quality_score: number;
  authenticity_score: number;
  price_value_score: number | null;
  recommendation_confidence: number;
  against_confidence: number;
  review_trend: string;
  source_breakdown: Record<string, SourceStat>;
  rating_distribution: Record<string, number>;
  model_info: ModelInfo;
}

interface Props { report: Report; onClose: () => void }

// ─── Constants ────────────────────────────────────────────────────────────────
const SOURCE_COLORS: Record<string, string> = { Amazon:'#ff9900', Flipkart:'#2874f0', Trustpilot:'#00b67a', G2:'#ff492c' };
const CONFIDENCE_COLOR: Record<string, string> = { High:'#22c55e', Medium:'#f59e0b', Low:'#f43f5e' };
const RISK_COLOR: Record<string, string> = { Low:'#22c55e', Medium:'#f59e0b', High:'#f43f5e' };
const TREND_ICON: Record<string, string> = { Improving:'↑', Declining:'↓', Stable:'→' };
const TREND_COLOR: Record<string, string> = { Improving:'#22c55e', Declining:'#f43f5e', Stable:'#f59e0b' };
const ASPECT_ICONS: Record<string, string> = { battery:'🔋', camera:'📷', display:'📱', performance:'⚡', design:'✨', price:'💰', software:'💻', build:'🏗️' };

// ─── Sub-components ───────────────────────────────────────────────────────────
function ScoreGauge({ score, color }: { score: number; color: string }) {
  const data = [{ value: score, fill: color }, { value: 100 - score, fill: 'var(--border)' }];
  return (
    <div style={{ position:'relative', width:150, height:150 }}>
      <ResponsiveContainer width="100%" height="100%">
        <RadialBarChart cx="50%" cy="50%" innerRadius="65%" outerRadius="90%" startAngle={180} endAngle={-180} data={data} barSize={14}>
          <RadialBar dataKey="value" cornerRadius={8} background={{ fill:'var(--border)' }} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div style={{ position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)', textAlign:'center' }}>
        <div style={{ fontSize:34, fontWeight:900, color, lineHeight:1 }}>{score}</div>
        <div style={{ fontSize:10, color:'#8892a4', marginTop:2 }}>/ 100</div>
      </div>
    </div>
  );
}

function MiniGauge({ value, label, color }: { value: number; label: string; color: string }) {
  const data = [{ value, fill: color }, { value: 100 - value, fill: 'var(--border)' }];
  return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', gap:4 }}>
      <div style={{ position:'relative', width:80, height:80 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart cx="50%" cy="50%" innerRadius="60%" outerRadius="85%" startAngle={180} endAngle={-180} data={data} barSize={8}>
            <RadialBar dataKey="value" cornerRadius={4} background={{ fill:'var(--border)' }} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div style={{ position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)', textAlign:'center' }}>
          <div style={{ fontSize:15, fontWeight:800, color }}>{value}</div>
        </div>
      </div>
      <div style={{ fontSize:10, color:'#8892a4', textAlign:'center' }}>{label}</div>
    </div>
  );
}

function AspectRadar({ data }: { data: { aspect: string; score: number; icon: string }[] }) {
  if (!data.length) return null;
  return (
    <ResponsiveContainer width="100%" height={220}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis dataKey="aspect" tick={{ fill:'#8892a4', fontSize:10 }}
          tickFormatter={(val) => `${ASPECT_ICONS[val] || ''} ${val}`} />
        <Radar dataKey="score" stroke="#6c63ff" fill="#6c63ff" fillOpacity={0.3} strokeWidth={2} dot={{ fill:'#6c63ff', r:3 }} />
        <Tooltip
          contentStyle={{ background:'#ffffff', border:'1px solid var(--border)', borderRadius:8, fontSize:12, boxShadow:'var(--shadow-hover)' }}
          formatter={(v: any, n: any, p: any) => [`${v}/100`, p.payload.aspect]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function ReportPanel({ report, onClose }: Props) {
  const total = report.total_reviews_analyzed || 1;
  const sentimentData = [
    { name:'Positive', value: report.positive_count, fill:'#22c55e' },
    { name:'Negative', value: report.negative_count, fill:'#f43f5e' },
    { name:'Neutral',  value: report.neutral_count,  fill:'#f59e0b' },
  ].filter(d => d.value > 0);

  // Aspect radar data — only show mentioned aspects
  const aspectData = Object.entries(report.aspect_sentiment || {})
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([aspect, score]) => ({ aspect, score: score as number, icon: ASPECT_ICONS[aspect] || '' }));

  const trend = report.review_trend || 'Stable';

  return (
    <div style={{ background:'var(--bg-card)', border:'1px solid var(--border)', borderRadius:24, padding:28, boxShadow:'var(--shadow-hover)' }}>

      {/* ── Header ── */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:24 }}>
        <div>
          <div style={{ fontSize:11, color:'#6c63ff', fontWeight:700, textTransform:'uppercase', letterSpacing:'0.08em', marginBottom:6 }}>
            🤖 AI Product Intelligence Report
          </div>
          <h2 style={{ fontSize:22, fontWeight:900, color:'var(--text-primary)', margin:0 }}>{report.product}</h2>
          <div style={{ fontSize:12, color:'#8892a4', marginTop:4, display:'flex', gap:12, flexWrap:'wrap' }}>
            <span>Based on <b style={{ color:'var(--text-primary)' }}>{report.total_reviews_analyzed}</b> reviews</span>
            <span>Confidence: <b style={{ color: CONFIDENCE_COLOR[report.confidence] }}>{report.confidence}</b></span>
            <span style={{ color: TREND_COLOR[trend], fontWeight:700 }}>
              {TREND_ICON[trend]} {trend}
            </span>
            {report.model_info?.trained && (
              <span style={{ color:'#6c63ff' }}>
                🧠 Model Accuracy: <b>{report.model_info.accuracy ? `${(report.model_info.accuracy * 100).toFixed(1)}%` : 'N/A'}</b>
              </span>
            )}
          </div>
        </div>
        <button onClick={onClose} style={{ background:'var(--bg-secondary)', border:'1px solid var(--border)', borderRadius:'50%', width:36, height:36, color:'var(--text-secondary)', cursor:'pointer', fontSize:18, display:'flex', alignItems:'center', justifyContent:'center' }}>✕</button>
      </div>

      {/* ── Row 1: Score + Key Stats + Mini Gauges ── */}
      <div style={{ display:'grid', gridTemplateColumns:'auto 1fr auto', gap:16, marginBottom:20 }}>

        {/* Score Gauge + Verdict */}
        <div style={{ padding:20, background:`${report.verdict_color}08`, border:`1px solid ${report.verdict_color}30`, borderRadius:20, display:'flex', flexDirection:'column', alignItems:'center', gap:8 }}>
          <ScoreGauge score={report.score} color={report.verdict_color} />
          <div style={{ fontSize:14, fontWeight:800, color:report.verdict_color, textAlign:'center' }}>
            {report.verdict_emoji} {report.verdict}
          </div>
        </div>

        {/* Key Stat Grid */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:10 }}>
          {[
            { label:'Total Reviews', value: report.total_reviews_analyzed, color:'#6c63ff' },
            { label:'Avg Rating', value:`⭐ ${report.avg_rating.toFixed(1)}`, color:'#f59e0b' },
            { label:'😊 Positive', value:`${report.positive_count} (${Math.round(report.positive_count/total*100)}%)`, color:'#22c55e' },
            { label:'😞 Negative', value:`${report.negative_count} (${Math.round(report.negative_count/total*100)}%)`, color:'#f43f5e' },
            { label:'👍 Recommend', value:`${report.recommendation_confidence}%`, color:'#22c55e' },
            { label:'👎 Against', value:`${report.against_confidence}%`, color:'#f43f5e' },
          ].map(s => (
            <div key={s.label} style={{ padding:'10px 14px', background:'var(--bg-primary)', border:'1px solid var(--border)', borderRadius:12 }}>
              <div style={{ fontSize:17, fontWeight:800, color:s.color }}>{s.value}</div>
              <div style={{ fontSize:10, color:'#8892a4', marginTop:2 }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* ML Gauges */}
        <div style={{ padding:'16px 20px', background:'var(--bg-primary)', border:'1px solid var(--border)', borderRadius:16, display:'flex', flexDirection:'column', gap:12, alignItems:'center', justifyContent:'center' }}>
          <div style={{ fontSize:11, color:'#8892a4', fontWeight:600, textAlign:'center' }}>🧠 ML Scores</div>
          <div style={{ display:'flex', gap:16 }}>
            <MiniGauge value={report.review_quality_score} label="Quality" color="#6c63ff" />
            <MiniGauge value={report.authenticity_score} label="Authentic" color="#00d4ff" />
            {report.price_value_score !== null && report.price_value_score !== undefined && (
              <MiniGauge value={report.price_value_score} label="Price-Value" color="#22c55e" />
            )}
          </div>
        </div>
      </div>

      {/* ── Row 2: Aspect Radar + Sentiment Donut ── */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr auto', gap:16, marginBottom:20 }}>

        {/* Aspect Radar */}
        {aspectData.length >= 3 && (
          <div style={{ padding:'16px 20px', background:'var(--bg-primary)', border:'1px solid var(--border)', borderRadius:16 }}>
            <div style={{ fontSize:13, fontWeight:700, color:'var(--text-primary)', marginBottom:8 }}>📡 Aspect-Level Sentiment</div>
            <div style={{ fontSize:11, color:'#8892a4', marginBottom:8 }}>How customers feel about specific product aspects</div>
            <AspectRadar data={aspectData} />
          </div>
        )}

        {/* Sentiment Donut + Source donut */}
        <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
          <div style={{ padding:'14px 16px', background:'var(--bg-primary)', border:'1px solid var(--border)', borderRadius:14, textAlign:'center' }}>
            <div style={{ fontSize:11, color:'#8892a4', fontWeight:600, marginBottom:6 }}>Sentiment Split</div>
            <ResponsiveContainer width={160} height={100}>
              <PieChart>
                <Pie data={sentimentData} cx="50%" cy="50%" innerRadius={28} outerRadius={44} paddingAngle={3} dataKey="value" strokeWidth={0}>
                  {sentimentData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                </Pie>
                <Tooltip contentStyle={{ background:'#ffffff', border:'1px solid var(--border)', borderRadius:8, fontSize:11, boxShadow:'var(--shadow-hover)' }} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display:'flex', gap:8, justifyContent:'center', flexWrap:'wrap' }}>
              {sentimentData.map(d => (
                <span key={d.name} style={{ fontSize:10, color:d.fill, fontWeight:700 }}>● {d.name}</span>
              ))}
            </div>
          </div>

          {/* Fake Risk */}
          <div style={{ padding:'14px 16px', background:`${RISK_COLOR[report.fake_analysis.risk] || '#f59e0b'}08`, border:`1px solid ${RISK_COLOR[report.fake_analysis.risk] || '#f59e0b'}30`, borderRadius:14, textAlign:'center' }}>
            <div style={{ fontSize:11, color:'#8892a4', fontWeight:600, marginBottom:4 }}>⚠️ Fake Risk</div>
            <div style={{ fontSize:24, fontWeight:900, color: RISK_COLOR[report.fake_analysis.risk] }}>{report.fake_analysis.risk}</div>
            <div style={{ fontSize:10, color:'#8892a4' }}>{report.fake_analysis.fake_count} suspicious ({report.fake_analysis.fake_percent}%)</div>
          </div>
        </div>
      </div>

      {/* ── Pros / Cons ── */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16, marginBottom:20 }}>
        <div style={{ padding:18, background:'rgba(34,197,94,0.06)', border:'1px solid rgba(34,197,94,0.2)', borderRadius:16 }}>
          <div style={{ fontSize:14, fontWeight:800, color:'#22c55e', marginBottom:12 }}>👍 What Customers Love</div>
          <ul style={{ margin:0, padding:0, listStyle:'none', display:'flex', flexDirection:'column', gap:8 }}>
            {report.pros.length > 0
              ? report.pros.map((p, i) => (
                  <li key={i} style={{ display:'flex', gap:8, fontSize:12, color:'#d1fae5', lineHeight:1.5 }}>
                    <span style={{ color:'#22c55e', flexShrink:0 }}>✓</span>{p}
                  </li>
                ))
              : <li style={{ color:'#4a5568', fontSize:12 }}>No highlights found.</li>}
          </ul>
          {report.what_customers_love && (
            <div style={{ marginTop:12, padding:'8px 12px', background:'rgba(34,197,94,0.08)', borderLeft:'2px solid #22c55e', borderRadius:'0 8px 8px 0', fontSize:11, color:'#86efac', fontStyle:'italic' }}>
              🤖 {report.what_customers_love}
            </div>
          )}
        </div>

        <div style={{ padding:18, background:'rgba(244,63,94,0.06)', border:'1px solid rgba(244,63,94,0.2)', borderRadius:16 }}>
          <div style={{ fontSize:14, fontWeight:800, color:'#f43f5e', marginBottom:12 }}>👎 Common Complaints</div>
          <ul style={{ margin:0, padding:0, listStyle:'none', display:'flex', flexDirection:'column', gap:8 }}>
            {report.cons.length > 0
              ? report.cons.map((c, i) => (
                  <li key={i} style={{ display:'flex', gap:8, fontSize:12, color:'#fecaca', lineHeight:1.5 }}>
                    <span style={{ color:'#f43f5e', flexShrink:0 }}>✗</span>{c}
                  </li>
                ))
              : <li style={{ color:'#4a5568', fontSize:12 }}>No complaints found.</li>}
          </ul>
          {report.what_customers_dislike && (
            <div style={{ marginTop:12, padding:'8px 12px', background:'rgba(244,63,94,0.08)', borderLeft:'2px solid #f43f5e', borderRadius:'0 8px 8px 0', fontSize:11, color:'#fca5a5', fontStyle:'italic' }}>
              🤖 {report.what_customers_dislike}
            </div>
          )}
        </div>
      </div>

      {/* ── Key Themes + Model Info ── */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr auto', gap:16, marginBottom:20 }}>
        <div style={{ padding:'16px 18px', background:'var(--bg-primary)', border:'1px solid var(--border)', borderRadius:14 }}>
          <div style={{ fontSize:13, fontWeight:700, color:'var(--text-primary)', marginBottom:10 }}>🏷️ Key Themes Discussed</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
            {report.key_themes.length > 0
              ? report.key_themes.map((t, i) => (
                  <span key={t} style={{ padding:'4px 12px', borderRadius:99, fontSize:12, fontWeight:600, background:`hsl(${i*47%360},60%,90%)`, color:`hsl(${i*47%360},80%,30%)`, border:`1px solid hsl(${i*47%360},60%,80%)` }}>{t}</span>
                ))
              : <span style={{ color:'#4a5568', fontSize:12 }}>No themes found.</span>}
          </div>
        </div>

        {/* Model Info badge */}
        <div style={{ padding:'14px 18px', background:'rgba(108,99,255,0.08)', border:'1px solid rgba(108,99,255,0.25)', borderRadius:14, minWidth:160, textAlign:'center' }}>
          <div style={{ fontSize:11, color:'#8892a4', fontWeight:600, marginBottom:6 }}>🧠 ML Model</div>
          {report.model_info?.trained ? (
            <>
              <div style={{ fontSize:13, fontWeight:700, color:'#22c55e' }}>Trained ✓</div>
              <div style={{ fontSize:11, color:'#8892a4', marginTop:4 }}>
                {report.model_info.review_count} reviews<br />
                Acc: {report.model_info.accuracy ? `${(report.model_info.accuracy*100).toFixed(1)}%` : 'N/A'}<br />
                {report.model_info.version}
              </div>
            </>
          ) : (
            <>
              <div style={{ fontSize:13, fontWeight:700, color:'#f59e0b' }}>Heuristic Mode</div>
              <div style={{ fontSize:10, color:'#8892a4', marginTop:4 }}>Train model for higher accuracy</div>
            </>
          )}
        </div>
      </div>

      {/* ── Source Breakdown ── */}
      {Object.keys(report.source_breakdown).length > 0 && (
        <div style={{ padding:'16px 18px', background:'var(--bg-primary)', border:'1px solid var(--border)', borderRadius:14, marginBottom:16 }}>
          <div style={{ fontSize:13, fontWeight:700, color:'var(--text-primary)', marginBottom:12 }}>📊 Source Breakdown</div>
          <div style={{ display:'flex', gap:12, flexWrap:'wrap' }}>
            {Object.entries(report.source_breakdown).map(([src, stat]) => {
              const color = SOURCE_COLORS[src] || '#6c63ff';
              return (
                <div key={src} style={{ flex:1, minWidth:110, padding:14, background:`${color}10`, border:`1px solid ${color}30`, borderRadius:14 }}>
                  <div style={{ fontSize:13, fontWeight:700, color, marginBottom:6 }}>{src}</div>
                  <div style={{ fontSize:20, fontWeight:800, color:'var(--text-primary)' }}>{stat.total}</div>
                  <div style={{ fontSize:10, color:'#8892a4', marginTop:4 }}>⭐ {stat.avg_rating} · 😊 {stat.positive} · 😞 {stat.negative}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Actions ── */}
      <div style={{ display:'flex', justifyContent:'flex-end', gap:10 }}>
        <button onClick={() => window.print()} style={{ padding:'10px 20px', background:'rgba(108,99,255,0.15)', border:'1px solid rgba(108,99,255,0.4)', borderRadius:10, color:'#6c63ff', fontSize:13, fontWeight:600, cursor:'pointer', fontFamily:'Inter,sans-serif' }}>
          🖨️ Print / Export PDF
        </button>
        <button onClick={onClose} style={{ padding:'10px 20px', background:'var(--bg-secondary)', border:'1px solid var(--border)', borderRadius:10, color:'var(--text-secondary)', fontSize:13, fontWeight:600, cursor:'pointer', fontFamily:'Inter,sans-serif' }}>
          Close Report
        </button>
      </div>
    </div>
  );
}
