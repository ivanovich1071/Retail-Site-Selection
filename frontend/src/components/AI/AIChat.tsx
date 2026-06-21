import { useState, useRef, useEffect, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { Button, Input, Tooltip, Tag, Spin } from "antd";
import {
  RobotOutlined, CloseOutlined, SendOutlined, ClearOutlined,
} from "@ant-design/icons";
import { aiChat } from "../../services/api";

interface Msg {
  role: "user" | "assistant";
  content: string;
  meta?: { mode?: string; model?: string; intent?: string; tools?: string[] };
}

const WELCOME: Msg = {
  role: "assistant",
  content:
    "Привет! Я геоаналитический ассистент. Спросите про потенциал площадки, " +
    "долю рынка (Хафф), каннибализацию или белые пятна рынка.",
};

export default function AIChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([WELCOME]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const bodyRef = useRef<HTMLDivElement>(null);
  const routerLoc = useLocation();

  // Hide on the login screen.
  const hidden = routerLoc.pathname.startsWith("/login");

  // Context-aware: pass current location id when on a location detail page.
  const buildContext = useCallback(() => {
    const m = routerLoc.pathname.match(/^\/locations\/(\d+)/);
    return m ? { location_id: Number(m[1]) } : undefined;
  }, [routerLoc.pathname]);

  useEffect(() => {
    if (open && bodyRef.current) {
      bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
    }
  }, [messages, open, loading]);

  const send = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const history = messages
      .filter((m) => m !== WELCOME)
      .map((m) => ({ role: m.role, content: m.content }));

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);
    try {
      const res = await aiChat(text, buildContext(), history);
      const tools = (res.tool_trace || []).map((t: any) => t.tool);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.answer || "(пустой ответ)",
          meta: { mode: res.mode, model: res.model, intent: res.intent, tools },
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Ошибка обращения к ассистенту: " +
            (err?.response?.data?.detail || err?.message || "неизвестная ошибка"),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (hidden) return null;

  // Collapsed launcher button.
  if (!open) {
    return (
      <Tooltip title="AI-ассистент" placement="right">
        <Button
          type="primary"
          shape="circle"
          size="large"
          icon={<RobotOutlined />}
          onClick={() => setOpen(true)}
          style={{
            position: "fixed", left: 20, bottom: 20, zIndex: 1100,
            width: 52, height: 52, boxShadow: "0 4px 14px rgba(0,0,0,0.3)",
          }}
        />
      </Tooltip>
    );
  }

  return (
    <div
      style={{
        position: "fixed", left: 16, bottom: 16, zIndex: 1100,
        width: 380, maxWidth: "calc(100vw - 32px)",
        height: "25vh", minHeight: 240,
        background: "#fff", borderRadius: 10,
        boxShadow: "0 6px 24px rgba(0,0,0,0.25)",
        display: "flex", flexDirection: "column", overflow: "hidden",
        border: "1px solid #e0e0e0",
      }}
    >
      {/* Header */}
      <div style={{
        background: "#1a5276", color: "#fff", padding: "8px 12px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <span style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 8 }}>
          <RobotOutlined /> AI-ассистент
        </span>
        <span>
          <Tooltip title="Очистить">
            <Button
              type="text" size="small" icon={<ClearOutlined />}
              style={{ color: "#fff" }}
              onClick={() => setMessages([WELCOME])}
            />
          </Tooltip>
          <Tooltip title="Свернуть">
            <Button
              type="text" size="small" icon={<CloseOutlined />}
              style={{ color: "#fff" }}
              onClick={() => setOpen(false)}
            />
          </Tooltip>
        </span>
      </div>

      {/* Messages (scrollable) */}
      <div
        ref={bodyRef}
        style={{
          flex: 1, overflowY: "auto", padding: "10px 12px",
          background: "#f7f9fb", display: "flex", flexDirection: "column", gap: 8,
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "85%",
            }}
          >
            <div style={{
              background: m.role === "user" ? "#1a5276" : "#fff",
              color: m.role === "user" ? "#fff" : "#1f1f1f",
              padding: "7px 10px", borderRadius: 8,
              border: m.role === "user" ? "none" : "1px solid #e0e0e0",
              whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 13,
              lineHeight: 1.45,
            }}>
              {m.content}
            </div>
            {m.meta && (m.meta.tools?.length || m.meta.mode) && (
              <div style={{ marginTop: 3, display: "flex", gap: 4, flexWrap: "wrap" }}>
                {m.meta.tools?.map((t) => (
                  <Tag key={t} color="blue" style={{ margin: 0, fontSize: 10 }}>{t}</Tag>
                ))}
                {m.meta.mode === "fallback" && (
                  <Tag color="orange" style={{ margin: 0, fontSize: 10 }}>fallback</Tag>
                )}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: "flex-start", padding: "4px 6px" }}>
            <Spin size="small" /> <span style={{ fontSize: 12, color: "#888" }}>думаю…</span>
          </div>
        )}
      </div>

      {/* Input */}
      <div style={{ display: "flex", gap: 6, padding: 8, borderTop: "1px solid #eee" }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Спросите про локацию…"
          autoSize={{ minRows: 1, maxRows: 3 }}
          onPressEnter={(e) => { e.preventDefault(); send(); }}
          disabled={loading}
        />
        <Button
          type="primary" icon={<SendOutlined />}
          onClick={send} loading={loading} disabled={!input.trim()}
        />
      </div>
    </div>
  );
}
