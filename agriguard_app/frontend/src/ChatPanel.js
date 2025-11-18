import React, { useState } from "react";
import { sendChat } from "./api";

function ChatPanel({ countyId }) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();

    if (!question.trim()) return;

    setLoading(true);
    setError("");
    setAnswer("");

    try {
      const data = await sendChat(question, countyId);
      setAnswer(data.answer);
    } catch (err) {
      console.error(err);
      setError("Failed to get a response from the assistant.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="ChatPanel">
      <h2>Assistant</h2>

      <form onSubmit={handleSubmit} style={{ marginBottom: "1rem" }}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={4}
          style={{ width: "100%" }}
          placeholder={
            countyId
              ? `Ask about stress, NDVI, yield, or trends for FIPS ${countyId}…`
              : "Ask a question (select a county for county-specific answers)…"
          }
        />

        <div style={{ marginTop: "0.5rem" }}>
          <button type="submit" disabled={loading || !question.trim()}>
            {loading ? "Asking…" : "Ask"}
          </button>
        </div>
      </form>

      {error && (
        <div style={{ color: "red", marginBottom: "0.75rem" }}>{error}</div>
      )}

      {answer && (
        <div
          style={{
            padding: "0.75rem",
            borderRadius: "4px",
            border: "1px solid #ddd",
            background: "#fafafa",
          }}
        >
          <strong>Answer:</strong>
          <div>{answer}</div>
        </div>
      )}
    </div>
  );
}

export default ChatPanel;
