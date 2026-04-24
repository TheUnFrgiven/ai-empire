const MODE_DESC = {
  cloud: "Single OpenRouter model. Fast, direct answers.",
  council: "All configured providers answer side by side.",
  debate: "Providers answer, critique, revise, then synthesize one final response.",
};

const ACCENT = {
  cloud: "#3b82f6",
  council: "#8b5cf6",
  debate: "#f59e0b",
};

export function ModeSelector({ mode, onChange }) {
  return (
    <>
      <div className="modeRow">
        {["cloud", "council", "debate"].map((item) => (
          <button
            key={item}
            className={`modeBtn ${mode === item ? "modeBtn--active" : ""}`}
            style={mode === item ? { borderColor: ACCENT[item], color: ACCENT[item] } : {}}
            onClick={() => onChange(item)}
          >
            {item}
          </button>
        ))}
      </div>
      <p className="modeDesc">{MODE_DESC[mode]}</p>
    </>
  );
}
