import { useState } from "react";
import { ArrowUpRight, ArrowDownRight, ChevronDown } from "lucide-react";
import { T } from "./api";

/* ── Coming Soon wrapper ───────────────────────────────────── */
export const ComingSoonBtn = ({ children, style = {} }) => {
    const [show, setShow] = useState(false);
    return (
        <div style={{ position: "relative", display: "inline-flex" }}
            onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}>
            <div style={{ opacity: 0.45, pointerEvents: "none", cursor: "not-allowed", ...style }}>
                {children}
            </div>
            {show && (
                <div style={{
                    position: "absolute", bottom: "115%", left: "50%", transform: "translateX(-50%)",
                    background: T.heading, color: "#fff", fontSize: 10, fontWeight: 600,
                    padding: "4px 10px", borderRadius: 6, whiteSpace: "nowrap", zIndex: 9999,
                    pointerEvents: "none",
                }}>
                    Coming Soon
                    <div style={{ position: "absolute", top: "100%", left: "50%", transform: "translateX(-50%)", width: 0, height: 0, borderLeft: "5px solid transparent", borderRight: "5px solid transparent", borderTop: "5px solid " + T.heading }} />
                </div>
            )}
        </div>
    );
};

/* ── KPI Card ──────────────────────────────────────────────── */
export const KpiCard = ({ title, value, sub, trend, trendUp, icon: Icon, bgColor, iconColor, delay = 0 }) => (
    <div style={{
        background: bgColor, borderRadius: 14, padding: "20px 22px",
        animation: "slideUp .45s ease " + delay + "s both",
        transition: "transform .2s, box-shadow .2s", cursor: "default",
        boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
    }}
        onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-3px)"; e.currentTarget.style.boxShadow = "0 6px 20px rgba(0,0,0,0.08)"; }}
        onMouseLeave={e => { e.currentTarget.style.transform = "translateY(0)"; e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.02)"; }}
    >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
            <div style={{ width: 42, height: 42, borderRadius: 11, background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 2px 8px rgba(0,0,0,0.06)" }}>
                <Icon size={20} color={iconColor} />
            </div>
            {trend && (
                <div style={{ display: "flex", alignItems: "center", gap: 2, fontSize: 12, fontWeight: 600, color: trendUp ? T.green : T.red }}>
                    {trendUp ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}{trend}
                </div>
            )}
        </div>
        <div style={{ fontSize: 26, fontWeight: 800, color: T.heading, letterSpacing: "-0.5px", lineHeight: 1.1 }}>{value}</div>
        <div style={{ fontSize: 12, color: T.textMuted, marginTop: 5, fontWeight: 500 }}>{title}</div>
        {sub && <div style={{ fontSize: 11, color: T.textLight, marginTop: 2 }}>{sub}</div>}
    </div>
);

/* ── Filter Button (for map) ───────────────────────────────── */
export const FilterBtn = ({ label, options, value, onSelect, open, onToggle }) => (
    <div style={{ position: "relative" }}>
        <button onClick={onToggle} style={{
            background: value !== "All" ? T.primarySoft : "#fff",
            border: "1px solid " + (value !== "All" ? "#c7c8f2" : T.cardBorder),
            borderRadius: 8, padding: "5px 11px", color: value !== "All" ? T.primary : T.textMuted,
            fontSize: 11.5, cursor: "pointer", display: "flex", alignItems: "center", gap: 3, fontWeight: 500, fontFamily: "inherit",
        }}>
            {label}: {value} <ChevronDown size={11} />
        </button>
        {open && (
            <div style={{
                position: "absolute", top: "110%", left: 0, background: "#fff",
                border: "1px solid " + T.cardBorder, borderRadius: 10, padding: 4,
                zIndex: 9999, minWidth: 130, boxShadow: "0 8px 24px rgba(0,0,0,0.1)"
            }}>
                {options.map(o => (
                    <button key={o} onClick={() => onSelect(o)} style={{
                        display: "block", width: "100%", textAlign: "left",
                        background: value === o ? T.primarySoft : "transparent",
                        border: "none", borderRadius: 7, padding: "7px 10px",
                        color: value === o ? T.primary : T.text, fontSize: 11.5,
                        cursor: "pointer", fontWeight: value === o ? 600 : 400, fontFamily: "inherit",
                    }}
                        onMouseEnter={e => { if (value !== o) e.target.style.background = "#f5f5fc"; }}
                        onMouseLeave={e => { if (value !== o) e.target.style.background = "transparent"; }}
                    >{o}</button>
                ))}
            </div>
        )}
    </div>
);

/* ── Chart Tooltip ─────────────────────────────────────────── */
export const CTooltip = ({ active, payload, label }) => {
    if (!active || !payload || payload.length === 0) return null;
    const fmtVal = (v) => {
        if (typeof v !== "number") return v;
        if (v >= 100000) return "₹" + (v / 100000).toFixed(1) + "L";
        if (v >= 1000) return "₹" + (v / 1000).toFixed(1) + "K";
        return v;
    };
    return (
        <div style={{ background: "#fff", border: "1px solid " + T.cardBorder, borderRadius: 10, padding: "10px 14px", fontSize: 12, boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}>
            <div style={{ color: T.textMuted, marginBottom: 6, fontWeight: 600 }}>{label}</div>
            {payload.map((p, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: p.color }} />
                    <span style={{ color: T.textMuted }}>{p.name}:</span>
                    <span style={{ color: T.heading, fontWeight: 600 }}>{fmtVal(p.value)}</span>
                </div>
            ))}
        </div>
    );
};
