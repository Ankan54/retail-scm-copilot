import { useState } from "react";
import {
  LayoutDashboard, MessageSquare, Menu, Search, Filter,
  ArrowUpRight, Bell, Zap, ChevronDown, IndianRupee, Factory,
} from "lucide-react";
import { ComingSoonBtn } from "./components";
import { T, fmt } from "./api";
import { DEALERS, COMMITMENT_DATA } from "./data";
import DashboardTab from "./DashboardTab";
import ProductionDashboardTab from "./ProductionDashboardTab";
import ChatTab from "./ChatTab";
import "./App.css";

export default function App() {
  const [tab, setTab] = useState("dashboard");
  const [sidebar, setSidebar] = useState(true);
  const [dashView, setDashView] = useState("sales");

  const atRisk = DEALERS.filter(d => d.health !== "healthy").length;
  const totalDealers = DEALERS.length;
  const totalCommit = COMMITMENT_DATA.reduce((s, c) => s + c.value, 0);

  return (
    <div style={{ display: "flex", height: "100vh", background: T.bg, fontFamily: "'DM Sans','Segoe UI',system-ui,sans-serif", color: T.text, overflow: "hidden" }}>

      {/* ═══════ SIDEBAR ═══════ */}
      <div style={{ width: sidebar ? 230 : 60, minWidth: sidebar ? 230 : 60, background: T.sidebar, display: "flex", flexDirection: "column", transition: "width .3s,min-width .3s", zIndex: 20, overflow: "hidden" }}>
        <div style={{ padding: sidebar ? "20px 18px 16px" : "20px 10px 16px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            <Zap size={18} color="#fff" />
          </div>
          {sidebar && (
            <div>
              <div style={{ fontSize: 15, fontWeight: 800, color: "#fff", letterSpacing: "-0.3px" }}>MSME Retail Copilot</div>
              <div style={{ fontSize: 9, fontWeight: 500, color: "#8b8fad", letterSpacing: "0.5px" }}>AI copilot for MSME manufacturers</div>
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
                  <span className="mono" style={{ fontSize: 12, fontWeight: 700, color: s.c }}>{s.val}</span>
                </div>
              ))}
            </>
          )}
        </div>
        <button onClick={() => setSidebar(!sidebar)} style={{ padding: 14, borderTop: "1px solid rgba(255,255,255,0.06)", background: "transparent", border: "none", color: T.sidebarTxt, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Menu size={18} />
        </button>
      </div>

      {/* ═══════ MAIN CONTENT ═══════ */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {/* Header */}
        <div style={{ padding: "12px 28px", borderBottom: "1px solid " + T.cardBorder, display: "flex", justifyContent: "space-between", alignItems: "center", background: "#fff" }}>
          <div>
            <h1 style={{ fontSize: 20, fontWeight: 800, color: T.heading }}>Welcome back, Manager!</h1>
            <p style={{ fontSize: 12, color: T.textMuted, marginTop: 1 }}>{tab === "dashboard" ? (dashView === "sales" ? "Track your dealer network, commitments, and revenue." : "Monitor production, capacity, and inventory health.") : "Chat with your AI copilot."}</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, background: T.bg, borderRadius: 9, padding: "7px 14px", border: "1px solid " + T.cardBorder }}>
              <Search size={14} color={T.textLight} />
              <span style={{ fontSize: 12, color: T.textLight }}>Search...</span>
            </div>
            <ComingSoonBtn>
              <button style={{ background: T.primary, color: "#fff", border: "none", borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}>
                <Filter size={13} /> Filters
              </button>
            </ComingSoonBtn>
            <ComingSoonBtn>
              <button style={{ background: "#fff", color: T.text, border: "1px solid " + T.cardBorder, borderRadius: 8, padding: "7px 14px", fontSize: 12, fontWeight: 500, cursor: "pointer", display: "flex", alignItems: "center", gap: 4, fontFamily: "inherit" }}>
                <ArrowUpRight size={13} /> Export
              </button>
            </ComingSoonBtn>
            <div style={{ position: "relative", width: 36, height: 36, borderRadius: 10, background: T.bg, border: "1px solid " + T.cardBorder, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
              <Bell size={16} color={T.textMuted} />
              <div style={{ position: "absolute", top: -3, right: -3, width: 16, height: 16, background: T.red, borderRadius: "50%", border: "2px solid #fff", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 8, fontWeight: 700, color: "#fff" }}>3</div>
            </div>
            <div style={{ width: 36, height: 36, borderRadius: 10, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "#fff" }}>AB</div>
          </div>
        </div>

        {/* Tab Content */}
        <div style={{ flex: 1, overflow: "auto", padding: tab === "chat" ? 0 : 24 }}>
          {tab === "dashboard" && (
            <div>
              {/* Sales / Production toggle */}
              <div style={{ display: "flex", gap: 4, marginBottom: 20, background: T.bg, padding: 4, borderRadius: 12, width: "fit-content" }}>
                {[
                  { id: "sales", label: "Sales", icon: IndianRupee },
                  { id: "production", label: "Production", icon: Factory },
                ].map(v => (
                  <button key={v.id} onClick={() => setDashView(v.id)} style={{
                    padding: "8px 20px", borderRadius: 10, fontSize: 13, fontWeight: 600,
                    border: "none", cursor: "pointer", fontFamily: "inherit",
                    display: "flex", alignItems: "center", gap: 6,
                    background: dashView === v.id ? "#fff" : "transparent",
                    color: dashView === v.id ? T.primary : T.textMuted,
                    boxShadow: dashView === v.id ? "0 1px 3px rgba(0,0,0,0.08)" : "none",
                    transition: "all .2s",
                  }}>
                    <v.icon size={15} /> {v.label}
                  </button>
                ))}
              </div>
              {dashView === "sales" && <DashboardTab />}
              {dashView === "production" && <ProductionDashboardTab />}
            </div>
          )}
          {tab === "chat" && <ChatTab />}
        </div>
      </div>
    </div>
  );
}
