import { useState, useEffect } from "react";
import {
    AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
    MapPin, IndianRupee, Target, AlertTriangle, Building2, Truck,
    Filter, ArrowUpRight, Package, Loader2,
} from "lucide-react";
import {
    T, fmt, fetchMetrics, fetchDealers, fetchRevenueChart,
    fetchCommitmentPipeline, fetchSalesTeam, fetchRecentActivity, fetchWeeklyPipeline
} from "./api";
import { KpiCard, FilterBtn, CTooltip, ComingSoonBtn } from "./components";

// Last 6 months as selectable options
const MONTH_OPTIONS = Array.from({ length: 6 }, (_, i) => {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() - i);
    return {
        value: d.toISOString().slice(0, 7),
        label: d.toLocaleString('en-IN', { month: 'short', year: '2-digit' }),
    };
});

// Compute % change between current and previous value
function trendPct(curr, prev) {
    if (!prev || prev === 0) return null;
    const delta = (curr - prev) / Math.abs(prev) * 100;
    return { text: (delta >= 0 ? "+" : "") + delta.toFixed(1) + "%", up: delta >= 0 };
}
import LeafletMap from "./LeafletMap";
import { DEALER_BY_CAT } from "./data"; // static category counts

const card = { background: T.cardBg, border: "1px solid " + T.cardBorder, borderRadius: 14, padding: 20, boxShadow: T.cardShadow };

const STATUS_COLORS = {
    Converted: "#22c55e", Pending: "#f59e0b", Partial: "#6366f1",
    Expired: "#ef4444", Cancelled: "#8b8fad"
};

function useApi(fetchFn, deps = []) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        setLoading(true);
        fetchFn().then(d => { setData(d); setLoading(false); });
    }, deps);
    return { data, loading };
}

function Spinner() {
    return (
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: T.textLight }}>
            <Loader2 size={24} style={{ animation: "spin 1s linear infinite" }} />
            <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
        </div>
    );
}

