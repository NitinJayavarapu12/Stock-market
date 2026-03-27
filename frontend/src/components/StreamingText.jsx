import ReactMarkdown from 'react-markdown'

export default function StreamingText({ text, done }) {
  if (!text) return null
  return (
    <div className="prose prose-invert prose-sm max-w-none text-slate-300 leading-relaxed">
      <ReactMarkdown>{text + (done ? '' : ' ▌')}</ReactMarkdown>
    </div>
  )
}
