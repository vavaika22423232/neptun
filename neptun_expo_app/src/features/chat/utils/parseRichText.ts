export type RichSegment =
  | { type: 'text'; value: string }
  | { type: 'mention'; value: string }
  | { type: 'hashtag'; value: string }
  | { type: 'url'; value: string };

const TOKEN =
  /(@[a-zA-Z0-9_\u0400-\u04FF]{2,20})|(#[\w\u0400-\u04FF]{2,32})|(https?:\/\/[^\s]+)/gu;

export function parseRichText(input: string): RichSegment[] {
  if (!input) return [{ type: 'text', value: '' }];
  const segments: RichSegment[] = [];
  let last = 0;
  for (const match of input.matchAll(TOKEN)) {
    const idx = match.index ?? 0;
    if (idx > last) segments.push({ type: 'text', value: input.slice(last, idx) });
    if (match[1]) segments.push({ type: 'mention', value: match[1] });
    else if (match[2]) segments.push({ type: 'hashtag', value: match[2] });
    else if (match[3]) segments.push({ type: 'url', value: match[3] });
    last = idx + match[0].length;
  }
  if (last < input.length) segments.push({ type: 'text', value: input.slice(last) });
  return segments.length ? segments : [{ type: 'text', value: input }];
}
