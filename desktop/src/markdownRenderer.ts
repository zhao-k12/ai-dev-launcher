import MarkdownIt from "markdown-it";

// One parser is shared by every historical message. Constructing a parser per
// message noticeably slows down opening long conversations.
const renderer = new MarkdownIt({ html: false, breaks: true, linkify: true, typographer: true });

export function renderMarkdown(content: string): string {
  return renderer.render(content);
}
