import { useState, useEffect, useRef, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from "recharts";
import {
  MapPin, TrendingUp, TrendingDown, Users, Package, IndianRupee, MessageSquare,
  LayoutDashboard, Send, ChevronRight, Filter, AlertTriangle, CheckCircle2,
  Clock, Target, Truck, ArrowUpRight, ArrowDownRight, Search, Bell,
  Menu, Sparkles, Bot, User, ChevronDown, Activity, Building2, Store,
  Warehouse, Zap, Eye, Phone, X, BarChart3, Calendar
} from "lucide-react";

/* ─── DATA ────────────────────────────────────────────────── */
const DEALERS = [
  { id:1, name:"Sharma Distributors", city:"Delhi", state:"Delhi", lat:28.61, lng:77.23, type:"Distributor", category:"A", health:"healthy", revenue:892000, outstanding:45000, lastVisit:"2 days ago", commitments:3, salesRep:"Ravi Kumar" },
  { id:2, name:"Gupta Traders", city:"Mumbai", state:"Maharashtra", lat:19.07, lng:72.87, type:"Retailer", category:"A", health:"at-risk", revenue:654000, outstanding:320000, lastVisit:"25 days ago", commitments:1, salesRep:"Priya Singh" },
  { id:3, name:"Patel Enterprises", city:"Ahmedabad", state:"Gujarat", lat:23.02, lng:72.57, type:"Wholesaler", category:"B", health:"healthy", revenue:523000, outstanding:12000, lastVisit:"5 days ago", commitments:2, salesRep:"Ravi Kumar" },
  { id:4, name:"Reddy & Sons", city:"Hyderabad", state:"Telangana", lat:17.38, lng:78.48, type:"Distributor", category:"A", health:"healthy", revenue:987000, outstanding:67000, lastVisit:"1 day ago", commitments:4, salesRep:"Anjali Reddy" },
  { id:5, name:"Mehta Supplies", city:"Jaipur", state:"Rajasthan", lat:26.91, lng:75.78, type:"Retailer", category:"C", health:"critical", revenue:123000, outstanding:189000, lastVisit:"45 days ago", commitments:0, salesRep:"Ravi Kumar" },
  { id:6, name:"Singh Brothers", city:"Chandigarh", state:"Punjab", lat:30.73, lng:76.77, type:"Distributor", category:"B", health:"healthy", revenue:456000, outstanding:23000, lastVisit:"3 days ago", commitments:2, salesRep:"Amit Verma" },
  { id:7, name:"Joshi Retail Hub", city:"Pune", state:"Maharashtra", lat:18.52, lng:73.85, type:"Retailer", category:"B", health:"at-risk", revenue:345000, outstanding:156000, lastVisit:"18 days ago", commitments:1, salesRep:"Priya Singh" },
  { id:8, name:"Das Trading Co.", city:"Kolkata", state:"West Bengal", lat:22.57, lng:88.36, type:"Wholesaler", category:"A", health:"healthy", revenue:789000, outstanding:34000, lastVisit:"4 days ago", commitments:3, salesRep:"Suman Das" },
  { id:9, name:"Iyer Agencies", city:"Chennai", state:"Tamil Nadu", lat:13.08, lng:80.27, type:"Distributor", category:"B", health:"healthy", revenue:567000, outstanding:89000, lastVisit:"6 days ago", commitments:2, salesRep:"Karthik Iyer" },
  { id:10, name:"Nair Distributors", city:"Kochi", state:"Kerala", lat:9.93, lng:76.26, type:"Distributor", category:"C", health:"at-risk", revenue:234000, outstanding:210000, lastVisit:"30 days ago", commitments:0, salesRep:"Karthik Iyer" },
  { id:11, name:"Bose Wholesale", city:"Patna", state:"Bihar", lat:25.6, lng:85.1, type:"Wholesaler", category:"C", health:"healthy", revenue:198000, outstanding:15000, lastVisit:"7 days ago", commitments:1, salesRep:"Suman Das" },
  { id:12, name:"Agarwal Stores", city:"Lucknow", state:"UP", lat:26.85, lng:80.94, type:"Retailer", category:"A", health:"healthy", revenue:876000, outstanding:56000, lastVisit:"2 days ago", commitments:3, salesRep:"Amit Verma" },
  { id:13, name:"Fernandes Trading", city:"Goa", state:"Goa", lat:15.49, lng:73.82, type:"Retailer", category:"C", health:"critical", revenue:87000, outstanding:95000, lastVisit:"60 days ago", commitments:0, salesRep:"Priya Singh" },
  { id:14, name:"Khan Enterprises", city:"Bhopal", state:"MP", lat:23.25, lng:77.41, type:"Distributor", category:"B", health:"healthy", revenue:432000, outstanding:28000, lastVisit:"4 days ago", commitments:2, salesRep:"Amit Verma" },
  { id:15, name:"Rao Agencies", city:"Bangalore", state:"Karnataka", lat:12.97, lng:77.59, type:"Wholesaler", category:"A", health:"healthy", revenue:945000, outstanding:78000, lastVisit:"1 day ago", commitments:5, salesRep:"Anjali Reddy" },
];

const REVENUE_DATA = [
  { month:"Jul", revenue:2800000, target:3200000, collections:2400000 },
  { month:"Aug", revenue:3100000, target:3200000, collections:2900000 },
  { month:"Sep", revenue:3500000, target:3400000, collections:3200000 },
  { month:"Oct", revenue:4200000, target:3600000, collections:3800000 },
  { month:"Nov", revenue:3800000, target:3800000, collections:3500000 },
  { month:"Dec", revenue:4500000, target:4000000, collections:4100000 },
  { month:"Jan", revenue:3900000, target:4200000, collections:3600000 },
  { month:"Feb", revenue:4100000, target:4200000, collections:3800000 },
];

const COMMITMENT_DATA = [
  { status:"Fulfilled", count:34, value:1820000, color:"#22c55e" },
  { status:"Confirmed", count:18, value:1240000, color:"#6366f1" },
  { status:"Pending", count:12, value:780000, color:"#f59e0b" },
  { status:"Overdue", count:5, value:340000, color:"#ef4444" },
];

const PIPELINE_BY_WEEK = [
  { week:"W1", new:8, confirmed:5, fulfilled:12, overdue:1 },
  { week:"W2", new:11, confirmed:7, fulfilled:9, overdue:2 },
  { week:"W3", new:6, confirmed:9, fulfilled:14, overdue:1 },
  { week:"W4", new:9, confirmed:4, fulfilled:11, overdue:3 },
];

const SALES_REPS = [
  { name:"Ravi Kumar", territory:"North", dealers:12, visits:28, target:1200000, achieved:1080000, commitments:8, conversion:78 },
  { name:"Priya Singh", territory:"West", dealers:10, visits:22, target:1000000, achieved:870000, commitments:5, conversion:65 },
  { name:"Anjali Reddy", territory:"South", dealers:8, visits:30, target:1100000, achieved:1210000, commitments:11, conversion:85 },
  { name:"Amit Verma", territory:"Central", dealers:11, visits:25, target:950000, achieved:920000, commitments:7, conversion:72 },
  { name:"Suman Das", territory:"East", dealers:9, visits:19, target:800000, achieved:690000, commitments:4, conversion:60 },
  { name:"Karthik Iyer", territory:"South", dealers:7, visits:26, target:900000, achieved:945000, commitments:9, conversion:82 },
];

const RECENT_ACTIVITIES = [
  { type:"visit", text:"Ravi Kumar visited Sharma Distributors", detail:"Commitment: 500 cases Premium Soap by next Tuesday", time:"2 hrs ago", icon:"visit" },
  { type:"commitment", text:"New commitment from Das Trading", detail:"\u20B93.4L order for Industrial Cleaners, delivery Mar 5", time:"4 hrs ago", icon:"commitment" },
  { type:"alert", text:"Gupta Traders flagged at-risk", detail:"\u20B93.2L overdue, no visit in 25 days", time:"6 hrs ago", icon:"alert" },
  { type:"order", text:"Order confirmed: Reddy & Sons", detail:"\u20B92.8L \u2014 converted from commitment logged Feb 18", time:"8 hrs ago", icon:"order" },
  { type:"collection", text:"Collection \u20B945K from Sharma Dist.", detail:"Collected by Ravi Kumar during visit", time:"2 hrs ago", icon:"collection" },
  { type:"visit", text:"Karthik Iyer visited Iyer Agencies", detail:"Product demo new range, follow-up scheduled", time:"1 day ago", icon:"visit" },
];

const DEALER_BY_TYPE = [
  { name:"Distributor", value:6, color:"#6366f1" },
  { name:"Retailer", value:5, color:"#ec4899" },
  { name:"Wholesaler", value:4, color:"#f59e0b" },
];

const CHAT_SUGGESTIONS = [
  "Brief me for Sharma Distributors visit",
  "Plan my visits for this week",
  "Show at-risk dealers in my region",
  "What's the demand forecast for Premium Soap?",
  "Kitna collection hua is mahine?",
  "Show commitment pipeline for North territory",
];

/* ─── UTILS ───────────────────────────────────────────────── */
const fmt = n => {
  if (n >= 10000000) return "\u20B9" + (n/10000000).toFixed(1) + "Cr";
  if (n >= 100000) return "\u20B9" + (n/100000).toFixed(1) + "L";
  if (n >= 1000) return "\u20B9" + (n/1000).toFixed(1) + "K";
  return "\u20B9" + n;
};

/* ─── THEME (light mode matching reference image) ─────────── */
const T = {
  sidebar: "#1a1f37",
  sidebarHov: "#252a42",
  sidebarAct: "#2f3556",
  sidebarTxt: "#8b8fad",
  bg: "#f0f1f6",
  cardBg: "#ffffff",
  cardBorder: "#e8e9f0",
  cardShadow: "0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03)",
  heading: "#1a1f37",
  text: "#3d4260",
  textMuted: "#8b8fad",
  textLight: "#a9adc4",
  primary: "#6366f1",
  primarySoft: "#ededfe",
  teal: "#0ea5e9",
  tealSoft: "#e6f6fe",
  pink: "#ec4899",
  pinkSoft: "#fdf0f7",
  green: "#22c55e",
  greenSoft: "#edfcf2",
  orange: "#f59e0b",
  orangeSoft: "#fef8e7",
  red: "#ef4444",
  redSoft: "#fef2f2",
  purple: "#7c3aed",
  purpleSoft: "#f3f0ff",
};

/* ─── INDIA MAP (SVG) ─────────────────────────────────────── */
const IndiaMap = ({ dealers, filters, onDealerClick }) => {
  const [hovered, setHovered] = useState(null);
  const toSVG = (lat, lng) => ({
    x: ((lng - 68) / (98 - 68)) * 280 + 50,
    y: ((35 - lat) / (35 - 6)) * 400 + 20,
  });
  const hCol = h => h === "healthy" ? T.green : h === "at-risk" ? T.orange : T.red;
  const filtered = dealers.filter(d => {
    if (filters.type !== "All" && d.type !== filters.type) return false;
    if (filters.health !== "All" && d.health !== filters.health) return false;
    if (filters.category !== "All" && d.category !== filters.category) return false;
    return true;
  });
  const indiaPath = "M 180 30 C 170 35 165 45 160 55 L 155 60 C 150 65 148 70 145 78 L 138 90 C 132 100 128 108 125 115 L 120 125 C 118 132 115 138 110 145 L 105 155 C 100 165 95 175 90 185 L 85 200 C 82 210 80 218 78 225 L 75 235 C 72 245 70 255 72 265 L 75 275 C 78 285 82 290 88 295 L 100 305 C 108 310 115 315 125 320 L 140 328 C 148 332 155 338 160 345 L 168 358 C 172 365 175 372 178 380 L 182 390 C 185 398 188 405 192 410 L 198 415 C 205 418 210 412 215 405 L 222 395 C 226 388 230 380 235 372 L 240 365 C 245 358 248 352 252 348 L 260 340 C 265 335 270 328 272 320 L 275 310 C 278 298 282 288 288 280 L 295 270 C 300 262 305 255 308 248 L 312 240 C 315 232 318 225 320 218 L 322 210 C 325 200 328 190 330 180 L 332 170 C 334 160 335 148 332 138 L 328 128 C 325 118 320 110 315 102 L 308 92 C 302 85 295 78 288 72 L 278 65 C 270 60 262 55 255 52 L 248 48 C 240 45 232 42 225 40 L 218 38 C 210 36 202 35 195 33 L 180 30 Z";

  return (
    <div style={{ position:"relative", width:"100%", height:"100%" }}>
      <svg viewBox="0 0 380 440" style={{ width:"100%", height:"100%" }}>
        <defs>
          <filter id="mapSh"><feDropShadow dx="0" dy="1" stdDeviation="2" floodColor="#6366f1" floodOpacity="0.06" /></filter>
          <filter id="glow"><feGaussianBlur stdDeviation="3" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <path d={indiaPath} fill="#ededfe" stroke="#c7c8f2" strokeWidth="1.2" filter="url(#mapSh)" />
        {[75,80,85,90].map(lng => { const {x} = toSVG(20,lng); return <line key={lng} x1={x} y1="20" x2={x} y2="420" stroke="#e8e9f0" strokeWidth="0.4" strokeDasharray="4 4" />; })}
        {[10,15,20,25,30].map(lat => { const {y} = toSVG(lat,80); return <line key={lat} x1="50" y1={y} x2="330" y2={y} stroke="#e8e9f0" strokeWidth="0.4" strokeDasharray="4 4" />; })}
        {filtered.map(d => {
          const p = toSVG(d.lat, d.lng);
          const c = hCol(d.health);
          const sz = d.category==="A"?9:d.category==="B"?7:5.5;
          const isH = hovered === d.id;
          return (
            <g key={d.id} style={{cursor:"pointer"}}
              onMouseEnter={() => setHovered(d.id)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onDealerClick && onDealerClick(d)}
            >
              {d.health !== "healthy" && (
                <circle cx={p.x} cy={p.y} r={sz+6} fill="none" stroke={c} strokeWidth="1" opacity=".4">
                  <animate attributeName="r" from={sz+3} to={sz+14} dur="2s" repeatCount="indefinite" />
                  <animate attributeName="opacity" from=".5" to="0" dur="2s" repeatCount="indefinite" />
                </circle>
              )}
              <circle cx={p.x} cy={p.y} r={sz+3} fill={c} opacity={isH?.22:.08} />
              <circle cx={p.x} cy={p.y} r={sz} fill={c} stroke="#fff" strokeWidth="2.5" opacity={isH?1:.85} filter={isH?"url(#glow)":undefined} />
              <text x={p.x} y={p.y+1.5} textAnchor="middle" fill="#fff" fontSize="7" fontWeight="bold" fontFamily="system-ui">{d.category}</text>
              {isH && <text x={p.x} y={p.y-sz-8} textAnchor="middle" fill={T.heading} fontSize="9" fontWeight="700" fontFamily="system-ui">{d.city}</text>}
            </g>
          );
        })}
      </svg>
      {hovered && (() => {
        const d = dealers.find(x => x.id === hovered);
        if (!d) return null;
        return (
          <div style={{ position:"absolute", top:12, right:12, background:"#fff", border:"1px solid "+T.cardBorder, borderRadius:12, padding:"14px 18px", minWidth:210, zIndex:10, boxShadow:"0 8px 24px rgba(0,0,0,0.1)" }}>
            <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
              <div style={{ width:8, height:8, borderRadius:"50%", background:hCol(d.health) }} />
              <span style={{ color:T.heading, fontWeight:700, fontSize:13 }}>{d.name}</span>
            </div>
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"5px 16px", fontSize:11.5, color:T.textMuted }}>
              <span>Type</span><span style={{ color:T.text, fontWeight:500 }}>{d.type}</span>
              <span>Revenue</span><span style={{ color:T.green, fontWeight:600 }}>{fmt(d.revenue)}</span>
              <span>Outstanding</span><span style={{ color:d.outstanding>100000?T.red:T.orange, fontWeight:600 }}>{fmt(d.outstanding)}</span>
              <span>Last Visit</span><span style={{ color:T.text, fontWeight:500 }}>{d.lastVisit}</span>
              <span>Commitments</span><span style={{ color:T.primary, fontWeight:600 }}>{d.commitments}</span>
              <span>Sales Rep</span><span style={{ color:T.text, fontWeight:500 }}>{d.salesRep}</span>
            </div>
          </div>
        );
      })()}
    </div>
  );
};