export default function DashboardTab() {
    const [mapF, setMapF] = useState({ atRiskOnly: false, category: "All" });
    const [openF, setOpenF] = useState(null);
    const [selectedMonth, setSelectedMonth] = useState(MONTH_OPTIONS[0].value);

    const { data: metrics, loading: mLoading } = useApi(() => fetchMetrics(selectedMonth), [selectedMonth]);
    const { data: dealers, loading: dLoading } = useApi(fetchDealers);
    const { data: revenueChart, loading: rcLoading } = useApi(fetchRevenueChart);
    const { data: commitPipeline, loading: cpLoading } = useApi(() => fetchCommitmentPipeline(selectedMonth), [selectedMonth]);
    const { data: salesTeam, loading: stLoading } = useApi(() => fetchSalesTeam(selectedMonth), [selectedMonth]);
    const { data: recentActivity, loading: raLoading } = useApi(() => fetchRecentActivity(selectedMonth), [selectedMonth]);
    const { data: weeklyPipeline, loading: wpLoading } = useApi(() => fetchWeeklyPipeline(selectedMonth), [selectedMonth]);

    // Trend calculations vs previous month
    const revTrend    = metrics ? trendPct(metrics.revenue,       metrics.prev_revenue)         : null;
    const collTrend   = metrics ? trendPct(metrics.collections,   metrics.prev_collections)     : null;
    const visitTrend  = metrics ? trendPct(metrics.visited_30d,   metrics.prev_visited)         : null;
    const pipeTrend   = metrics ? trendPct(metrics.pipeline_count, metrics.prev_pipeline_count) : null;

    const selectedMonthLabel = MONTH_OPTIONS.find(m => m.value === selectedMonth)?.label || selectedMonth;

    // Compute dealer counts by category from live data
    const dealerByCat = dealers ? [
        { name: "Platinum (A)", value: dealers.filter(d => d.category === "A").length, color: T.primary },
        { name: "Gold (B)", value: dealers.filter(d => d.category === "B").length, color: T.orange },
        { name: "Silver (C)", value: dealers.filter(d => d.category === "C").length, color: T.textMuted },
    ] : DEALER_BY_CAT;

    return (
        <div style={{ maxWidth: 1400, margin: "0 auto" }} onClick={() => openF && setOpenF(null)}>

            {/* Month selector */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18 }}>
                <span style={{ fontSize: 12, color: T.textMuted, fontWeight: 600, marginRight: 4 }}>Period:</span>
                {MONTH_OPTIONS.map(m => (
                    <button key={m.value} onClick={() => setSelectedMonth(m.value)} style={{
                        padding: "5px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                        border: "1px solid " + (selectedMonth === m.value ? T.primary : T.cardBorder),
                        background: selectedMonth === m.value ? T.primary : "#fff",
                        color: selectedMonth === m.value ? "#fff" : T.textMuted,
                        cursor: "pointer", fontFamily: "inherit", transition: "all .15s",
                    }}>{m.label}</button>
                ))}
            </div>

            {/* KPIs */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 16, marginBottom: 22 }}>
                {mLoading ? Array(6).fill(0).map((_, i) => (
                    <div key={i} style={{ ...card, height: 120, display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner /></div>
                )) : <>
                    <KpiCard title="Total Revenue" value={fmt(metrics?.revenue)} trend={revTrend?.text} trendUp={revTrend?.up ?? true} icon={IndianRupee} bgColor={T.pinkSoft} iconColor={T.pink} delay={0} sub="vs prev month" />
                    <KpiCard title="Active Dealers" value={metrics?.active_dealers ?? "—"} icon={Building2} bgColor={T.tealSoft} iconColor={T.teal} delay={.04} sub="5 territories" />
                    <KpiCard title="Commitment Pipeline" value={fmt(metrics?.pipeline_value)} trend={pipeTrend?.text ?? (metrics?.pipeline_count + " items")} trendUp={pipeTrend?.up ?? true} icon={Target} bgColor={T.purpleSoft} iconColor={T.purple} delay={.08} sub="Pending + partial" />
                    <KpiCard title="Visit Coverage" value={dealers ? Math.round(dealers.filter(d => d.last_visit !== "No visits").length / dealers.length * 100) + "%" : "—"} trend={visitTrend?.text} trendUp={visitTrend?.up ?? true} icon={MapPin} bgColor={T.greenSoft} iconColor={T.green} delay={.12} sub={dealers ? `${dealers.filter(d => d.last_visit !== "No visits").length}/${dealers.length} visited` : ""} />
                    <KpiCard title="Collections" value={fmt(metrics?.collections)} trend={collTrend?.text ?? (metrics?.target_pct + "%")} trendUp={collTrend?.up ?? true} icon={Truck} bgColor={T.orangeSoft} iconColor={T.orange} delay={.16} sub={"Of target " + fmt(metrics?.monthly_target)} />
                    <KpiCard title="At-Risk Dealers" value={metrics?.at_risk ?? "—"} trendUp={false} icon={AlertTriangle} bgColor={T.redSoft} iconColor={T.red} delay={.2} sub="Need attention" />
                </>}
            </div>

            {/* Target Banner */}
            <div style={{ background: "linear-gradient(135deg,#f59e0b,#f97316)", borderRadius: 14, padding: "16px 24px", marginBottom: 22, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                    <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, color: "#fff" }}>
                        {mLoading ? "…" : (metrics?.target_pct ?? 0) + "%"}
                    </div>
                    <div>
                        <div style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>
                            {mLoading ? "Loading target data…" : `${selectedMonthLabel} target is ${metrics?.target_pct ?? 0}% complete`}
                        </div>
                        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", marginTop: 2 }}>
                            {mLoading ? "" : `${fmt(metrics?.collections)} of ${fmt(metrics?.monthly_target)} collected`}
                        </div>
                    </div>
                </div>
                <ComingSoonBtn>
                    <button style={{ background: "rgba(255,255,255,0.2)", border: "1px solid rgba(255,255,255,0.3)", borderRadius: 8, padding: "7px 16px", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>View Details →</button>
                </ComingSoonBtn>
            </div>

            {/* Map + Pipeline */}
            <div style={{ display: "grid", gridTemplateColumns: "1.45fr 1fr", gap: 20, marginBottom: 22 }}>
                <div style={{ ...card }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                        <div>
                            <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Dealer Network Map</h3>
                            <p style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>
                                {dLoading ? "Loading…" : `${(dealers || []).filter(d => {
                                    if (mapF.atRiskOnly && !["at-risk", "critical"].includes(d.health)) return false;
                                    if (mapF.category !== "All" && d.category !== mapF.category) return false;
                                    return true;
                                }).length} dealers · hover for details · scroll to zoom`}
                            </p>
                        </div>
                        <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
                            <button onClick={() => setMapF(f => ({ ...f, atRiskOnly: !f.atRiskOnly }))} style={{
                                padding: "5px 12px", borderRadius: 8, fontSize: 11, fontWeight: 600, cursor: "pointer",
                                border: "1px solid " + (mapF.atRiskOnly ? T.red : T.cardBorder),
                                background: mapF.atRiskOnly ? T.redSoft : "#fff",
                                color: mapF.atRiskOnly ? T.red : T.textMuted,
                                fontFamily: "inherit", display: "flex", alignItems: "center", gap: 4,
                            }}>
                                <AlertTriangle size={11} />At-Risk Only
                            </button>
                            <FilterBtn label="Cat" options={["All", "A", "B", "C"]} value={mapF.category} onSelect={v => { setMapF(f => ({ ...f, category: v })); setOpenF(null); }} open={openF === "cat"} onToggle={() => setOpenF(openF === "cat" ? null : "cat")} />
                        </div>
                    </div>
                    <div style={{ display: "flex", gap: 14, marginBottom: 10, fontSize: 10, color: T.textMuted }}>
                        {[{ l: "Healthy", c: T.green }, { l: "At-Risk", c: T.orange }, { l: "Critical", c: T.red }].map(x => (
                            <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                <span style={{ width: 9, height: 9, borderRadius: "50%", background: x.c, display: "inline-block" }} />{x.l}
                            </span>
                        ))}
                        <span style={{ color: T.textLight }}>| Pin size = Category (A &gt; B &gt; C)</span>
                    </div>
                    <div style={{ height: 360, borderRadius: 12, overflow: "hidden" }}>
                        {dLoading ? <Spinner /> : <LeafletMap dealers={dealers || []} filters={mapF} />}
                    </div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                    <div style={{ ...card, flex: 1 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Commitment Pipeline</h3>
                        <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 12 }}>From dealer conversations · value = qty × price</p>
                        {cpLoading ? <Spinner /> : (
                            <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                                <div style={{ width: 150, height: 150 }}>
                                    <ResponsiveContainer>
                                        <PieChart>
                                            <Pie data={commitPipeline || []} cx="50%" cy="50%" innerRadius={46} outerRadius={66} dataKey="cnt" nameKey="status" paddingAngle={3} strokeWidth={0}>
                                                {(commitPipeline || []).map((e, i) => <Cell key={i} fill={e.color} />)}
                                            </Pie>
                                            <Tooltip content={({ active, payload }) => {
                                                if (!active || !payload?.length) return null;
                                                const p = payload[0];
                                                return (
                                                    <div style={{ background: "#fff", border: "1px solid " + T.cardBorder, borderRadius: 10, padding: "10px 14px", fontSize: 12, boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}>
                                                        <div style={{ fontWeight: 700, color: p.payload.color, marginBottom: 4 }}>{p.name}</div>
                                                        <div style={{ color: T.text }}>{p.value} commitments</div>
                                                        <div style={{ color: T.textMuted, fontSize: 11, marginTop: 2 }}>{fmt(p.payload.value)}</div>
                                                    </div>
                                                );
                                            }} />
                                        </PieChart>
                                    </ResponsiveContainer>
                                </div>
                                <div style={{ flex: 1 }}>
                                    {(commitPipeline || []).map((c, i) => (
                                        <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 0", borderBottom: i < (commitPipeline.length - 1) ? "1px solid " + T.cardBorder : "none" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                                                <div style={{ width: 8, height: 8, borderRadius: "50%", background: c.color }} />
                                                <span style={{ fontSize: 12, color: T.textMuted }}>{c.status}</span>
                                            </div>
                                            <div>
                                                <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: T.heading }}>{c.cnt}</span>
                                                <span style={{ fontSize: 10, color: T.textLight, marginLeft: 6 }}>{fmt(c.value)}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                    <div style={{ ...card }}>
                        <h3 style={{ fontSize: 13, fontWeight: 700, color: T.heading, marginBottom: 12 }}>Dealers by Category</h3>
                        <div style={{ display: "flex", gap: 10 }}>
                            {dealerByCat.map((d, i) => (
                                <div key={i} style={{ flex: 1, textAlign: "center", padding: "14px 8px", background: i === 0 ? T.primarySoft : i === 1 ? T.orangeSoft : T.bg, borderRadius: 11 }}>
                                    <div className="mono" style={{ fontSize: 24, fontWeight: 800, color: d.color }}>{d.value}</div>
                                    <div style={{ fontSize: 10, color: T.textMuted, marginTop: 2 }}>{d.name}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Revenue Chart + Top Dealers */}
            <div style={{ display: "grid", gridTemplateColumns: "1.45fr 1fr", gap: 20, marginBottom: 22 }}>
                <div style={{ ...card }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                        <div>
                            <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Revenue Analytics</h3>
                            <div style={{ display: "flex", gap: 16, marginTop: 4, fontSize: 11 }}>
                                <span style={{ color: T.textMuted }}>Total <strong style={{ color: T.heading }}>{fmt((revenueChart || []).reduce((s, r) => s + r.revenue, 0))}</strong></span>
                                <span style={{ color: T.textMuted }}>Collections <strong style={{ color: T.heading }}>{fmt((revenueChart || []).reduce((s, r) => s + r.collections, 0))}</strong></span>
                            </div>
                        </div>
                        <div style={{ display: "flex", gap: 12, fontSize: 10, color: T.textMuted }}>
                            {[{ n: "Revenue", c: T.primary }, { n: "Target", c: T.pink }, { n: "Collections", c: T.green }].map(x => (
                                <span key={x.n} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                    <span style={{ width: 10, height: 3, background: x.c, borderRadius: 2, display: "inline-block" }} />{x.n}
                                </span>
                            ))}
                        </div>
                    </div>
                    <div style={{ height: 260 }}>
                        {rcLoading ? <Spinner /> : (
                            <ResponsiveContainer>
                                <AreaChart data={revenueChart || []}>
                                    <defs>
                                        <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.primary} stopOpacity={.2} /><stop offset="100%" stopColor={T.primary} stopOpacity={0} /></linearGradient>
                                        <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.green} stopOpacity={.15} /><stop offset="100%" stopColor={T.green} stopOpacity={0} /></linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ededf0" />
                                    <XAxis dataKey="month" tick={{ fill: T.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => v >= 100000 ? "₹" + (v / 100000).toFixed(0) + "L" : v} />
                                    <Tooltip content={<CTooltip />} />
                                    <Area type="monotone" dataKey="revenue" stroke={T.primary} strokeWidth={2.5} fill="url(#rg)" name="Revenue" />
                                    <Area type="monotone" dataKey="collections" stroke={T.green} strokeWidth={2} fill="url(#cg)" name="Collections" />
                                    <Area type="monotone" dataKey="target" stroke={T.pink} strokeWidth={2} fill="none" strokeDasharray="6 4" name="Target" />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>
                <div style={{ ...card }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Top Dealers</h3>
                        <ComingSoonBtn><span style={{ fontSize: 11, color: T.primary, fontWeight: 600, cursor: "pointer" }}>View All →</span></ComingSoonBtn>
                    </div>
                    {dLoading ? <Spinner /> : [...(dealers || [])].sort((a, b) => b.revenue - a.revenue).slice(0, 7).map((d, i) => {
                        const cols = [T.primary, T.pink, T.green, T.orange, T.teal];
                        const c = cols[i % 5];
                        return (
                            <div key={d.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px", borderRadius: 8, transition: "background .15s", cursor: "pointer" }}
                                onMouseEnter={e => e.currentTarget.style.background = T.bg}
                                onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                            >
                                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                                    <div style={{ width: 32, height: 32, borderRadius: 8, background: c + "15", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: c, flexShrink: 0 }}>{d.name.split(" ").map(w => w[0]).join("").slice(0, 2)}</div>
                                    <div>
                                        <div style={{ fontSize: 12, fontWeight: 600, color: T.heading }}>{d.name}</div>
                                        <div style={{ fontSize: 10, color: T.textLight }}>{d.city} · Cat {d.category}</div>
                                    </div>
                                </div>
                                <div style={{ textAlign: "right" }}>
                                    <div className="mono" style={{ fontSize: 13, fontWeight: 700, color: T.green }}>{fmt(d.revenue)}</div>
                                    <div style={{ fontSize: 10, color: T.textLight }}>{d.pending_commitments} pending</div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Weekly Pipeline + Activity */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 22 }}>
                <div style={{ ...card }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Weekly Commitment Flow</h3>
                    <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 14 }}>Commitments captured → converted (last 28 days)</p>
                    <div style={{ height: 220 }}>
                        {wpLoading ? <Spinner /> : (
                            <ResponsiveContainer>
                                <BarChart data={weeklyPipeline || []} barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ededf0" />
                                    <XAxis dataKey="week" tick={{ fill: T.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <Tooltip content={<CTooltip />} />
                                    <Bar dataKey="new" fill={T.teal} name="New" radius={[3, 3, 0, 0]} />
                                    <Bar dataKey="confirmed" fill={T.primary} name="Confirmed" radius={[3, 3, 0, 0]} />
                                    <Bar dataKey="fulfilled" fill={T.green} name="Fulfilled" radius={[3, 3, 0, 0]} />
                                    <Bar dataKey="overdue" fill={T.red} name="Overdue" radius={[3, 3, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>
                <div style={{ ...card }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Recent Activity</h3>
                        <ComingSoonBtn><span style={{ fontSize: 11, color: T.primary, fontWeight: 600, cursor: "pointer" }}>View All →</span></ComingSoonBtn>
                    </div>
                    {raLoading ? <Spinner /> : (
                        <div style={{ maxHeight: 250, overflow: "auto" }}>
                            {(recentActivity || []).map((a, i) => {
                                const colors = { visit: T.teal, commitment: T.primary, alert: T.red, order: T.green, collection: T.orange };
                                const bgs = { visit: T.tealSoft, commitment: T.primarySoft, alert: T.redSoft, order: T.greenSoft, collection: T.orangeSoft };
                                const icons = { visit: MapPin, commitment: Target, alert: AlertTriangle, order: Package, collection: IndianRupee };
                                const Ic = icons[a.icon] || MapPin;
                                return (
                                    <div key={i} style={{ display: "flex", gap: 10, padding: "8px 6px", borderRadius: 8, transition: "background .15s" }}
                                        onMouseEnter={e => e.currentTarget.style.background = T.bg}
                                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                                    >
                                        <div style={{ width: 32, height: 32, borderRadius: 9, flexShrink: 0, background: bgs[a.icon] || T.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                            <Ic size={14} color={colors[a.icon] || T.textMuted} />
                                        </div>
                                        <div style={{ flex: 1, minWidth: 0 }}>
                                            <div style={{ fontSize: 12, fontWeight: 600, color: T.heading }}>{a.text}</div>
                                            <div style={{ fontSize: 10, color: T.textMuted, marginTop: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.detail}</div>
                                        </div>
                                        <span style={{ fontSize: 10, color: T.textLight, whiteSpace: "nowrap", flexShrink: 0 }}>{a.time?.slice(0, 10)}</span>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {/* Sales Team */}
            <div style={{ ...card, marginBottom: 24 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <div>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Sales Team Performance</h3>
                        <p style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>Rep-level metrics this month</p>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                        <ComingSoonBtn>
                            <button style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 7, padding: "5px 12px", fontSize: 11, fontWeight: 600, display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}><Filter size={11} /> Filters</button>
                        </ComingSoonBtn>
                        <ComingSoonBtn>
                            <button style={{ background: "#fff", color: T.text, border: "1px solid " + T.cardBorder, borderRadius: 7, padding: "5px 12px", fontSize: 11, fontWeight: 500, display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}><ArrowUpRight size={11} /> Export</button>
                        </ComingSoonBtn>
                    </div>
                </div>
                {stLoading ? <Spinner /> : (
                    <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 3px" }}>
                        <thead>
                            <tr>
                                {["Sales Rep", "Territory", "Dealers", "Visits", "Target", "Achieved", "Commitments", "Conversion"].map(h => (
                                    <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontSize: 10.5, fontWeight: 600, color: T.textLight, textTransform: "uppercase", letterSpacing: ".4px", borderBottom: "1px solid " + T.cardBorder }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {(salesTeam || []).map((r, i) => {
                                const pct = r.target > 0 ? Math.round(r.achieved / r.target * 100) : 0;
                                const pc = pct >= 100 ? T.green : pct >= 80 ? T.orange : T.red;
                                const pb = pct >= 100 ? T.greenSoft : pct >= 80 ? T.orangeSoft : T.redSoft;
                                const ac = [T.primary, T.pink, T.green, T.orange, T.teal, T.purple];
                                const conv = Number(r.conversion) || 0;
                                return (
                                    <tr key={i} onMouseEnter={e => e.currentTarget.style.background = T.bg} onMouseLeave={e => e.currentTarget.style.background = "transparent"} style={{ transition: "background .15s" }}>
                                        <td style={{ padding: "10px 12px", borderRadius: "8px 0 0 8px" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                                <div style={{ width: 30, height: 30, borderRadius: 8, background: ac[i % ac.length] + "18", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: ac[i % ac.length] }}>{r.name.split(" ").map(n => n[0]).join("")}</div>
                                                <span style={{ fontSize: 12.5, fontWeight: 600, color: T.heading }}>{r.name}</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted }}>{r.territory || "—"}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12 }}>{r.dealers}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12 }}>{r.visits}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted }}>{fmt(r.target)}</td>
                                        <td style={{ padding: "10px 12px" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                                                <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: T.heading }}>{fmt(r.achieved)}</span>
                                                <span style={{ fontSize: 10, fontWeight: 600, color: pc, background: pb, padding: "2px 7px", borderRadius: 5 }}>{pct}%</span>
                                            </div>
                                        </td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12, color: T.primary, fontWeight: 600 }}>{r.commitments}</td>
                                        <td style={{ padding: "10px 12px", borderRadius: "0 8px 8px 0" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                                <div style={{ width: 52, height: 5, borderRadius: 3, background: "#ededf0", overflow: "hidden" }}>
                                                    <div style={{ width: Math.min(conv, 100) + "%", height: "100%", borderRadius: 3, background: conv >= 80 ? T.green : conv >= 65 ? T.orange : T.red }} />
                                                </div>
                                                <span className="mono" style={{ fontSize: 11, fontWeight: 600, color: conv >= 80 ? T.green : conv >= 65 ? T.orange : T.red }}>{conv}%</span>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    );
}
