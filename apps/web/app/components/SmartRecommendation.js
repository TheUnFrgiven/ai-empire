const MODE_ACCENT = {
  cloud: "#3b82f6",
  council: "#8b5cf6",
  debate: "#f59e0b",
};

export function SmartRecommendation({ smart, onUseMode }) {
  if (!smart) return null;

  const accent = MODE_ACCENT[smart.suggested_mode] || MODE_ACCENT.cloud;
  const signals = (smart.matches?.[smart.suggested_mode] || []).slice(0, 5);
  const alternatives = ["cloud", "council", "debate"].filter((item) => item !== smart.suggested_mode);

  return (
    <div className="smartBox">
      <div className="smartHeader">
        <span className="smartTitle">Smart Recommendation</span>
        <span className="modeBadge" style={{ background: `${accent}22`, color: accent, borderColor: `${accent}55` }}>
          {smart.suggested_mode}
        </span>
      </div>
      <p className="smartReason">{smart.reason}</p>
      {signals.length > 0 && (
        <div className="signalsRow">
          <span className="signalsLabel">Detected signals:</span>
          {signals.map((signal) => (
            <span key={signal} className="signal">{signal}</span>
          ))}
        </div>
      )}
      <div className="smartActions">
        <button className="recommendBtn" style={{ background: accent }} onClick={() => onUseMode(smart.suggested_mode)}>
          Use {smart.suggested_mode}
        </button>
        {alternatives.map((item) => (
          <button key={item} className="altBtn" onClick={() => onUseMode(item)}>
            Use {item}
          </button>
        ))}
      </div>
    </div>
  );
}
