import { useState } from "react";
import { MarkdownBlock } from "./MarkdownBlock";
import { ModelCard } from "./ModelCard";

const CONFIDENCE_STYLE = {
  High: { bg: "#052e16", color: "#4ade80", border: "#166534" },
  Medium: { bg: "#431407", color: "#fb923c", border: "#9a3412" },
  Low: { bg: "#450a0a", color: "#f87171", border: "#991b1b" },
};

function Collapsible({ id, title, count, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="collapsible">
      <button className="collapsibleTrigger" onClick={() => setOpen((value) => !value)}>
        <span className="collapsibleTitle">{title}</span>
        <span className="collapsibleMeta">
          {count} item{count !== 1 ? "s" : ""} <span className="chevron">{open ? "▲" : "▼"}</span>
        </span>
      </button>
      {open && <div className="collapsibleBody" id={id}>{children}</div>}
    </div>
  );
}

function CouncilResult({ answer }) {
  const items = Array.isArray(answer.answer) ? answer.answer : Object.values(answer.answer || {});
  const proposals = answer.role_proposals || [];
  return (
    <>
      {proposals.length > 0 && (
        <div className="debateSection">
          <div className="debateSectionLabel">Autonomous Roles</div>
          <div className="rolesRow">
            {proposals.map((proposal) => (
              <div key={`${proposal.provider}-${proposal.role}`} className="roleCard">
                <span className="roleCardProvider">{proposal.provider}</span>
                <span className="roleCardName">{proposal.model}</span>
                <span className="roleCardRole">{proposal.role}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="councilGrid">
        {items.map((item) => (
          <ModelCard key={`${item.provider}-${item.model}`} data={item} role={item.role} />
        ))}
      </div>
    </>
  );
}

function DebateResult({ answer }) {
  const round1 = answer.round1 || [];
  const round2 = answer.round2 || [];
  const roles = answer.round0_roles || {};
  const proposals = answer.role_proposals || [];
  const stages = answer.stages || [];
  const confidence = answer.confidence || "Medium";
  const confidenceStyle = CONFIDENCE_STYLE[confidence] || CONFIDENCE_STYLE.Medium;

  return (
    <div className="debateLayout">
      {proposals.length > 0 && (
        <div className="debateSection">
          <div className="debateSectionLabel">Autonomous Roles</div>
          <div className="rolesRow">
            {proposals.map((proposal) => (
              <div key={`${proposal.provider}-${proposal.role}`} className="roleCard">
                <span className="roleCardProvider">{proposal.provider}</span>
                <span className="roleCardName">{proposal.model}</span>
                <span className="roleCardRole">{proposal.role}</span>
                {proposal.reason && <span className="roleCardReason">{proposal.reason}</span>}
                {!proposal.autonomous && <span className="roleCardFallback">Fallback role</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {stages.length > 0 && (
        <div className="stageStrip">
          {stages.map((stage) => (
            <span key={stage.id} className={`stagePill stagePill--${stage.status}`}>
              {stage.label}
            </span>
          ))}
        </div>
      )}

      <div className="finalSection">
        <div className="finalSectionHeader">
          <span className="debateSectionLabel">Final Synthesized Answer</span>
          <span
            className="confBadge"
            style={{
              background: confidenceStyle.bg,
              color: confidenceStyle.color,
              borderColor: confidenceStyle.border,
            }}
          >
            {confidence} Confidence
          </span>
        </div>
        {answer.confidence_reason && <p className="confReason">{answer.confidence_reason}</p>}
        <MarkdownBlock className="finalText">{answer.final_answer || answer.final || ""}</MarkdownBlock>
      </div>

      <Collapsible id="round1" title="Round 1 - Independent Answers" count={round1.length}>
        {round1.map((item) => (
          <ModelCard key={`${item.provider}-${item.model}-r1`} data={item} role={roles[item.provider]} />
        ))}
      </Collapsible>

      <Collapsible id="round2" title="Round 2 - Critiques and Revisions" count={round2.length}>
        {round2.map((item) => (
          <ModelCard key={`${item.provider}-${item.model}-r2`} data={item} role={roles[item.provider]} />
        ))}
      </Collapsible>
    </div>
  );
}

export function Results({ answer, copied, onCopy }) {
  return (
    <div className="answerBox">
      <div className="answerBoxHeader">
        <h2 className="answerTitle">Answer</h2>
        <button className="copyBtn" onClick={onCopy}>
          {copied ? "Copied" : "Copy"}
        </button>
      </div>

      {answer.mode === "cloud" && <MarkdownBlock className="answerText">{answer.answer || answer.error || ""}</MarkdownBlock>}
      {answer.mode === "council" && <CouncilResult answer={answer} />}
      {answer.mode === "council_debate" && <DebateResult answer={answer} />}
    </div>
  );
}
