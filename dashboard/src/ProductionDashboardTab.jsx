import { useState, useEffect } from "react";
import {
    AreaChart, Area, BarChart, Bar, ReferenceLine,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
    Factory, Gauge, Package, ClipboardList, AlertTriangle, Truck, Loader2,
} from "lucide-react";
import {
    T, fetchProductionMetrics, fetchProductionDaily,
    fetchProductionDemandSupply, fetchProductionInventory, fetchForecast,
} from "./api";
import { KpiCard } from "./components";

// Last 6 months as selectable options
const MONTH_OPTIONS = Array.from({ length: 6 }, (_, i) => {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() - i);
    return {
        value: d.toISOString().slice(0, 7),
        label: d.toLocaleString("en-IN", { month: "short", year: "2-digit" }),
    };
});

function trendPct(curr, prev) {
    if (!prev || prev === 0) return null;
    const delta = ((curr - prev) / Math.abs(prev)) * 100;
    return { text: (delta >= 0 ? "+" : "") + delta.toFixed(1) + "%", up: delta >= 0 };
}

const card = {
    background: T.cardBg,
    border: "1px solid " + T.cardBorder,
    borderRadius: 14,
    padding: 20,
    boxShadow: T.cardShadow,
};

function useApi(fetchFn, deps = []) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    useEffect(() => {
        setLoading(true);
        fetchFn().then((d) => { setData(d); setLoading(false); });
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

const numFmt = (n) => {
    if (n == null) return "—";
    return n.toLocaleString("en-IN");
};

const UnitTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null;
    return (
        <div style={{ background: "#fff", border: "1px solid " + T.cardBorder, borderRadius: 10, padding: "10px 14px", fontSize: 12, boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}>
            <div style={{ color: T.textMuted, marginBottom: 6, fontWeight: 600 }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: p.color }} />
                    <span style={{ color: T.textMuted }}>{p.name}:</span>
                    <span className="mono" style={{ color: T.heading, fontWeight: 600 }}>{numFmt(p.value)}</span>
                </div>
            ))}
        </div>
    );
};

const STATUS_BADGE = {
    CRITICAL: { color: T.red, bg: T.redSoft },
    LOW:      { color: T.orange, bg: T.orangeSoft },
    HEALTHY:  { color: T.green, bg: T.greenSoft },
};

