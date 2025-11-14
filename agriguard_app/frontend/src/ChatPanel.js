import React, { useState } from "react";

function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSend(event) {
    event.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMessage = { role: "user", content: trimmed };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setErrorMsg("");
    setIsThinking(true);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmed })
      });

      if (!res.ok) {
        throw new Error("Chat request failed");
      }

      const data = await res.json();
      const assistantMessage = {
        role: "assistant",
        content: data.answer || "No answer returned."
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error(err);
      setErrorMsg("There was a problem contacting the AI assistant.");
    } finally {
      setIsThinking(false);
    }
  }

  return (
    <div className="card chat-panel">
      <h2>Chat with AgriGuard</h2>

      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-placeholder">
            Ask about crop stress, yield, or field conditions…
          </p>
        )}

        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`chat-bubble ${m.role === "user" ? "user" : "assistant"}`}
          >
            <span className="role-label">
              {m.role === "user" ? "You" : "AgriGuard"}
            </span>
            <p>{m.content}</p>
          </div>
        ))}

        {isThinking && (
          <div className="chat-bubble assistant thinking">
            <span className="role-label">AgriGuard</span>
            <p>Thinking…</p>
          </div>
        )}

        {errorMsg && <p className="error-text">{errorMsg}</p>}
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask about your fields…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button type="submit" disabled={!input.trim() || isThinking}>
          Send
        </button>
      </form>
    </div>
  );
}

export default ChatPanel;