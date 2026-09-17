// .semgrep/tests/react_dangerous_html.jsx
import DOMPurify from "dompurify";

function BadComment({ html }) {
  // ruleid: react-dangerous-html-unsanitized
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

function GoodComment({ html }) {
  // ok: react-dangerous-html-unsanitized
  return <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }} />;
}