export default function ProductionDashboardTab() {
    const [selectedMonth, setSelectedMonth] = useState(MONTH_OPTIONS[0].value);

    const { data: metrics, loading: mLoading }       = useApi(() => fetchProductionMetrics(selectedMonth), [selectedMonth]);
    const { data: dailyData, loading: ddLoading }     = useApi(() => fetchProductionDaily(selectedMonth), [selectedMonth]);
    const { data: demandSupply, loading: dsLoading }  = useApi(fetchProductionDemandSupply);
    const { data: inventory, loading: invLoading }    = useApi(fetchProductionInventory);
    const { data: forecastData, loading: fcLoading }  = useApi(() => fetchForecast(20));

    // Trend computations
    const prodTrend   = metrics ? trendPct(metrics.actual_produced, metrics.prev_actual)     : null;
    const utilTrend   = metrics ? trendPct(metrics.utilization_pct, metrics.prev_utilization) : null;
    const pendTrend   = metrics ? trendPct(metrics.pending_orders,  metrics.prev_pending)     : null;
    const fulfTrend   = metrics ? trendPct(metrics.order_fulfill_pct, metrics.prev_fulfill_pct) : null;

    const selectedMonthLabel = MONTH_OPTIONS.find((m) => m.value === selectedMonth)?.label || selectedMonth;

    // Aggregate daily data: group by date, sum planned/actual across products
    const batchChartData = (dailyData || []).reduce((acc, r) => {
        const existing = acc.find((a) => a.planned_date === r.planned_date);
        if (existing) {
            existing.planned += r.planned;
            existing.actual += r.actual;
        } else {
            acc.push({ planned_date: r.planned_date, label: r.label, planned: r.planned, actual: r.actual });
        }
        return acc;
    }, []);

    // Build combined historical + forecast timeline for the demand chart
    // Historical: solid areas (produced, ordered). Forecast: dashed line (forecast_qty), no fill.
    const combinedDemandChart = (() => {
        const historical = (demandSupply || []).map(r => ({
            label: r.month,
            ym: r.ym,
            produced: r.produced,
            ordered: r.ordered,
            committed: r.committed,
            forecast: null,  // no forecast in historical period
            isForecast: false,
        }));

        // Aggregate weekly forecast data by calendar month
        const forecastByMonth = {};
        if (forecastData?.products) {
            Object.values(forecastData.products).forEach(productData => {
                (productData.weekly_forecast || []).forEach(week => {
                    const ym = week.week_start.slice(0, 7);  // "YYYY-MM"
                    const mon = new Date(week.week_start + "T00:00:00")
                        .toLocaleString("en-IN", { month: "short" });
                    if (!forecastByMonth[ym]) forecastByMonth[ym] = { label: mon, ym, total: 0 };
                    forecastByMonth[ym].total += week.forecast_qty;
                });
            });
        }

        // Only include future months not already in historical
        const historicalYms = new Set(historical.map(r => r.ym));
        const futureMonths = Object.values(forecastByMonth)
            .filter(m => !historicalYms.has(m.ym))
            .sort((a, b) => a.ym.localeCompare(b.ym))
            .slice(0, 5)
            .map(m => ({
                label: m.label,
                ym: m.ym,
                produced: null,
                ordered: null,
                committed: null,
                forecast: m.total,
                isForecast: true,
            }));

        // Bridge point: last historical point gets forecast value for visual continuity
        if (historical.length > 0 && futureMonths.length > 0) {
            const last = historical[historical.length - 1];
            last.forecast = futureMonths[0].forecast;  // connect the lines
        }

        return [...historical, ...futureMonths];
    })();

    // Index of the last historical point (for ReferenceLine)
    const todayIndex = combinedDemandChart.findLastIndex(r => !r.isForecast);

    return (
        <div style={{ maxWidth: 1400, margin: "0 auto" }}>
            {/* Month selector */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 18 }}>
                <span style={{ fontSize: 12, color: T.textMuted, fontWeight: 600, marginRight: 4 }}>Period:</span>
                {MONTH_OPTIONS.map((m) => (
                    <button key={m.value} onClick={() => setSelectedMonth(m.value)} style={{
                        padding: "5px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                        border: "1px solid " + (selectedMonth === m.value ? T.primary : T.cardBorder),
                        background: selectedMonth === m.value ? T.primary : "#fff",
                        color: selectedMonth === m.value ? "#fff" : T.textMuted,
                        cursor: "pointer", fontFamily: "inherit", transition: "all .15s",
                    }}>{m.label}</button>
                ))}
            </div>

            {/* 6 KPI Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 16, marginBottom: 22 }}>
                {mLoading ? Array(6).fill(0).map((_, i) => (
                    <div key={i} style={{ ...card, height: 120, display: "flex", alignItems: "center", justifyContent: "center" }}><Spinner /></div>
                )) : <>
                    <KpiCard
                        title="Production Output" value={numFmt(metrics?.actual_produced)}
                        trend={prodTrend?.text} trendUp={prodTrend?.up ?? true}
                        icon={Factory} bgColor={T.tealSoft} iconColor={T.teal} delay={0}
                        sub={`${numFmt(metrics?.actual_produced)} of ${numFmt(metrics?.planned_production)} planned`}
                    />
                    <KpiCard
                        title="Capacity Utilization" value={(metrics?.utilization_pct ?? 0) + "%"}
                        trend={utilTrend?.text} trendUp={utilTrend?.up ?? true}
                        icon={Gauge} bgColor={T.primarySoft} iconColor={T.primary} delay={0.04}
                        sub={`${numFmt(metrics?.actual_produced)} / ${numFmt(metrics?.total_capacity)} capacity`}
                    />
                    <KpiCard
                        title="Available Stock" value={numFmt(metrics?.available_stock)}
                        icon={Package} bgColor={T.greenSoft} iconColor={T.green} delay={0.08}
                        sub={`${numFmt(metrics?.total_reserved)} reserved of ${numFmt(metrics?.total_stock)} total`}
                    />
                    <KpiCard
                        title="Pending Orders" value={metrics?.pending_orders ?? "—"}
                        trend={pendTrend?.text} trendUp={pendTrend ? !pendTrend.up : false}
                        icon={ClipboardList} bgColor={T.orangeSoft} iconColor={T.orange} delay={0.12}
                        sub={`${numFmt(metrics?.pending_units)} units to fulfill`}
                    />
                    <KpiCard
                        title="Safety Stock Alerts" value={metrics?.safety_breaches ?? 0}
                        icon={AlertTriangle} bgColor={T.redSoft} iconColor={T.red} delay={0.16}
                        trendUp={false}
                        sub="products below safety level"
                    />
                    <KpiCard
                        title="Order Fulfillment" value={(metrics?.order_fulfill_pct ?? 0) + "%"}
                        trend={fulfTrend?.text} trendUp={fulfTrend?.up ?? true}
                        icon={Truck} bgColor={T.purpleSoft} iconColor={T.purple} delay={0.2}
                        sub={`${metrics?.delivered_orders ?? 0} of ${metrics?.total_orders ?? 0} orders delivered`}
                    />
                </>}
            </div>

            {/* Capacity Banner */}
            <div style={{ background: "linear-gradient(135deg,#0ea5e9,#22c55e)", borderRadius: 14, padding: "16px 24px", marginBottom: 22, display: "flex", alignItems: "center", gap: 16 }}>
                <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, color: "#fff" }}>
                    {mLoading ? "…" : (metrics?.utilization_pct ?? 0) + "%"}
                </div>
                <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>
                        {mLoading ? "Loading production data…" : `${selectedMonthLabel} production is ${metrics?.utilization_pct ?? 0}% of capacity`}
                    </div>
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", marginTop: 2 }}>
                        {mLoading ? "" : `${numFmt(metrics?.actual_produced)} units produced · ${numFmt(metrics?.total_capacity)} monthly capacity`}
                    </div>
                </div>
            </div>

            {/* Charts Row 1: Production Batches + Demand vs Supply */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 22 }}>
                {/* Production Batches */}
                <div style={{ ...card }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Production Batches</h3>
                    <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 14 }}>Planned vs actual output per batch</p>
                    <div style={{ display: "flex", gap: 12, marginBottom: 10, fontSize: 10, color: T.textMuted }}>
                        {[{ l: "Planned", c: T.primary }, { l: "Actual", c: T.green }].map((x) => (
                            <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                <span style={{ width: 10, height: 3, background: x.c, borderRadius: 2, display: "inline-block" }} />{x.l}
                            </span>
                        ))}
                    </div>
                    <div style={{ height: 290 }}>
                        {ddLoading ? <Spinner /> : (
                            <ResponsiveContainer>
                                <BarChart data={batchChartData} barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ededf0" />
                                    <XAxis dataKey="label" tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <Tooltip content={<UnitTooltip />} />
                                    <Bar dataKey="planned" fill={T.primary} name="Planned" radius={[3, 3, 0, 0]} fillOpacity={0.4} />
                                    <Bar dataKey="actual" fill={T.green} name="Actual" radius={[3, 3, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>

                {/* Demand vs Supply + Forecast */}
                <div style={{ ...card }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 2 }}>
                        <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Demand vs Supply & Forecast</h3>
                        <span style={{ fontSize: 10, fontWeight: 600, color: T.orange, background: T.orangeSoft, padding: "2px 8px", borderRadius: 5 }}>AI Forecast →</span>
                    </div>
                    <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 10 }}>Historical actuals (solid) merging into AI demand forecast (dashed)</p>
                    <div style={{ display: "flex", gap: 12, marginBottom: 10, fontSize: 10, color: T.textMuted }}>
                        {[
                            { l: "Produced", c: T.green },
                            { l: "Ordered", c: T.primary },
                            { l: "Forecast", c: T.orange, dashed: true },
                        ].map((x) => (
                            <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                <span style={{
                                    width: 10, height: 2, background: x.c, borderRadius: 2,
                                    display: "inline-block",
                                    borderTop: x.dashed ? `2px dashed ${x.c}` : "none",
                                    background: x.dashed ? "none" : x.c,
                                }} />{x.l}
                            </span>
                        ))}
                        <span style={{ color: T.textLight, marginLeft: 4 }}>| Dashed = future</span>
                    </div>
                    <div style={{ height: 290 }}>
                        {(dsLoading || fcLoading) ? <Spinner /> : (
                            <ResponsiveContainer>
                                <AreaChart data={combinedDemandChart}>
                                    <defs>
                                        <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={T.green} stopOpacity={0.2} />
                                            <stop offset="100%" stopColor={T.green} stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="og" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={T.primary} stopOpacity={0.15} />
                                            <stop offset="100%" stopColor={T.primary} stopOpacity={0} />
                                        </linearGradient>
                                        <linearGradient id="fg" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={T.orange} stopOpacity={0.12} />
                                            <stop offset="100%" stopColor={T.orange} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ededf0" />
                                    <XAxis dataKey="label" tick={{ fill: T.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <Tooltip content={<UnitTooltip />} />
                                    {/* Vertical "Today" divider at last historical point */}
                                    {todayIndex >= 0 && (
                                        <ReferenceLine
                                            x={combinedDemandChart[todayIndex]?.label}
                                            stroke={T.textLight}
                                            strokeDasharray="4 3"
                                            label={{ value: "Today", position: "insideTopRight", fontSize: 9, fill: T.textLight }}
                                        />
                                    )}
                                    {/* Historical: solid areas */}
                                    <Area type="monotone" dataKey="produced" stroke={T.green} strokeWidth={2.5} fill="url(#pg)" name="Produced" connectNulls={false} />
                                    <Area type="monotone" dataKey="ordered" stroke={T.primary} strokeWidth={2} fill="url(#og)" name="Ordered" connectNulls={false} />
                                    {/* Forecast: dashed line with light fill */}
                                    <Area type="monotone" dataKey="forecast" stroke={T.orange} strokeWidth={2} fill="url(#fg)" strokeDasharray="7 4" name="Forecast" connectNulls={false} dot={{ fill: T.orange, r: 3 }} />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>
            </div>

            {/* Charts Row 2: Product Inventory + Incoming Stock */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 22 }}>
                {/* Product Inventory Status */}
                <div style={{ ...card }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Inventory by Product</h3>
                    <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 14 }}>Current stock vs safety & reorder levels</p>
                    <div style={{ display: "flex", gap: 12, marginBottom: 10, fontSize: 10, color: T.textMuted }}>
                        {[{ l: "Available", c: T.green }, { l: "Reserved", c: T.orange }, { l: "Safety Stock", c: T.red }, { l: "Reorder Level", c: T.primary }].map((x) => (
                            <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                                <span style={{ width: 10, height: x.c === T.red || x.c === T.primary ? 2 : 3, background: x.c, borderRadius: 2, display: "inline-block", borderTop: x.c === T.red || x.c === T.primary ? "1px dashed " + x.c : "none" }} />{x.l}
                            </span>
                        ))}
                    </div>
                    <div style={{ height: 220 }}>
                        {invLoading ? <Spinner /> : (
                            <ResponsiveContainer>
                                <BarChart data={inventory || []} layout="vertical" barCategoryGap="25%">
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ededf0" horizontal={false} />
                                    <XAxis type="number" tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} />
                                    <YAxis type="category" dataKey="product" tick={{ fill: T.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} width={100} />
                                    <Tooltip content={<UnitTooltip />} />
                                    <Bar dataKey="available" fill={T.green} name="Available" radius={[0, 3, 3, 0]} stackId="stock" />
                                    <Bar dataKey="reserved" fill={T.orange} name="Reserved" radius={[0, 3, 3, 0]} stackId="stock" />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </div>

                {/* Incoming Stock Summary */}
                <div style={{ ...card }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Incoming Stock</h3>
                    <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 14 }}>Expected arrivals from production</p>
                    {invLoading ? <Spinner /> : (
                        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                            {(inventory || []).map((item, i) => {
                                const badge = STATUS_BADGE[item.status] || STATUS_BADGE.HEALTHY;
                                return (
                                    <div key={i} style={{ padding: "16px 18px", background: T.bg, borderRadius: 12 }}>
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                                            <span style={{ fontSize: 13, fontWeight: 700, color: T.heading }}>{item.product}</span>
                                            <span style={{ fontSize: 10, fontWeight: 600, color: badge.color, background: badge.bg, padding: "3px 10px", borderRadius: 6 }}>{item.status}</span>
                                        </div>
                                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
                                            <div>
                                                <div style={{ fontSize: 10, color: T.textLight, marginBottom: 2 }}>Available</div>
                                                <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: T.heading }}>{numFmt(item.available)}</div>
                                            </div>
                                            <div>
                                                <div style={{ fontSize: 10, color: T.textLight, marginBottom: 2 }}>Incoming</div>
                                                <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: item.incoming_qty > 0 ? T.teal : T.textLight }}>{item.incoming_qty > 0 ? "+" + numFmt(item.incoming_qty) : "—"}</div>
                                            </div>
                                            <div>
                                                <div style={{ fontSize: 10, color: T.textLight, marginBottom: 2 }}>Days of Cover</div>
                                                <div className="mono" style={{ fontSize: 16, fontWeight: 700, color: item.days_of_cover < 7 ? T.red : item.days_of_cover < 14 ? T.orange : T.green }}>{item.days_of_cover >= 999 ? "∞" : item.days_of_cover + "d"}</div>
                                            </div>
                                        </div>
                                        {item.next_arrival && (
                                            <div style={{ fontSize: 10, color: T.textMuted, marginTop: 6 }}>Next arrival: {item.next_arrival}</div>
                                        )}
                                    </div>
                                );
                            })}
                            {(!inventory || inventory.length === 0) && (
                                <div style={{ textAlign: "center", padding: 24, color: T.textMuted, fontSize: 12 }}>No inventory data available</div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* Inventory Health Table */}
            <div style={{ ...card, marginBottom: 24 }}>
                <div style={{ marginBottom: 14 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Inventory Health</h3>
                    <p style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>Stock levels, safety thresholds, and replenishment status</p>
                </div>
                {invLoading ? <Spinner /> : (
                    <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 3px" }}>
                        <thead>
                            <tr>
                                {["Product", "On Hand", "Reserved", "Available (ATP)", "Safety Stock", "Reorder Level", "Status", "Incoming", "Days of Cover"].map((h) => (
                                    <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontSize: 10.5, fontWeight: 600, color: T.textLight, textTransform: "uppercase", letterSpacing: ".4px", borderBottom: "1px solid " + T.cardBorder }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {(inventory || []).map((r, i) => {
                                const badge = STATUS_BADGE[r.status] || STATUS_BADGE.HEALTHY;
                                return (
                                    <tr key={i}
                                        onMouseEnter={(e) => (e.currentTarget.style.background = T.bg)}
                                        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                                        style={{ transition: "background .15s" }}
                                    >
                                        <td style={{ padding: "10px 12px", borderRadius: "8px 0 0 8px" }}>
                                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                                <div style={{ width: 30, height: 30, borderRadius: 8, background: T.tealSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                    <Package size={14} color={T.teal} />
                                                </div>
                                                <div>
                                                    <div style={{ fontSize: 12.5, fontWeight: 600, color: T.heading }}>{r.product}</div>
                                                    <div style={{ fontSize: 10, color: T.textLight }}>{r.product_code}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12 }}>{numFmt(r.on_hand)}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted }}>{numFmt(r.reserved)}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12, fontWeight: 600, color: T.heading }}>{numFmt(r.available)}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted }}>{numFmt(r.safety_stock)}</td>
                                        <td className="mono" style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted }}>{numFmt(r.reorder_level)}</td>
                                        <td style={{ padding: "10px 12px" }}>
                                            <span style={{ fontSize: 10, fontWeight: 600, color: badge.color, background: badge.bg, padding: "3px 10px", borderRadius: 6 }}>{r.status}</span>
                                        </td>
                                        <td style={{ padding: "10px 12px" }}>
                                            {r.incoming_qty > 0 ? (
                                                <div>
                                                    <span className="mono" style={{ fontSize: 12, fontWeight: 600, color: T.teal }}>+{numFmt(r.incoming_qty)}</span>
                                                    {r.next_arrival && <div style={{ fontSize: 9, color: T.textLight, marginTop: 1 }}>{r.next_arrival}</div>}
                                                </div>
                                            ) : (
                                                <span style={{ fontSize: 11, color: T.textLight }}>—</span>
                                            )}
                                        </td>
                                        <td style={{ padding: "10px 12px", borderRadius: "0 8px 8px 0" }}>
                                            <span className="mono" style={{
                                                fontSize: 12, fontWeight: 600,
                                                color: r.days_of_cover >= 999 ? T.green : r.days_of_cover < 7 ? T.red : r.days_of_cover < 14 ? T.orange : T.green,
                                            }}>
                                                {r.days_of_cover >= 999 ? "∞" : r.days_of_cover + " days"}
                                            </span>
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
