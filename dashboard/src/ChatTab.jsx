import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Sparkles, ChevronRight, Plus, MessageSquare, Clock } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { T, sendChatMessage, sendChatMessageStream, getStreamingUrl } from "./api";
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
            text: "Namaste! 🙏 I'm your SupplyChain Copilot. I can help you with team performance analytics, dealer network health, at-risk dealer reviews, commitment pipeline tracking, revenue insights, and demand forecasting. How can I help?",
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
        setSuggestionsOpen(true);
    };

    const [typingStatus, setTypingStatus] = useState("");
    const [suggestionsOpen, setSuggestionsOpen] = useState(true);

    const sendChat = useCallback(async () => {
        if (!input.trim() || typing) return;
        const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
        const userMsg = { role: "user", text: input, time: now };
        const firstMsg = active.messages.length === 1; // only welcome message
        const msgText = input;
        const convId = activeId;

        setConversations(prev => prev.map(c => c.id !== convId ? c : {
            ...c,
            title: firstMsg ? msgText.slice(0, 36) + (msgText.length > 36 ? "…" : "") : c.title,
            preview: msgText.slice(0, 45) + (msgText.length > 45 ? "…" : ""),
            time: now,
            messages: [...c.messages, userMsg],
        }));
        setInput("");
        setTyping(true);
        setTypingStatus("Thinking...");
        setSuggestionsOpen(false);

        const sessionId = String(convId);

        try {
            if (getStreamingUrl()) {
                // Streaming mode: progressive text + trace steps
                let accumulated = "";
                let detectedAgent = "Supervisor";

                await sendChatMessageStream(msgText, sessionId, {
                    onChunk: (text) => {
                        accumulated += text;
                        setConversations(prev => prev.map(c => {
                            if (c.id !== convId) return c;
                            const msgs = [...c.messages];
                            const last = msgs[msgs.length - 1];
                            if (last && last.role === "assistant" && last._streaming) {
                                msgs[msgs.length - 1] = { ...last, text: accumulated };
                            } else {
                                msgs.push({
                                    role: "assistant", text: accumulated, agent: detectedAgent,
                                    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                                    _streaming: true,
                                });
                            }
                            return { ...c, messages: msgs };
                        }));
                    },
                    onTrace: (step, agent) => {
                        if (agent) detectedAgent = agent;
                        setTypingStatus(step);
                    },
                    onDone: (agent) => {
                        if (agent) detectedAgent = agent;
                        // Finalize: remove _streaming flag, set correct agent
                        setConversations(prev => prev.map(c => {
                            if (c.id !== convId) return c;
                            const msgs = [...c.messages];
                            const last = msgs[msgs.length - 1];
                            if (last && last._streaming) {
                                const { _streaming, ...rest } = last;
                                msgs[msgs.length - 1] = { ...rest, agent: detectedAgent };
                            }
                            return { ...c, messages: msgs };
                        }));
                        setTyping(false);
                        setTypingStatus("");
                    },
                    onError: (errMsg) => {
                        const agentMsg = {
                            role: "assistant", text: errMsg || "Something went wrong. Please try again.",
                            agent: "System", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                        };
                        setConversations(prev => prev.map(c => c.id !== convId ? c : { ...c, messages: [...c.messages, agentMsg] }));
                        setTyping(false);
                        setTypingStatus("");
                    },
                });
            } else {
                // Non-streaming fallback via /api/chat
                const result = await sendChatMessage(msgText, sessionId);
                const agentMsg = {
                    role: "assistant",
                    text: result.text || "No response received.",
                    agent: result.agent || "Supervisor",
                    time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                };
                setConversations(prev => prev.map(c => c.id !== convId ? c : { ...c, messages: [...c.messages, agentMsg] }));
                setTyping(false);
                setTypingStatus("");
            }
        } catch (err) {
            const agentMsg = {
                role: "assistant", text: `Something went wrong: ${err.message}. Please try again.`,
                agent: "System", time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
            };
            setConversations(prev => prev.map(c => c.id !== convId ? c : { ...c, messages: [...c.messages, agentMsg] }));
            setTyping(false);
            setTypingStatus("");
        }
    }, [input, activeId, active, typing]);

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
                                        padding: "12px 16px", borderRadius: 14, fontSize: 13, lineHeight: 1.65,
                                        background: m.role === "user" ? "linear-gradient(135deg,#6366f1,#818cf8)" : "#fff",
                                        border: m.role === "user" ? "none" : "1px solid " + T.cardBorder,
                                        color: m.role === "user" ? "#fff" : T.text,
                                        boxShadow: m.role === "assistant" ? T.cardShadow : "0 2px 8px rgba(99,102,241,0.18)",
                                        borderTopRightRadius: m.role === "user" ? 4 : 14,
                                        borderTopLeftRadius: m.role === "assistant" ? 4 : 14,
                                        whiteSpace: m.role === "user" ? "pre-wrap" : undefined,
                                    }}>
                                        {m.role === "assistant"
                                            ? <div className="chat-md"><Markdown remarkPlugins={[remarkGfm]}>{m.text}</Markdown></div>
                                            : m.text}
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
                                <div style={{ padding: "14px 18px", borderRadius: 14, borderTopLeftRadius: 4, background: "#fff", border: "1px solid " + T.cardBorder, display: "flex", alignItems: "center", gap: 8, boxShadow: T.cardShadow }}>
                                    <div style={{ display: "flex", gap: 5 }}>
                                        {[0, 1, 2].map(j => <div key={j} style={{ width: 7, height: 7, borderRadius: "50%", background: T.primary, animation: "dotBounce 1.2s ease " + j * .2 + "s infinite" }} />)}
                                    </div>
                                    {typingStatus && <span style={{ fontSize: 11, color: T.textMuted, marginLeft: 4 }}>{typingStatus}</span>}
                                </div>
                            </div>
                        )}
                        <div ref={chatEnd} />
                    </div>
                </div>

                {/* Suggestion chips — collapsible, shown after every assistant response */}
                {!typing && msgs.length > 0 && msgs[msgs.length - 1].role === "assistant" && (
                    <div style={{ padding: "0 32px 10px", maxWidth: 812, margin: "0 auto", width: "100%" }}>
                        <button onClick={() => setSuggestionsOpen(o => !o)} style={{
                            display: "flex", alignItems: "center", gap: 5, background: "none", border: "none",
                            cursor: "pointer", color: T.textMuted, fontSize: 11, fontWeight: 600, padding: "2px 0 6px",
                            fontFamily: "inherit",
                        }}>
                            <Sparkles size={11} color={T.primary} />
                            Suggested questions
                            <ChevronRight size={12} style={{ transform: suggestionsOpen ? "rotate(90deg)" : "rotate(0deg)", transition: "transform .2s" }} />
                        </button>
                        {suggestionsOpen && (
                            <div style={{ display: "flex", flexWrap: "wrap", gap: 7 }}>
                                {CHAT_SUGGESTIONS.map((s, i) => (
                                    <button key={i} onClick={() => setInput(s)} style={{ padding: "7px 13px", borderRadius: 10, background: "#fff", border: "1px solid " + T.cardBorder, color: T.textMuted, fontSize: 11.5, cursor: "pointer", transition: "all .2s", fontFamily: "inherit" }}
                                        onMouseEnter={e => { e.target.style.borderColor = "#c7c8f2"; e.target.style.color = T.primary; e.target.style.background = T.primarySoft; }}
                                        onMouseLeave={e => { e.target.style.borderColor = T.cardBorder; e.target.style.color = T.textMuted; e.target.style.background = "#fff"; }}
                                    >{s}</button>
                                ))}
                            </div>
                        )}
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
