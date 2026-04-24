const ACCENT = {
  cloud: "#3b82f6",
  council: "#8b5cf6",
  debate: "#f59e0b",
};

export function PromptBox({
  prompt,
  mode,
  loading,
  onPromptChange,
  onSend,
  onSmartAnalyze,
  onCancel,
}) {
  const accent = ACCENT[mode] || ACCENT.cloud;

  return (
    <>
      <div className="inputWrapper">
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          placeholder="Write your prompt here..."
          disabled={loading}
          style={{ borderColor: prompt.length > 0 ? `${accent}55` : undefined }}
        />
        <span className={`charCount ${prompt.length > 800 ? "charCount--warn" : ""}`}>
          {prompt.length}
        </span>
      </div>

      <div className="actionRow">
        <button
          className="sendBtn"
          style={{ background: accent }}
          onClick={onSend}
          disabled={loading || !prompt.trim()}
        >
          {loading ? "Working..." : `Send (${mode})`}
        </button>
        <button className="smartBtn" onClick={onSmartAnalyze} disabled={loading || !prompt.trim()}>
          Smart Analyze
        </button>
        {loading && (
          <button className="cancelBtn" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
      <p className="hint">Ctrl + Enter to send</p>
    </>
  );
}
