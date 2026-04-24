import ReactMarkdown from "react-markdown";

export function MarkdownBlock({ children, className = "markdown" }) {
  return (
    <div className={className}>
      <ReactMarkdown>{children || ""}</ReactMarkdown>
    </div>
  );
}
