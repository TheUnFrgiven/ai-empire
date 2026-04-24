import { MarkdownBlock } from "./MarkdownBlock";

const PROVIDER_COLOR = {
  Gemini: "#7c3aed",
  Grok: "#38bdf8",
  Groq: "#f97316",
  Ollama: "#22c55e",
  OpenAI: "#10a37f",
  "Mistral AI": "#ff7000",
  Meta: "#0866ff",
};

export function ModelCard({ data, role }) {
  if (!data) return null;
  const provider = data.provider || "Unknown";
  const providerColor = PROVIDER_COLOR[provider] || "#64748b";
  const text = data.text || data.answer || "";

  return (
    <div className="modelCard">
      <div className="modelCardHeader">
        <span className="modelName">{data.model || data.label || provider}</span>
        <div className="modelBadges">
          <span
            className="badge providerBadge"
            style={{ background: `${providerColor}20`, color: providerColor, borderColor: `${providerColor}55` }}
          >
            {provider}
          </span>
          {role && <span className="badge roleBadge">{role}</span>}
        </div>
      </div>
      {data.error ? (
        <p className="modelError">{data.error}</p>
      ) : (
        <MarkdownBlock className="modelText">{text || "No response"}</MarkdownBlock>
      )}
    </div>
  );
}
