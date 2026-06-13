'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import StatCard from '@/components/StatCard';
import SentimentChart from '@/components/SentimentChart';
import TopicsChart from '@/components/TopicsChart';
import FakeGauge from '@/components/FakeGauge';
import ReviewFeed from '@/components/ReviewFeed';
import AlertPanel from '@/components/AlertPanel';
import SummaryPanel from '@/components/SummaryPanel';
import SearchBar from '@/components/SearchBar';
import SearchResults from '@/components/SearchResults';
import SearchAnalytics from '@/components/SearchAnalytics';
import ReportPanel from '@/components/ReportPanel';
import ChatBot from '@/components/ChatBot';
import {
  Review, Stats, SentimentTrendPoint, TopicCount, Alert, API_BASE, WS_BASE
} from '@/lib/types';

type NavItem = 'dashboard' | 'reviews' | 'alerts' | 'topics' | 'search' | 'assistant';
interface Toast { id: number; type: 'success' | 'error' | 'info'; message: string }

export default function HomePage() {
  const [activeNav, setActiveNav] = useState<NavItem>('dashboard');
  const [stats, setStats] = useState<Stats | null>(null);
  const [trend, setTrend] = useState<SentimentTrendPoint[]>([]);
  const [topics, setTopics] = useState<TopicCount[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [scraping, setScraping] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const [searchResults, setSearchResults] = useState<Review[]>([]);
  const [searchBySource, setSearchBySource] = useState<Record<string, number>>({});
  const [searchAnalytics, setSearchAnalytics] = useState<Record<string, any> | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchedProduct, setSearchedProduct] = useState('');
  const [searchStatus, setSearchStatus] = useState<Record<string, string>>({});
  const [notAvailable, setNotAvailable] = useState<string[]>([]);
  const [report, setReport] = useState<Record<string, any> | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const toastId = useRef(0);

  const addToast = useCallback((type: Toast['type'], message: string) => {
    const id = ++toastId.current;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      const [statsRes, trendRes, topicsRes, reviewsRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/api/reviews/stats`),
        fetch(`${API_BASE}/api/reviews/sentiment-trend`),
        fetch(`${API_BASE}/api/reviews/topics`),
        fetch(`${API_BASE}/api/reviews?limit=50`),
        fetch(`${API_BASE}/api/alerts`),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (trendRes.ok) setTrend(await trendRes.json());
      if (topicsRes.ok) setTopics(await topicsRes.json());
      if (reviewsRes.ok) {
        const raw: Review[] = await reviewsRes.json();
        // Deduplicate by id
        const map = new Map(raw.map(r => [r.id, r]));
        setReviews(Array.from(map.values()));
      }
      if (alertsRes.ok) setAlerts(await alertsRes.json());
    } catch { /* Backend may not be running */ }
  }, []);

  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket(`${WS_BASE}/api/ws/feed`);
        wsRef.current = ws;
        ws.onopen = () => setWsConnected(true);
        ws.onclose = () => { setWsConnected(false); setTimeout(connect, 3000); };
        ws.onerror = () => setWsConnected(false);
        ws.onmessage = (event) => {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'new_review') {
              const r: Review = msg.data;
              setReviews((prev) => {
                const map = new Map(prev.map(x => [x.id, x]));
                map.set(r.id, r);
                return Array.from(map.values()).slice(0, 50);
              });
              setSearchResults((prev) => {
                if (prev.length === 0 && !isSearching) return prev;
                const map = new Map(prev.map(x => [x.id, x]));
                map.set(r.id, r);
                return Array.from(map.values());
              });
              fetchAll();
            } else if (msg.type === 'search_complete') {
              setIsSearching(false);
              setSearchBySource(msg.data.by_source || {});
              setNotAvailable(msg.data.not_available || []);
              addToast('success', `Found ${msg.data.total} reviews for ${msg.data.product}`);
              fetchAll();
            } else if (msg.type === 'search_started') {
              setSearchStatus({});
            }
          } catch { /* ignore */ }
        };
      } catch { /* ignore */ }
    };
    connect();
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => { clearInterval(interval); wsRef.current?.close(); };
  }, [fetchAll]);

  const handleScrape = async () => {
    setScraping(true);
    addToast('info', 'Scraping and analysing reviews…');
    try {
      const res = await fetch(`${API_BASE}/api/scrape?count=30`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        addToast('success', `${data.reviews_added} reviews added!`);
        await fetchAll();
      } else { addToast('error', 'Scrape failed.'); }
    } catch { addToast('error', 'Cannot connect to backend.'); }
    finally { setScraping(false); }
  };

  const handleSearch = async (product: string, sources: string[]) => {
    setIsSearching(true); setSearchedProduct(product);
    setSearchResults([]); setSearchBySource({});
    setSearchAnalytics(null); setReport(null);
    setSearchStatus({}); setNotAvailable([]);
    addToast('info', `Searching ${product} across ${sources.length} sites…`);
    try {
      const res = await fetch(`${API_BASE}/api/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product, sources, max_reviews_per_source: 20 }),
      });
      if (res.ok) {
        const data = await res.json();
        // Deduplicate by id
        const raw: Review[] = data.reviews || [];
        const map = new Map(raw.map((r: Review) => [r.id, r]));
        setSearchResults(Array.from(map.values()));
        setSearchBySource(data.by_source || {});
        setNotAvailable(data.not_available || []);
        setSearchAnalytics(data.analytics || null);
        addToast('success', `Found ${data.total} reviews for ${product}`);
        await fetchAll();
      } else { addToast('error', 'Search failed.'); }
    } catch { addToast('error', 'Cannot connect to backend.'); }
    finally { setIsSearching(false); }
  };

  const handleGenerateReport = async () => {
    if (searchResults.length === 0 || isGeneratingReport) return;
    setIsGeneratingReport(true); setReport(null);
    addToast('info', 'Generating AI report… this may take 20–60 seconds');
    try {
      const ids = searchResults.map((r) => r.id).filter(Boolean);
      const res = await fetch(`${API_BASE}/api/report`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product: searchedProduct, review_ids: ids }),
      });
      if (res.ok) {
        const data = await res.json();
        setReport(data);
        addToast('success', `Report ready! Score: ${data.score}/100`);
      } else { addToast('error', 'Report generation failed.'); }
    } catch { addToast('error', 'Cannot connect to backend.'); }
    finally { setIsGeneratingReport(false); }
  };

  const positiveRate = stats && stats.total > 0
    ? Math.round((stats.positive / stats.total) * 100)
    : 0;

  // Suppress unused warning
  void scraping; void handleScrape; void SummaryPanel;

  return (
    <div className="app-shell">

      {/* ── Topbar ── */}
      <header className="topbar">
        <div className="topbar-logo">
          <div className="logo-mark">BW</div>
          <div>
            <div className="logo-text">BuyWise</div>
            <div className="logo-sub">AI Review Intelligence</div>
          </div>
        </div>

        <nav className="topbar-nav">
          {([
            ['dashboard', '📊', 'Dashboard'],
            ['search',    '🔍', 'Search'],
            ['alerts',    '🚨', 'Alerts'],
            ['topics',    '🏷️', 'Topics'],
          ] as [NavItem, string, string][]).map(([key, icon, label]) => (
            <button
              key={key}
              className={`nav-link ${activeNav === key ? 'active' : ''}`}
              onClick={() => setActiveNav(key)}
            >
              <span>{icon}</span>
              {label}
              <span className="nav-dot" />
            </button>
          ))}
        </nav>

        <div className="topbar-actions">
          <div className="ws-indicator">
            <div className={`ws-dot ${wsConnected ? 'connected' : ''}`} />
            <span>{wsConnected ? 'Live' : 'Offline'}</span>
          </div>
        </div>
      </header>

      {/* ── Split Layout ── */}
      <main className="zillow-layout">

        {/* Left Pane */}
        <div className="left-pane">
          <div className="pane-search-header">
            <SearchBar
              onSearch={(p, s) => { setActiveNav('search'); handleSearch(p, s); }}
              isSearching={isSearching}
              searchStatus={searchStatus}
            />
          </div>
          <div>
            {!isSearching && notAvailable.length > 0 && (
              <div className="availability-row">
                {notAvailable.map((site) => (
                  <span key={site} style={{
                    fontSize: '11.5px', color: 'var(--cream-muted)',
                    background: 'var(--bg-raised)', padding: '3px 8px',
                    borderRadius: '6px', border: '1px solid var(--border)',
                  }}>✗ {site}</span>
                ))}
              </div>
            )}
            {(activeNav === 'search' || searchResults.length > 0) ? (
              <SearchResults
                reviews={searchResults}
                searchedProduct={searchedProduct}
                bySource={searchBySource}
                isSearching={isSearching}
              />
            ) : (
              <ReviewFeed reviews={reviews} />
            )}
          </div>
        </div>

        {/* Right Pane */}
        <div className="right-pane">

          {activeNav === 'dashboard' && (
            <div className="fade-in" style={{ maxWidth: '960px', margin: '0 auto' }}>
              <div className="dash-header">
                <div className="dash-greeting">Here&apos;s your market pulse 👋</div>
                <h1 className="page-heading">Review Intelligence Dashboard</h1>
              </div>
              <div className="stats-row" style={{ marginBottom: '16px' }}>
                <StatCard icon="📝" label="Total Reviews" value={stats?.total ?? 0} color="violet"
                  trend={stats && stats.total > 0 ? `${positiveRate}% positive` : undefined} trendDir="up" />
                <StatCard icon="✅" label="Positive" value={stats?.positive ?? 0} color="green"
                  trend={stats && stats.total > 0 ? `${positiveRate}%` : undefined} trendDir="up" />
                <StatCard icon="💔" label="Negative" value={stats?.negative ?? 0} color="red"
                  trend={stats && stats.total > 0 ? `${Math.round((stats.negative / stats.total) * 100)}%` : undefined} trendDir="down" />
                <StatCard icon="⚠️" label="Suspicious" value={stats?.fake_count ?? 0} color="orange"
                  trend={stats ? `${stats.fake_percent}% rate` : undefined} trendDir="down" />
              </div>
              <div className="charts-row">
                <div className="glass-card">
                  <div className="card-header">
                    <span className="card-title">📈 Sentiment Over Time</span>
                  </div>
                  <SentimentChart data={trend} />
                </div>
                <div className="glass-card">
                  <div className="card-header">
                    <span className="card-title">🛡️ Fake Review Detector</span>
                  </div>
                  <FakeGauge stats={stats} />
                </div>
              </div>
            </div>
          )}

          {activeNav === 'search' && (
            <div className="fade-in" style={{ maxWidth: '960px', margin: '0 auto' }}>
              <div className="section-header">
                <div>
                  <h1 className="page-heading">
                    {isSearching
                      ? `Analysing ${searchedProduct}\u2026`
                      : searchResults.length > 0
                        ? `Results for \u201c${searchedProduct}\u201d`
                        : 'Product Search & Analytics'}
                  </h1>
                  {searchResults.length > 0 && !isSearching && (
                    <div className="section-sub">
                      {searchResults.length} reviews across{' '}
                      {Object.keys(searchBySource).filter(k => searchBySource[k] > 0).join(', ')}
                    </div>
                  )}
                </div>
                {!isSearching && searchResults.length > 0 && (
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <button className="btn-primary" onClick={handleGenerateReport} disabled={isGeneratingReport}>
                      {isGeneratingReport ? <div className="spinner" /> : <span>✨</span>}
                      <span>{isGeneratingReport ? 'Generating\u2026' : 'AI Report'}</span>
                    </button>
                    <button className="btn-secondary" onClick={() => {
                      setSearchResults([]); setSearchedProduct('');
                      setSearchBySource({}); setSearchAnalytics(null); setReport(null);
                    }}>Clear</button>
                  </div>
                )}
              </div>
              {!isSearching && report && (
                <ReportPanel report={report as any} onClose={() => setReport(null)} />
              )}
              {!isSearching && searchAnalytics && searchResults.length > 0 && !report && (
                <SearchAnalytics analytics={searchAnalytics as any} product={searchedProduct} />
              )}
              {!isSearching && searchResults.length === 0 && (
                <div className="empty-state">
                  <div className="empty-icon">🔍</div>
                  <p>Search for any product on the left &mdash; I&apos;ll fetch real reviews from Amazon &amp; Flipkart and analyse them instantly.</p>
                </div>
              )}
            </div>
          )}

          {activeNav === 'topics' && (
            <div className="fade-in" style={{ maxWidth: '960px', margin: '0 auto' }}>
              <div className="section-header">
                <div>
                  <h1 className="page-heading">Topic Intelligence</h1>
                  <div className="section-sub">What customers are really talking about</div>
                </div>
              </div>
              <div className="glass-card">
                <TopicsChart data={topics} />
              </div>
            </div>
          )}

          {activeNav === 'alerts' && (
            <div className="fade-in" style={{ maxWidth: '960px', margin: '0 auto' }}>
              <div className="section-header">
                <div>
                  <h1 className="page-heading">Flagged Reviews</h1>
                  <div className="section-sub">Suspicious &amp; negative signals worth your attention</div>
                </div>
              </div>
              <div className="glass-card">
                <AlertPanel alerts={alerts} />
              </div>
            </div>
          )}

        </div>
      </main>

      {/* ── Floating AI Chatbot ── */}
      <ChatBot />

      {/* Toasts */}
      <div className="toast-container">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>{t.message}</div>
        ))}
      </div>
    </div>
  );
}
