import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Sparkles, ChevronRight, Plus, MessageSquare, Clock } from "lucide-react";
import { T } from "./api";
import { CHAT_SUGGESTIONS } from "./data";

// Each "conversation" = { id, title, preview, time, messages[] }
const initConversation = () => ({
    id: Date.now(),
    title: "New Conversation",
    preview: "",
    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    messages: [
        {
            role: "assistant",
            text: "Namaste! 🙏 I'm your SupplyChain Copilot. I can help with dealer briefings, visit planning, commitment tracking, and demand forecasting. How can I help?",
            time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            agent: "Supervisor",
        },
    ],
});

export default function ChatTab() {
    const [conversations, setConversations] = useState([initConversation()]);
    const [activeId, setActiveId] = useState(conversations[0].id);
    const [input, setInput] = useState("");
    const [typing, setTyping] = useState(false);
    const chatEnd = useRef(null);

    const active = conversations.find(c => c.id === activeId);

    useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [active?.messages, typing]);

    const newConversation = () => {
        const c = initConversation();
        setConversations(prev => [c, ...prev]);
        setActiveId(c.id);
        setInput("");
    };

    const sendChat = useCallback(() => {
        if (!input.trim()) return;
        const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const userMsg = { role: "user", text: input, time: now };
        const firstMsg = active.messages.length === 1; // only welcome message

        setConversations(prev => prev.map(c => c.id !== activeId ? c : {
            ...c,
            title: firstMsg ? input.slice(0, 36) + (input.length > 36 ? "…" : "") : c.title,
            preview: input.slice(0, 45) + (input.length > 45 ? "…" : ""),
            time: now,
            messages: [...c.messages, userMsg],
        }));
        setInput("");
        setTyping(true);

        // TODO: Replace with real Bedrock supervisor agent call via /api/chat
        const q = input.toLowerCase();
        setTimeout(() => {
            let r = { agent: "Supervisor", text: "I can help you with:\n\n• Dealer Briefing — \"Brief me for [dealer name]\"\n• Visit Planning — \"Plan my visits this week\"\n• Commitment Tracking — \"Show commitment pipeline\"\n• Demand Forecast — \"Forecast for [product]\"\n• Collections — \"Kitna collection hua?\"\n• Risk Alerts — \"Show at-risk dealers\"" };

            if (q.includes("sharma") || q.includes("brief")) {
                r = { agent: "Dealer Intelligence Agent", text: "📋 Dealer Brief: Sharma General Store\n\n🏢 Platinum (A) Dealer — Central Delhi\n📊 Monthly Revenue: ₹8.92L (↑12% vs last quarter)\n💰 Outstanding: ₹45,000 (within credit limit)\n📅 Last Visit: 2 days ago by Ankan Bera\n\nActive Commitments (3):\n• 500 cases Premium Soap — due next Tuesday\n• 200 cases Industrial Cleaner — due Mar 10\n• Trial order: New range samples requested\n\nSuggested Talking Points:\n1. Follow up on Premium Soap delivery\n2. Discuss new product range\n3. Competitor pricing — consider loyalty discount" };
            } else if (q.includes("plan") && q.includes("visit")) {
                r = { agent: "Sales Analytics Agent", text: "📅 Visit Plan — This Week\n\nPriority 1 — URGENT 🔴\n• Gupta Traders (East Delhi) — ₹3.2L overdue, 25 days gap\n• Mehta Supplies (North Delhi) — ₹1.89L overdue, 45 days\n\nPriority 2 — Follow-up 🟡\n• Joshi Retail Hub — Payment follow-up\n• Nair Distributors — Declining orders\n\nPriority 3 — Growth 🟢\n• Sharma General Store — Confirm 500 case commitment\n• Reddy & Sons — Upsell new range" };
            } else if (q.includes("risk") || q.includes("at-risk")) {
                r = { agent: "Dealer Intelligence Agent", text: "⚠️ At-Risk Dealers (4)\n\n🔴 Critical:\n• Mehta Supplies — ₹1.89L overdue, 45 days no visit\n\n🟡 At-Risk:\n• Gupta Traders — ₹3.2L overdue, declining frequency\n• Joshi Retail Hub — ₹1.56L overdue\n• Nair Distributors — ₹2.1L overdue" };
            } else if (q.includes("forecast") || q.includes("demand")) {
                r = { agent: "Order Planning Agent", text: "📈 Demand Forecast — Premium Soap\n\nNext 4 Weeks:\n• W1: 1,200 cases (850 committed + 350 forecast)\n• W2: 980 cases (620 committed + 360 forecast)\n• W3: 1,100 cases (400 committed + 700 forecast)\n• W4: 950 cases (200 committed + 750 forecast)\n\nConfidence: 78% | 15% higher than same period last year" };
            } else if (q.includes("collection") || q.includes("kitna") || q.includes("mahine")) {
                r = { agent: "Dealer Intelligence Agent", text: "💰 Collections — March 2026\n\nTotal: ₹17.0L / ₹30.0L target (56.7%)\n\nTop Collected:\n• Reddy & Sons: ₹4.8L ✅\n• Das Trading: ₹4.2L ✅\n• Sharma General Store: ₹3.9L ✅\n\nPending:\n• Gupta Traders: ₹3.2L (25 days overdue)\n• Nair Distributors: ₹2.1L\n• Mehta Supplies: ₹1.89L (45 days!)" };
            } else if (q.includes("log") || q.includes("visit")) {
                r = { agent: "Visit Capture Agent", text: "Sure! To log a visit, please tell me:\n1. Which dealer did you visit?\n2. What commitments were made?\n3. Any payment collected?\n\nExample: \"Visited Sharma General Store, they committed 500 cases of Premium Soap by Tuesday, collected ₹45K\"" };
            } else if (q.includes("commitment") || q.includes("pipeline")) {
                r = { agent: "Visit Capture Agent", text: "📋 Commitment Pipeline\n\nTotal: 500 commitments\n\n✅ Converted: 275 (₹18.2L) — 55%\n🟡 Pending: 90 (₹7.8L) — 18%\n🔵 Partial: 60 (₹5.4L) — 12%\n🔴 Expired: 60 (₹3.4L) — 12%\n⛔ Cancelled: 15 (₹1.2L) — 3%\n\nConversion Rate: 67%" };
            }

            const agentMsg = { role: "assistant", ...r, time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) };
            setConversations(prev => prev.map(c => c.id !== activeId ? c : { ...c, messages: [...c.messages, agentMsg] }));
            setTyping(false);
        }, 1400);
    }, [input, activeId, active]);

    const msgs = active?.messages || [];

    return (
        <div style={{ display: "flex", height: "100%" }}>

            {/* ── Chat History Sidebar ── */}
            <div style={{ width: 240, borderRight: "1px solid " + T.cardBorder, background: "#fff", display: "flex", flexDirection: "column" }}>
                <div style={{ padding: "14px 14px 10px", borderBottom: "1px solid " + T.cardBorder }}>
                    <button onClick={newConversation} style={{
                        display: "flex", alignItems: "center", justifyContent: "center", gap: 6, width: "100%",
                        background: "linear-gradient(135deg,#6366f1,#818cf8)", color: "#fff", border: "none",
                        borderRadius: 10, padding: "9px 12px", fontSize: 12, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
                    }}>
                        <Plus size={14} /> New Conversation
                    </button>
                </div>
                <div style={{ flex: 1, overflow: "auto", padding: "8px 8px" }}>
                    <div style={{ fontSize: 10, fontWeight: 600, color: T.textLight, letterSpacing: "0.8px", textTransform: "uppercase", padding: "6px 8px 4px" }}>History</div>
                    {conversations.map(c => (
                        <button key={c.id} onClick={() => setActiveId(c.id)} style={{
                            display: "block", width: "100%", textAlign: "left", padding: "10px 10px", marginBottom: 2,
                            background: c.id === activeId ? T.primarySoft : "transparent",
                            border: "none", borderRadius: 10, cursor: "pointer", fontFamily: "inherit",
                            transition: "background .15s",
                        }}
                            onMouseEnter={e => { if (c.id !== activeId) e.currentTarget.style.background = T.bg; }}
                            onMouseLeave={e => { if (c.id !== activeId) e.currentTarget.style.background = "transparent"; }}
                        >
                            <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                                <div style={{ marginTop: 2, flexShrink: 0 }}>
                                    <MessageSquare size={13} color={c.id === activeId ? T.primary : T.textMuted} />
                                </div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: 12, fontWeight: c.id === activeId ? 700 : 500, color: c.id === activeId ? T.primary : T.heading, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title}</div>
                                    {c.preview && <div style={{ fontSize: 10, color: T.textMuted, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.preview}</div>}
                                    <div style={{ display: "flex", alignItems: "center", gap: 3, marginTop: 3 }}>
                                        <Clock size={9} color={T.textLight} />
                                        <span style={{ fontSize: 9, color: T.textLight }}>{c.time}</span>
                                    </div>
                                </div>
                            </div>
                        </button>
                    ))}
                </div>
                <div style={{ padding: "10px 12px", borderTop: "1px solid " + T.cardBorder, fontSize: 10, color: T.textLight, textAlign: "center", background: T.bg }}>
                    <div style={{ fontWeight: 600, color: T.textMuted, marginBottom: 2 }}>Active Agents</div>
                    {["Supervisor", "Dealer Intel", "Visit Capture", "Order Planning"].map(a => (
                        <div key={a} style={{ display: "inline-flex", alignItems: "center", gap: 3, margin: "1px 3px" }}>
                            <div style={{ width: 5, height: 5, borderRadius: "50%", background: T.green }} />
                            <span>{a}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── Chat Main ── */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
                <div style={{ flex: 1, overflow: "auto", padding: "24px 32px" }}>
                    <div style={{ maxWidth: 780, margin: "0 auto" }}>
                        {msgs.map((m, i) => (
                            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", marginBottom: 16, animation: i === msgs.length - 1 ? "slideUp .3s ease both" : "none" }}>
                                {m.role === "assistant" && (
                                    <div style={{ width: 34, height: 34, borderRadius: 10, marginRight: 10, flexShrink: 0, background: "linear-gradient(135deg,#6366f1,#ec4899)", display: "flex", alignItems: "center", justifyContent: "center", marginTop: 4 }}>
                                        <Bot size={16} color="#fff" />
                                    </div>
                                )}
                                <div style={{ maxWidth: "72%" }}>
                                    {m.role === "assistant" && m.agent && (
                                        <div style={{ fontSize: 10, color: T.primary, marginBottom: 4, fontWeight: 600, display: "flex", alignItems: "center", gap: 3 }}>
                                            <Sparkles size={10} /> {m.agent}
                                        </div>
                                    )}
                                    <div style={{
                                        padding: "12px 16px", borderRadius: 14, fontSize: 13, lineHeight: 1.65, whiteSpace: "pre-wrap",
                                        background: m.role === "user" ? "linear-gradient(135deg,#6366f1,#818cf8)" : "#fff",
                                        border: m.role === "user" ? "none" : "1px solid " + T.cardBorder,
                                        color: m.role === "user" ? "#fff" : T.text,
                                        boxShadow: m.role === "assistant" ? T.cardShadow : "0 2px 8px rgba(99,102,241,0.18)",
                                        borderTopRightRadius: m.role === "user" ? 4 : 14,
                                        borderTopLeftRadius: m.role === "assistant" ? 4 : 14,
                                    }}>{m.text}</div>
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
                                    {[0, 1, 2].map(j => <div key={j} style={{ width: 7, height: 7, borderRadius: "50%", background: T.primary, animation: "dotBounce 1.2s ease " + j * .2 + "s infinite" }} />)}
                                </div>
                            </div>
                        )}
                        <div ref={chatEnd} />
                    </div>
                </div>

                {/* Suggestion chips — only on fresh conversation */}
                {msgs.length <= 1 && (
                    <div style={{ padding: "0 32px 10px", maxWidth: 812, margin: "0 auto", width: "100%", display: "flex", flexWrap: "wrap", gap: 7 }}>
                        {CHAT_SUGGESTIONS.map((s, i) => (
                            <button key={i} onClick={() => setInput(s)} style={{ padding: "7px 13px", borderRadius: 10, background: "#fff", border: "1px solid " + T.cardBorder, color: T.textMuted, fontSize: 11.5, cursor: "pointer", transition: "all .2s", fontFamily: "inherit" }}
                                onMouseEnter={e => { e.target.style.borderColor = "#c7c8f2"; e.target.style.color = T.primary; e.target.style.background = T.primarySoft; }}
                                onMouseLeave={e => { e.target.style.borderColor = T.cardBorder; e.target.style.color = T.textMuted; e.target.style.background = "#fff"; }}
                            >{s}</button>
                        ))}
                    </div>
                )}

                {/* Input box */}
                <div style={{ padding: "14px 32px 18px", borderTop: "1px solid " + T.cardBorder, background: "#fff" }}>
                    <div style={{ maxWidth: 780, margin: "0 auto", display: "flex", alignItems: "center", gap: 10, background: T.bg, border: "1px solid " + T.cardBorder, borderRadius: 14, padding: "4px 4px 4px 16px" }}>
                        <input
                            value={input} onChange={e => setInput(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendChat()}
                            placeholder="Ask your SupplyChain Copilot… (Hindi / English / Hinglish)"
                            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: T.heading, fontSize: 13, fontFamily: "'DM Sans',system-ui" }}
                        />
                        <button onClick={sendChat} style={{
                            width: 40, height: 40, borderRadius: 10, cursor: input.trim() ? "pointer" : "default",
                            background: input.trim() ? "linear-gradient(135deg,#6366f1,#818cf8)" : T.bg,
                            border: input.trim() ? "none" : "1px solid " + T.cardBorder,
                            display: "flex", alignItems: "center", justifyContent: "center",
                            transition: "background .2s",
                        }}>
                            <Send size={16} color={input.trim() ? "#fff" : T.textLight} />
                        </button>
                    </div>
                    <div style={{ textAlign: "center", marginTop: 7, fontSize: 10, color: T.textLight }}>
                        Powered by Bedrock Multi-Agent · Supervisor → Dealer Intel · Visit Capture · Order Planning
                    </div>
                </div>
            </div>
        </div>
    );
}