/* ─── KPI CARD ────────────────────────────────────────────── */
const KpiCard = ({ title, value, sub, trend, trendUp, icon: Icon, bgColor, iconColor, delay = 0 }) => (
  <div style={{
    background: bgColor, borderRadius: 14, padding: "20px 22px",
    position: "relative", overflow: "hidden",
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

/* ─── FILTER BUTTON ───────────────────────────────────────── */
const FilterBtn = ({ label, options, value, onSelect, open, onToggle }) => (
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
        zIndex: 50, minWidth: 120, boxShadow: "0 8px 24px rgba(0,0,0,0.1)"
      }}>
        {options.map(o => (
          <button key={o} onClick={() => onSelect(o)} style={{
            display: "block", width: "100%", textAlign: "left",
            background: value === o ? T.primarySoft : "transparent",
            border: "none", borderRadius: 7, padding: "6px 10px",
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

/* ─── CHART TOOLTIP ───────────────────────────────────────── */
const CTooltip = ({ active, payload, label }) => {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div style={{ background: "#fff", border: "1px solid " + T.cardBorder, borderRadius: 10, padding: "10px 14px", fontSize: 12, boxShadow: "0 4px 16px rgba(0,0,0,0.08)" }}>
      <div style={{ color: T.textMuted, marginBottom: 6, fontWeight: 600 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 2 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: p.color }} />
          <span style={{ color: T.textMuted }}>{p.name}:</span>
          <span style={{ color: T.heading, fontWeight: 600 }}>{typeof p.value === "number" && p.value > 1000 ? fmt(p.value) : p.value}</span>
        </div>
      ))}
    </div>
  );
};

/* ════════════════════════════════════════════════════════════ */
/* ─── MAIN APP ─────────────────────────────────────────────  */
/* ════════════════════════════════════════════════════════════ */
export default function SupplyChainCopilot() {
  const [tab, setTab] = useState("dashboard");
  const [mapF, setMapF] = useState({ type: "All", health: "All", category: "All" });
  const [openF, setOpenF] = useState(null);
  const [chatMsgs, setChatMsgs] = useState([
    { role: "assistant", text: "Namaste! \uD83D\uDE4F I'm your SupplyChain Copilot. I can help with dealer briefings, visit planning, commitment tracking, and demand forecasting. How can I help?", time: "9:00 AM", agent: "Supervisor" },
  ]);
  const [chatIn, setChatIn] = useState("");
  const [typing, setTyping] = useState(false);
  const [sidebar, setSidebar] = useState(true);
  const chatEnd = useRef(null);

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [chatMsgs]);

  const atRisk = DEALERS.filter(d => d.health !== "healthy").length;
  const totalDealers = DEALERS.length;
  const visitedRecent = DEALERS.filter(d => !d.lastVisit.includes("25") && !d.lastVisit.includes("30") && !d.lastVisit.includes("45") && !d.lastVisit.includes("60")).length;
  const totalCommit = COMMITMENT_DATA.reduce((s, c) => s + c.value, 0);

  const sendChat = useCallback(() => {
    if (!chatIn.trim()) return;
    const msg = { role: "user", text: chatIn, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
    setChatMsgs(p => [...p, msg]);
    setChatIn("");
    setTyping(true);
    setTimeout(() => {
      const q = msg.text.toLowerCase();
      let r = { text: "", agent: "Supervisor" };
      if (q.includes("sharma") || q.includes("brief")) {
        r = { agent: "Dealer Intelligence Agent", text: "\uD83D\uDCCB Dealer Brief: Sharma Distributors\n\n\uD83C\uDFE2 Category A Distributor \u2014 Delhi\n\uD83D\uDCCA Monthly Revenue: \u20B98.92L (\u219112% vs last quarter)\n\uD83D\uDCB0 Outstanding: \u20B945,000 (within credit limit)\n\uD83D\uDCC5 Last Visit: 2 days ago by Ravi Kumar\n\nActive Commitments (3):\n\u2022 500 cases Premium Soap \u2014 due next Tuesday\n\u2022 200 cases Industrial Cleaner \u2014 due Mar 10\n\u2022 Trial order: New range samples requested\n\nSuggested Talking Points:\n1. Follow up on Premium Soap delivery\n2. Discuss new product range (strong interest)\n3. Competitor pricing pressure \u2014 consider loyalty discount\n\n\u26A1 Commitment fulfillment rate: 85%" };
      } else if (q.includes("plan") && q.includes("visit")) {
        r = { agent: "Sales Analytics Agent", text: "\uD83D\uDCC5 Visit Plan \u2014 This Week\n\nPriority 1 \u2014 URGENT \uD83D\uDD34\n\u2022 Gupta Traders (Mumbai) \u2014 \u20B93.2L overdue, 25 days gap\n\u2022 Mehta Supplies (Jaipur) \u2014 \u20B91.89L overdue, 45 days gap\n\nPriority 2 \u2014 Follow-up \uD83D\uDFE1\n\u2022 Joshi Retail Hub (Pune) \u2014 Payment follow-up, 18 days\n\u2022 Nair Distributors (Kochi) \u2014 Declining orders\n\nPriority 3 \u2014 Growth \uD83D\uDFE2\n\u2022 Sharma Distributors (Delhi) \u2014 Confirm 500 case commitment\n\u2022 Reddy & Sons (Hyderabad) \u2014 Upsell new range\n\n\uD83D\uDCCD Optimized route saves ~2 hours" };
      } else if (q.includes("risk") || q.includes("at-risk")) {
        r = { agent: "Dealer Intelligence Agent", text: "\u26A0\uFE0F At-Risk Dealers (" + atRisk + ")\n\n\uD83D\uDD34 Critical:\n\u2022 Mehta Supplies \u2014 \u20B91.89L overdue, 45 days no visit\n\u2022 Fernandes Trading \u2014 \u20B995K overdue, 60 days no visit\n\n\uD83D\uDFE1 At-Risk:\n\u2022 Gupta Traders \u2014 \u20B93.2L overdue, declining frequency\n\u2022 Joshi Retail Hub \u2014 \u20B91.56L overdue\n\u2022 Nair Distributors \u2014 \u20B92.1L overdue\n\n\uD83D\uDCA1 Prioritize Gupta Traders (highest outstanding) and Mehta Supplies (longest gap)" };
      } else if (q.includes("forecast") || q.includes("demand")) {
        r = { agent: "Order Planning Agent", text: "\uD83D\uDCC8 Demand Forecast \u2014 Premium Soap\n\nNext 4 Weeks:\n\u2022 W1: 1,200 cases (850 commitments + 350 forecast)\n\u2022 W2: 980 cases (620 commitments + 360 forecast)\n\u2022 W3: 1,100 cases (400 commitments + 700 forecast)\n\u2022 W4: 950 cases (200 commitments + 750 forecast)\n\nConfidence: 78%\nCommitment-backed: 2,070 cases (49%)\nHistorical forecast: 2,160 cases (51%)\n\n\uD83D\uDCA1 15% higher than same period last year" };
      } else if (q.includes("collection") || q.includes("kitna")) {
        r = { agent: "Dealer Intelligence Agent", text: "\uD83D\uDCB0 Collections \u2014 February 2025\n\nTotal: \u20B938.0L / \u20B942.0L target (90.5%)\n\nTop:\n\u2022 Reddy & Sons: \u20B94.8L \u2705\n\u2022 Das Trading: \u20B94.2L \u2705\n\u2022 Sharma Distributors: \u20B93.9L \u2705\n\nPending:\n\u2022 Gupta Traders: \u20B93.2L (25 days overdue)\n\u2022 Nair Distributors: \u20B92.1L (15 days)\n\u2022 Mehta Supplies: \u20B91.89L (45 days)\n\n\uD83D\uDCCA Total outstanding: \u20B914.2L" };
      } else if (q.includes("commitment") || q.includes("pipeline")) {
        r = { agent: "Visit Capture Agent", text: "\uD83D\uDCCB Commitment Pipeline\n\nTotal: \u20B941.8L (69 commitments)\n\n\u2705 Fulfilled: 34 (\u20B918.2L) \u2014 49%\n\uD83D\uDD35 Confirmed: 18 (\u20B912.4L) \u2014 26%\n\uD83D\uDFE1 Pending: 12 (\u20B97.8L) \u2014 17%\n\uD83D\uDD34 Overdue: 5 (\u20B93.4L) \u2014 7%\n\nConversion Rate: 78%\n\nTop:\n1. Rao Agencies: 5 (\u20B96.8L)\n2. Reddy & Sons: 4 (\u20B95.2L)\n3. Sharma Distributors: 3 (\u20B94.1L)" };
      } else {
        r = { agent: "Supervisor", text: "I can help you with:\n\n\u2022 Dealer Briefing \u2014 \"Brief me for [dealer name]\"\n\u2022 Visit Planning \u2014 \"Plan my visits this week\"\n\u2022 Commitment Tracking \u2014 \"Show commitment pipeline\"\n\u2022 Demand Forecast \u2014 \"Forecast for [product]\"\n\u2022 Collections \u2014 \"Kitna collection hua?\"\n\u2022 Risk Alerts \u2014 \"Show at-risk dealers\"" };
      }
      setChatMsgs(p => [...p, { role: "assistant", ...r, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }]);
      setTyping(false);
    }, 1400);
  }, [chatIn, atRisk]);

  const card = { background: T.cardBg, border: "1px solid " + T.cardBorder, borderRadius: 14, padding: 20, boxShadow: T.cardShadow };

  return (
    <div style={{ display: "flex", height: "100vh", background: T.bg, fontFamily: "'DM Sans','Segoe UI',system-ui,sans-serif", color: T.text, overflow: "hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:5px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:#d0d1dd;border-radius:3px}
        @keyframes slideUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
        @keyframes dotBounce{0%,60%,100%{transform:translateY(0)}30%{transform:translateY(-4px)}}
      `}</style>

      {/* ═══════ SIDEBAR ═══════ */}
      <div style={{ width: sidebar ? 230 : 60, minWidth: sidebar ? 230 : 60, background: T.sidebar, display: "flex", flexDirection: "column", transition: "width .3s,min-width .3s", zIndex: 20, overflow: "hidden" }}>
        <div style={{ padding: sidebar ? "20px 18px 16px" : "20px 10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Zap size={18} color="#fff" />
          </div>
          {sidebar && (
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: "#fff", letterSpacing: "-0.3px" }}>SupplyChain</div>
              <div style={{ fontSize: 9, fontWeight: 600, color: "#8b8fad", letterSpacing: "1.5px", textTransform: "uppercase" }}>Copilot</div>
            </div>
          )}
        </div>
        <div style={{ padding: "14px 8px", flex: 1 }}>
          {sidebar && <div style={{ fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", letterSpacing: "1px", textTransform: "uppercase", padding: "0 10px", marginBottom: 8 }}>MAIN</div>}
          {[
            { id: "dashboard", icon: LayoutDashboard, label: "Dashboard", badge: null },
            { id: "chat", icon: MessageSquare, label: "AI Copilot", badge: "AI" },
          ].map(item => (
            <button key={item.id} onClick={() => setTab(item.id)} style={{
              display: "flex", alignItems: "center", gap: 10, width: "100%",
              padding: sidebar ? "10px 14px" : "10px 0", justifyContent: sidebar ? "flex-start" : "center",
              background: tab === item.id ? T.sidebarAct : "transparent",
              border: "none", borderRadius: 10,
              color: tab === item.id ? "#fff" : T.sidebarTxt,
              fontSize: 13, fontWeight: tab === item.id ? 600 : 500, cursor: "pointer",
              transition: "all .2s", marginBottom: 3, fontFamily: "inherit",
            }}
              onMouseEnter={e => { if (tab !== item.id) e.currentTarget.style.background = T.sidebarHov; }}
              onMouseLeave={e => { if (tab !== item.id) e.currentTarget.style.background = "transparent"; }}
            >
              <item.icon size={18} />
              {sidebar && item.label}
              {item.badge && sidebar && (
                <span style={{ marginLeft: "auto", background: "linear-gradient(135deg,#6366f1,#ec4899)", color: "#fff", fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 6 }}>{item.badge}</span>
              )}
            </button>
          ))}
          {sidebar && (
            <>
              <div style={{ fontSize: 10, fontWeight: 600, color: "rgba(255,255,255,0.25)", letterSpacing: "1px", textTransform: "uppercase", padding: "16px 10px 8px" }}>QUICK STATS</div>
              {[
                { label: "Active Dealers", val: totalDealers, c: "#6366f1" },
                { label: "At-Risk", val: atRisk, c: "#ef4444" },
                { label: "Pipeline", val: fmt(totalCommit), c: "#22c55e" },
              ].map((s, i) => (
                <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 12px", marginBottom: 1 }}>
                  <span style={{ fontSize: 11, color: T.sidebarTxt }}>{s.label}</span>
                  <span style={{ fontSize: 12, fontWeight: 700, color: s.c, fontFamily: "'JetBrains Mono',monospace" }}>{s.val}</span>
                </div>
              ))}
            </>
          )}
        </div>
        <button onClick={() => setSidebar(!sidebar)} style={{ padding: 14, borderTop: "1px solid rgba(255,255,255,0.06)", background: "transparent", border: "none", color: T.sidebarTxt, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Menu size={18} />
        </button>
      </div>

      {/* ═══════ MAIN ═══════ */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ padding: "12px 28px", borderBottom: "1px solid " + T.cardBorder, display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fff" }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, color: T.heading }}>Welcome back, Ravi Kumar!</h1>
            <p style={{ fontSize: 12, color: T.textMuted, marginTop: 1 }}>{tab === "dashboard" ? "Track your dealer network, commitments, and revenue." : "Chat with your SupplyChain AI assistant."}</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: T.bg, borderRadius: 9, padding: "7px 14px", border: "1px solid " + T.cardBorder }}>
              <Search size={14} color={T.textLight} />
              <span style={{ fontSize: 12, color: T.textLight }}>Search...</span>
            </div>
            <button style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}>
              <Filter size={13} /> Filters
            </button>
            <button style={{ background: "#fff", color: T.text, border: "1px solid " + T.cardBorder, borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}>
              <ArrowUpRight size={13} /> Export
            </button>
            <div style={{ position: "relative", width: 36, height: 36, borderRadius: 10, background: T.bg, border: "1px solid " + T.cardBorder, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
              <Bell size={16} color={T.textMuted} />
              <div style={{ position: "absolute", top: -3, right: -3, width: 16, height: 16, background: T.red, borderRadius: "50%", border: "2px solid #fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, fontWeight: 700, color: "#fff" }}>3</div>
            </div>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "#fff" }}>RK</div>
          </div>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: "auto", padding: tab === "chat" ? 0 : 24 }} onClick={() => openF && setOpenF(null)}>
          {tab === "dashboard" && (
            <div style={{ maxWidth: 1400, margin: "0 auto" }}>
              {/* KPIs */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: 16, marginBottom: 22 }}>
                <KpiCard title="Total Revenue" value={fmt(REVENUE_DATA[7].revenue)} trend="8.2%" trendUp icon={IndianRupee} bgColor={T.pinkSoft} iconColor={T.pink} delay={0} sub="This month" />
                <KpiCard title="Active Dealers" value={totalDealers} trend="+2 new" trendUp icon={Building2} bgColor={T.tealSoft} iconColor={T.teal} delay={.04} sub="5 territories" />
                <KpiCard title="Commitment Pipeline" value={fmt(totalCommit)} trend="12%" trendUp icon={Target} bgColor={T.purpleSoft} iconColor={T.purple} delay={.08} sub="69 commitments" />
                <KpiCard title="Visit Coverage" value={Math.round(visitedRecent / totalDealers * 100) + "%"} trend="5%" trendUp icon={MapPin} bgColor={T.greenSoft} iconColor={T.green} delay={.12} sub={visitedRecent + "/" + totalDealers + " visited"} />
                <KpiCard title="Collections" value={fmt(REVENUE_DATA[7].collections)} trend="90.5%" trendUp icon={Truck} bgColor={T.orangeSoft} iconColor={T.orange} delay={.16} sub="Of \u20B942L target" />
                <KpiCard title="At-Risk Dealers" value={atRisk} trend={Math.round(atRisk / totalDealers * 100) + "%"} trendUp={false} icon={AlertTriangle} bgColor={T.redSoft} iconColor={T.red} delay={.2} sub="Need attention" />
              </div>
              {/* Banner */}
              <div style={{ background: "linear-gradient(135deg,#f59e0b,#f97316)", borderRadius: 14, padding: "16px 24px", marginBottom: 22, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                  <div style={{ width: 48, height: 48, borderRadius: "50%", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, fontWeight: 800, color: "#fff" }}>73%</div>
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>Your February target is 73% complete</div>
                    <div style={{ fontSize: 12, color: "rgba(255,255,255,0.8)", marginTop: 2 }}>{"\u20B9"}30.7L of {"\u20B9"}42L. 5 overdue commitments need follow-up.</div>
                  </div>
                </div>
                <button style={{ background: "rgba(255,255,255,0.2)", border: "1px solid rgba(255,255,255,0.3)", borderRadius: 8, padding: "7px 16px", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>View Details {"\u2192"}</button>
              </div>
              {/* Map + Pipeline */}
              <div style={{ display: "grid", gridTemplateColumns: "1.45fr 1fr", gap: 20, marginBottom: 22 }}>
                <div style={{ ...card }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <div>
                      <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Dealer Network Map</h3>
                      <p style={{ fontSize: 11, color: T.textMuted, marginTop: 2 }}>
                        {DEALERS.filter(d => {
                          if (mapF.type !== "All" && d.type !== mapF.type) return false;
                          if (mapF.health !== "All" && d.health !== mapF.health) return false;
                          if (mapF.category !== "All" && d.category !== mapF.category) return false;
                          return true;
                        }).length} dealers shown
                      </p>
                    </div>
                    <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
                      <FilterBtn label="Type" options={["All", "Distributor", "Retailer", "Wholesaler"]} value={mapF.type} onSelect={v => { setMapF(f => ({ ...f, type: v })); setOpenF(null); }} open={openF === "type"} onToggle={() => setOpenF(openF === "type" ? null : "type")} />
                      <FilterBtn label="Health" options={["All", "healthy", "at-risk", "critical"]} value={mapF.health} onSelect={v => { setMapF(f => ({ ...f, health: v })); setOpenF(null); }} open={openF === "health"} onToggle={() => setOpenF(openF === "health" ? null : "health")} />
                      <FilterBtn label="Cat" options={["All", "A", "B", "C"]} value={mapF.category} onSelect={v => { setMapF(f => ({ ...f, category: v })); setOpenF(null); }} open={openF === "cat"} onToggle={() => setOpenF(openF === "cat" ? null : "cat")} />
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: 14, marginBottom: 10, fontSize: 10, color: T.textMuted }}>
                    {[{ l: "Healthy", c: T.green }, { l: "At-Risk", c: T.orange }, { l: "Critical", c: T.red }].map(x => (
                      <span key={x.l} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                        <span style={{ width: 8, height: 8, borderRadius: "50%", background: x.c }} />{x.l}
                      </span>
                    ))}
                    <span style={{ color: T.textLight }}>| Size = Category (A {">"} B {">"} C)</span>
                  </div>
                  <div style={{ height: 340 }}><IndiaMap dealers={DEALERS} filters={mapF} /></div>
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                  <div style={{ ...card, flex: 1 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Commitment Pipeline</h3>
                    <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 12 }}>From dealer conversations</p>
                    <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
                      <div style={{ width: 150, height: 150 }}>
                        <ResponsiveContainer>
                          <PieChart>
                            <Pie data={COMMITMENT_DATA} cx="50%" cy="50%" innerRadius={46} outerRadius={66} dataKey="count" paddingAngle={3} strokeWidth={0}>
                              {COMMITMENT_DATA.map((e, i) => <Cell key={i} fill={e.color} />)}
                            </Pie>
                            <text x="50%" y="46%" textAnchor="middle" fill={T.heading} fontSize={22} fontWeight={800}>69</text>
                            <text x="50%" y="60%" textAnchor="middle" fill={T.textMuted} fontSize={10}>Total</text>
                          </PieChart>
                        </ResponsiveContainer>
                      </div>
                      <div style={{ flex: 1 }}>
                        {COMMITMENT_DATA.map((c, i) => (
                          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 0", borderBottom: i < 3 ? "1px solid " + T.cardBorder : "none" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                              <div style={{ width: 8, height: 8, borderRadius: "50%", background: c.color }} />
                              <span style={{ fontSize: 12, color: T.textMuted }}>{c.status}</span>
                            </div>
                            <div>
                              <span style={{ fontSize: 13, fontWeight: 700, color: T.heading, fontFamily: "'JetBrains Mono',monospace" }}>{c.count}</span>
                              <span style={{ fontSize: 10, color: T.textLight, marginLeft: 6 }}>{fmt(c.value)}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div style={{ ...card }}>
                    <h3 style={{ fontSize: 13, fontWeight: 700, color: T.heading, marginBottom: 12 }}>Dealers by Type</h3>
                    <div style={{ display: "flex", gap: 10 }}>
                      {DEALER_BY_TYPE.map((d, i) => (
                        <div key={i} style={{ flex: 1, textAlign: "center", padding: "14px 8px", background: i === 0 ? T.primarySoft : i === 1 ? T.pinkSoft : T.orangeSoft, borderRadius: 11 }}>
                          <div style={{ fontSize: 24, fontWeight: 800, color: d.color, fontFamily: "'JetBrains Mono',monospace" }}>{d.value}</div>
                          <div style={{ fontSize: 10, color: T.textMuted, marginTop: 2 }}>{d.name}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
              {/* Revenue + Top Dealers */}
              <div style={{ display: "grid", gridTemplateColumns: "1.45fr 1fr", gap: 20, marginBottom: 22 }}>
                <div style={{ ...card }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <div>
                      <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Revenue Analytics</h3>
                      <div style={{ display: "flex", gap: 16, marginTop: 4, fontSize: 11 }}>
                        <span style={{ color: T.textMuted }}>Total Revenue <strong style={{ color: T.heading }}>{"\u20B9"}41L</strong></span>
                        <span style={{ color: T.textMuted }}>Collections <strong style={{ color: T.heading }}>{"\u20B9"}38L</strong></span>
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
                    <ResponsiveContainer>
                      <AreaChart data={REVENUE_DATA}>
                        <defs>
                          <linearGradient id="rg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.primary} stopOpacity={.2} /><stop offset="100%" stopColor={T.primary} stopOpacity={0} /></linearGradient>
                          <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={T.green} stopOpacity={.15} /><stop offset="100%" stopColor={T.green} stopOpacity={0} /></linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ededf0" />
                        <XAxis dataKey="month" tick={{ fill: T.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: T.textMuted, fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={fmt} />
                        <Tooltip content={<CTooltip />} />
                        <Area type="monotone" dataKey="revenue" stroke={T.primary} strokeWidth={2.5} fill="url(#rg)" name="Revenue" />
                        <Area type="monotone" dataKey="collections" stroke={T.green} strokeWidth={2} fill="url(#cg)" name="Collections" />
                        <Line type="monotone" dataKey="target" stroke={T.pink} strokeWidth={2} strokeDasharray="6 4" dot={false} name="Target" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
                <div style={{ ...card }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Top Dealers</h3>
                    <span style={{ fontSize: 11, color: T.primary, fontWeight: 600, cursor: "pointer" }}>View All {"\u2192"}</span>
                  </div>
                  {[...DEALERS].sort((a, b) => b.revenue - a.revenue).slice(0, 7).map((d, i) => {
                    const cols = [T.primary, T.pink, T.green, T.orange, T.teal];
                    const c = cols[i % 5];
                    return (
                      <div key={d.id} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "8px 8px", borderRadius: 8, transition: "background .15s", cursor: "pointer" }}
                        onMouseEnter={e => e.currentTarget.style.background = T.bg}
                        onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                          <div style={{ width: 32, height: 32, borderRadius: 8, background: c + "15", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: c }}>{d.name.split(" ").map(w => w[0]).join("").slice(0, 2)}</div>
                          <div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: T.heading }}>{d.name}</div>
                            <div style={{ fontSize: 10, color: T.textLight }}>{d.city} {"\u00B7"} {d.type}</div>
                          </div>
                        </div>
                        <div style={{ textAlign: "right" }}>
                          <div style={{ fontSize: 13, fontWeight: 700, color: T.green, fontFamily: "'JetBrains Mono',monospace" }}>{fmt(d.revenue)}</div>
                          <div style={{ fontSize: 10, color: T.textLight }}>{d.commitments} commitments</div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              {/* Pipeline + Activity */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20, marginBottom: 22 }}>
                <div style={{ ...card }}>
                  <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading, marginBottom: 2 }}>Weekly Commitment Flow</h3>
                  <p style={{ fontSize: 11, color: T.textMuted, marginBottom: 14 }}>Commitments captured {"\u2192"} converted</p>
                  <div style={{ height: 220 }}>
                    <ResponsiveContainer>
                      <BarChart data={PIPELINE_BY_WEEK} barCategoryGap="20%">
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
                  </div>
                </div>
                <div style={{ ...card }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
                    <h3 style={{ fontSize: 15, fontWeight: 700, color: T.heading }}>Recent Activity</h3>
                    <span style={{ fontSize: 11, color: T.primary, fontWeight: 600, cursor: "pointer" }}>View All {"\u2192"}</span>
                  </div>
                  <div style={{ maxHeight: 250, overflow: "auto" }}>
                    {RECENT_ACTIVITIES.map((a, i) => {
                      const colors = { visit: T.teal, commitment: T.primary, alert: T.red, order: T.green, collection: T.orange };
                      const bgs = { visit: T.tealSoft, commitment: T.primarySoft, alert: T.redSoft, order: T.greenSoft, collection: T.orangeSoft };
                      const icons = { visit: MapPin, commitment: Target, alert: AlertTriangle, order: Package, collection: IndianRupee };
                      const Ic = icons[a.icon];
                      return (
                        <div key={i} style={{ display: "flex", gap: 10, padding: "8px 6px", borderRadius: 8, transition: "background .15s" }}
                          onMouseEnter={e => e.currentTarget.style.background = T.bg}
                          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                        >
                          <div style={{ width: 32, height: 32, borderRadius: 9, flexShrink: 0, background: bgs[a.icon], display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <Ic size={14} color={colors[a.icon]} />
                          </div>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontSize: 12, fontWeight: 600, color: T.heading }}>{a.text}</div>
                            <div style={{ fontSize: 10, color: T.textMuted, marginTop: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{a.detail}</div>
                          </div>
                          <span style={{ fontSize: 10, color: T.textLight, whiteSpace: "nowrap", flexShrink: 0 }}>{a.time}</span>
                        </div>
                      );
                    })}
                  </div>
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
                    <button style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 7, padding: "5px 12px", fontSize: 11, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}><Filter size={11} /> Filters</button>
                    <button style={{ background: "#fff", color: T.text, border: "1px solid " + T.cardBorder, borderRadius: 7, padding: "5px 12px", fontSize: 11, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}><ArrowUpRight size={11} /> Export</button>
                  </div>
                </div>
                <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "0 3px" }}>
                  <thead>
                    <tr>
                      {["Sales Rep", "Territory", "Dealers", "Visits", "Target", "Achieved", "Commitments", "Conversion"].map(h => (
                        <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontSize: 10.5, fontWeight: 600, color: T.textLight, textTransform: "uppercase", letterSpacing: ".4px", borderBottom: "1px solid " + T.cardBorder }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {SALES_REPS.map((r, i) => {
                      const pct = Math.round(r.achieved / r.target * 100);
                      const pc = pct >= 100 ? T.green : pct >= 80 ? T.orange : T.red;
                      const pb = pct >= 100 ? T.greenSoft : pct >= 80 ? T.orangeSoft : T.redSoft;
                      const ac = [T.primary, T.pink, T.green, T.orange, T.teal, T.purple];
                      return (
                        <tr key={i} style={{ transition: "background .15s" }}
                          onMouseEnter={e => e.currentTarget.style.background = T.bg}
                          onMouseLeave={e => e.currentTarget.style.background = "transparent"}
                        >
                          <td style={{ padding: "10px 12px", borderRadius: "8px 0 0 8px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ width: 30, height: 30, borderRadius: 8, background: ac[i] + "18", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 10, fontWeight: 700, color: ac[i] }}>{r.name.split(" ").map(n => n[0]).join("")}</div>
                              <span style={{ fontSize: 12.5, fontWeight: 600, color: T.heading }}>{r.name}</span>
                            </div>
                          </td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted }}>{r.territory}</td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: T.text, fontFamily: "'JetBrains Mono',monospace" }}>{r.dealers}</td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: T.text, fontFamily: "'JetBrains Mono',monospace" }}>{r.visits}</td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: T.textMuted, fontFamily: "'JetBrains Mono',monospace" }}>{fmt(r.target)}</td>
                          <td style={{ padding: "10px 12px" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                              <span style={{ fontSize: 12, fontWeight: 600, color: T.heading, fontFamily: "'JetBrains Mono',monospace" }}>{fmt(r.achieved)}</span>
                              <span style={{ fontSize: 10, fontWeight: 600, color: pc, background: pb, padding: "2px 7px", borderRadius: 5 }}>{pct}%</span>
                            </div>
                          </td>
                          <td style={{ padding: "10px 12px", fontSize: 12, color: T.primary, fontWeight: 600, fontFamily: "'JetBrains Mono',monospace" }}>{r.commitments}</td>
                          <td style={{ padding: "10px 12px", borderRadius: "0 8px 8px 0" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ width: 50, height: 5, borderRadius: 3, background: "#ededf0", overflow: "hidden" }}>
                                <div style={{ width: r.conversion + "%", height: "100%", borderRadius: 3, background: r.conversion >= 80 ? T.green : r.conversion >= 65 ? T.orange : T.red }} />
                              </div>
                              <span style={{ fontSize: 11, fontWeight: 600, color: r.conversion >= 80 ? T.green : r.conversion >= 65 ? T.orange : T.red, fontFamily: "'JetBrains Mono',monospace" }}>{r.conversion}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ══════════ CHAT ══════════ */}
          {tab === "chat" && (
            <div style={{ display: "flex", height: "100%" }}>
              <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                <div style={{ flex: 1, overflow: "auto", padding: "24px 32px" }}>
                  <div style={{ maxWidth: 780, margin: "0 auto" }}>
                    {chatMsgs.map((m, i) => (
                      <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", marginBottom: 16, animation: "slideUp .3s ease " + Math.min(i * .08, .4) + "s both" }}>
                        {m.role === "assistant" && (
                          <div style={{ width: 34, height: 34, borderRadius: 10, marginRight: 10, flexShrink: 0, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", marginTop: 4 }}>
                            <Bot size={16} color="#fff" />
                          </div>
                        )}
                        <div style={{ maxWidth: "70%" }}>
                          {m.role === "assistant" && m.agent && (
                            <div style={{ fontSize: 10, color: T.primary, marginBottom: 4, fontWeight: 600, display: "flex", alignItems: "center", gap: 3 }}>
                              <Sparkles size={10} /> {m.agent}
                            </div>
                          )}
                          <div style={{
                            padding: "12px 16px", borderRadius: 14,
                            background: m.role === "user" ? "linear-gradient(135deg,#6366f1,#818cf8)" : "#fff",
                            border: m.role === "user" ? "none" : "1px solid " + T.cardBorder,
                            color: m.role === "user" ? "#fff" : T.text, fontSize: 13, lineHeight: 1.65,
                            whiteSpace: "pre-wrap", boxShadow: m.role === "assistant" ? T.cardShadow : "0 2px 8px rgba(99,102,241,0.15)",
                            borderTopRightRadius: m.role === "user" ? 4 : 14,
                            borderTopLeftRadius: m.role === "assistant" ? 4 : 14,
                          }}>
                            {m.text}
                          </div>
                          <div style={{ fontSize: 10, color: T.textLight, marginTop: 4, textAlign: m.role === "user" ? "right" : "left" }}>{m.time}</div>
                        </div>
                        {m.role === "user" && (
                          <div style={{ width: 34, height: 34, borderRadius: 10, marginLeft: 10, flexShrink: 0, background: T.bg, border: "1px solid " + T.cardBorder, display: "flex", alignItems: "center", justifyContent: "center", marginTop: 4 }}>
                            <User size={16} color={T.textMuted} />
                          </div>
                        )}
                      </div>
                    ))}
                    {typing && (
                      <div style={{ display: "flex", gap: 10, marginBottom: 16 }}>
                        <div style={{ width: 34, height: 34, borderRadius: 10, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Bot size={16} color="#fff" />
                        </div>
                        <div style={{ padding: "14px 18px", borderRadius: 14, borderTopLeftRadius: 4, background: "#fff", border: "1px solid " + T.cardBorder, display: "flex", gap: 5, boxShadow: T.cardShadow }}>
                          {[0, 1, 2].map(j => (
                            <div key={j} style={{ width: 7, height: 7, borderRadius: "50%", background: T.primary, animation: "dotBounce 1.2s ease " + j * .2 + "s infinite" }} />
                          ))}
                        </div>
                      </div>
                    )}
                    <div ref={chatEnd} />
                  </div>
                </div>
                {chatMsgs.length <= 2 && (
                  <div style={{ padding: "0 32px 10px", maxWidth: 780, margin: "0 auto", width: "100%", display: "flex", flexWrap: "wrap", gap: 7 }}>
                    {CHAT_SUGGESTIONS.map((s, i) => (
                      <button key={i} onClick={() => setChatIn(s)} style={{ padding: "7px 13px", borderRadius: 10, background: "#fff", border: "1px solid " + T.cardBorder, color: T.textMuted, fontSize: 11.5, cursor: "pointer", transition: "all .2s", fontFamily: "inherit" }}
                        onMouseEnter={e => { e.target.style.borderColor = "#c7c8f2"; e.target.style.color = T.primary; e.target.style.background = T.primarySoft; }}
                        onMouseLeave={e => { e.target.style.borderColor = T.cardBorder; e.target.style.color = T.textMuted; e.target.style.background = "#fff"; }}
                      >{s}</button>
                    ))}
                  </div>
                )}
                <div style={{ padding: "14px 32px 18px", borderTop: "1px solid " + T.cardBorder, background: "#fff" }}>
                  <div style={{ maxWidth: 780, margin: "0 auto", display: "flex", alignItems: "center", gap: 10, background: T.bg, border: "1px solid " + T.cardBorder, borderRadius: 14, padding: "4px 4px 4px 16px" }}>
                    <input value={chatIn} onChange={e => setChatIn(e.target.value)} onKeyDown={e => e.key === "Enter" && sendChat()}
                      placeholder="Ask your SupplyChain Copilot... (Hindi / English / Hinglish)"
                      style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: T.heading, fontSize: 13, fontFamily: "'DM Sans',system-ui" }}
                    />
                    <button onClick={sendChat} style={{
                      width: 40, height: 40, borderRadius: 10,
                      background: chatIn.trim() ? "linear-gradient(135deg,#6366f1,#818cf8)" : T.bg,
                      border: chatIn.trim() ? "none" : "1px solid " + T.cardBorder,
                      cursor: chatIn.trim() ? "pointer" : "default",
                      display: "flex", alignItems: "center", justifyContent: "center",
                    }}>
                      <Send size={16} color={chatIn.trim() ? "#fff" : T.textLight} />
                    </button>
                  </div>
                  <div style={{ textAlign: "center", marginTop: 7, fontSize: 10, color: T.textLight }}>Powered by Multi-Agent System {"\u00B7"} Supervisor {"\u2192"} Dealer Intel {"\u00B7"} Visit Capture {"\u00B7"} Order Planning</div>
                </div>
              </div>
              <div style={{ width: 250, borderLeft: "1px solid " + T.cardBorder, background: "#fff", padding: 20, display: "flex", flexDirection: "column", gap: 14, overflow: "auto" }}>
                <h4 style={{ fontSize: 13, fontWeight: 700, color: T.heading }}>Active Agents</h4>
                {[
                  { name: "Supervisor", desc: "Routes queries to specialists", color: T.primary, icon: Zap },
                  { name: "Dealer Intelligence", desc: "Profiles, payments, history", color: T.green, icon: Building2 },
                  { name: "Visit Capture", desc: "Extract commitments from NL", color: T.purple, icon: MessageSquare },
                  { name: "Order Planning", desc: "Forecast & ATP/CTP", color: T.orange, icon: Package },
                ].map((a, i) => (
                  <div key={i} style={{ padding: "10px 12px", borderRadius: 10, background: T.bg, border: "1px solid " + T.cardBorder }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 4 }}>
                      <div style={{ width: 26, height: 26, borderRadius: 7, background: a.color + "15", display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <a.icon size={13} color={a.color} />
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 600, color: T.heading }}>{a.name}</span>
                    </div>
                    <p style={{ fontSize: 10, color: T.textMuted, paddingLeft: 33 }}>{a.desc}</p>
                  </div>
                ))}
                <div style={{ marginTop: "auto" }}>
                  <h4 style={{ fontSize: 12, fontWeight: 600, color: T.textMuted, marginBottom: 8 }}>Quick Actions</h4>
                  {["Log a visit", "Check dealer health", "View pipeline"].map((a, i) => (
                    <button key={i} onClick={() => setChatIn(a)} style={{ display: "block", width: "100%", textAlign: "left", padding: "7px 10px", marginBottom: 4, borderRadius: 8, background: "transparent", border: "1px solid " + T.cardBorder, color: T.textMuted, fontSize: 11, cursor: "pointer", fontFamily: "inherit" }}
                      onMouseEnter={e => { e.target.style.borderColor = "#c7c8f2"; e.target.style.color = T.primary; }}
                      onMouseLeave={e => { e.target.style.borderColor = T.cardBorder; e.target.style.color = T.textMuted; }}
                    >
                      <ChevronRight size={10} style={{ display: "inline", marginRight: 3 }} />{a}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
