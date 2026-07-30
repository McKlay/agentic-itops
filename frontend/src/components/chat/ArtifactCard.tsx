import { useState } from 'react';
import type { Artifact } from '../../types/api';
import StatusPill from '../shared/StatusPill';

interface ArtifactCardProps {
  artifact: Artifact;
}

export default function ArtifactCard({ artifact }: ArtifactCardProps) {
  const data = artifact.data;
  const type = artifact.type;

  // RCA/CAP Report Card
  if (type === 'rca_report' || type === 'report') {
    return (
      <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-md)] animate-[slideIn_0.3s_ease-out]">
        <div className="px-5 py-4 border-b border-[var(--line)] bg-gradient-to-r from-[var(--green-soft)] to-transparent">
          <h3 className="text-base font-bold text-[#12814b]">{String(data.title || 'RCA/CAP Report')}</h3>
          <p className="text-[12px] text-[var(--muted)] mt-1">
            Confidence: {data.confidence ? `${Number(data.confidence) * 100}%` : 'N/A'} · Human approval required
          </p>
        </div>
        {Boolean(data.executive_summary) && (
          <Section title="Executive Summary">
            <p>{String(data.executive_summary)}</p>
          </Section>
        )}
        {Boolean(data.root_cause) && (
          <Section title="Root Cause Analysis">
            <p>{String(data.root_cause)}</p>
          </Section>
        )}
        {Array.isArray(data.corrective_actions) && (
          <Section title="Corrective Action Plan">
            <ul className="list-disc pl-5 space-y-1">
              {(data.corrective_actions as string[]).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </Section>
        )}
        {Array.isArray(data.evidence) && (
          <Section title="Supporting Evidence">
            <ul className="list-disc pl-5 space-y-1">
              {(data.evidence as string[]).map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          </Section>
        )}
        {Boolean(data.status) && (
          <Section title="Governance">
            <p className="font-medium">Approval Status: {String(data.status)}</p>
          </Section>
        )}
      </div>
    );
  }

  // Incident Card
  if (type === 'incident_card' || type === 'incident') {
    return (
      <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-md)] animate-[slideIn_0.3s_ease-out]">
        <div className="px-5 py-4 border-b border-[var(--line)]">
          <h3 className="text-base font-bold text-[var(--text)]">Incident {String(data.id || '')}</h3>
          <p className="text-[12px] text-[var(--muted)] mt-1">{String(data.title || '')}</p>
        </div>
        <div className="px-5 py-3 grid grid-cols-3 gap-3 text-[12px] border-b border-[var(--line)]">
          <div>
            <span className="text-[var(--muted)]">Status</span>
            <div className="mt-1"><StatusPill status={String(data.status || 'open')} /></div>
          </div>
          <div>
            <span className="text-[var(--muted)]">Priority</span>
            <div className="mt-1 font-semibold text-[var(--text)]">P{String(data.severity || '?')}</div>
          </div>
          <div>
            <span className="text-[var(--muted)]">Service</span>
            <div className="mt-1 font-semibold text-[var(--text)]">{String(data.service || '—')}</div>
          </div>
        </div>
        {Boolean(data.summary) && (
          <Section title="Description">
            <p>{String(data.summary)}</p>
          </Section>
        )}
        <div className="px-5 py-3 flex gap-2">
          <button className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--purple)] text-white hover:bg-[var(--purple-hover)] transition-all shadow-sm">
            Troubleshoot in KB
          </button>
          <button className="px-3 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--surface)] text-[var(--text)] border border-[var(--line)] hover:border-[var(--purple)] transition-all">
            Create KB Draft
          </button>
        </div>
      </div>
    );
  }

  // Knowledge Draft Card
  if (type === 'knowledge_draft') {
    return (
      <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-md)] animate-[slideIn_0.3s_ease-out]">
        <div className="px-5 py-4 border-b border-[var(--line)] bg-gradient-to-r from-[var(--purple-soft)] to-transparent">
          <h3 className="text-base font-bold text-[var(--text)]">{String(data.title || 'Knowledge Draft')}</h3>
          <p className="text-[12px] text-[var(--muted)] mt-1">
            Local knowledge draft · Human validation required
          </p>
        </div>
        {Boolean(data.content) && (
          <Section title="Article Content">
            <div
              className="prose prose-sm max-w-none"
              dangerouslySetInnerHTML={{ __html: String(data.content) }}
            />
          </Section>
        )}
        {data.status === 'pending' && (
          <div className="px-5 py-3 flex gap-2 border-t border-[var(--line)]">
            <button className="px-4 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--green)] text-white hover:opacity-90 transition-all shadow-sm">
              ✓ Approve
            </button>
            <button className="px-4 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--red)] text-white hover:opacity-90 transition-all shadow-sm">
              ✕ Reject
            </button>
          </div>
        )}
      </div>
    );
  }

  // Knowledge Result Card — compact source-attribution card for knowledge_agent citations.
  // Steps and notes are rendered inside the chat bubble (via final_response);
  // this card surfaces only the referenced KB articles.
  if (type === 'knowledge_result') {
    const citations = Array.isArray(data.citations) ? (data.citations as string[]) : [];
    const citationUrls: Record<string, string> =
      data.citation_urls && typeof data.citation_urls === 'object'
        ? (data.citation_urls as Record<string, string>)
        : {};
    const confidence = typeof data.confidence === 'number' ? data.confidence : null;
    const confPct = confidence !== null ? Math.round(confidence * 100) : null;
    const confColor =
      confPct === null ? 'text-[var(--muted)]'
      : confPct >= 80 ? 'text-[var(--green)]'
      : confPct >= 50 ? 'text-amber-500'
      : 'text-[var(--red)]';

    // Source chip collapse — show first 3, expand on demand
    const SOURCES_INITIAL = 3;
    const [showAllSources, setShowAllSources] = useState(false);
    const visibleCitations = showAllSources ? citations : citations.slice(0, SOURCES_INITIAL);
    const hiddenCount = citations.length - SOURCES_INITIAL;

    if (citations.length === 0) return null;

    return (
      <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden shadow-[var(--shadow-sm)] animate-[slideIn_0.3s_ease-out]">

        {/* ── Compact header ── */}
        <div className="px-4 py-2.5 border-b border-[var(--line)] bg-gradient-to-r from-[var(--purple-soft)] to-transparent flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-[var(--purple)] text-[13px]">📖</span>
            <span className="text-[11px] font-bold text-[var(--purple)] tracking-wide uppercase">
              Referenced Sources
            </span>
          </div>
          {confPct !== null && (
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full bg-[var(--surface-raised,var(--surface))] border border-[var(--line)] ${confColor}`}>
              {confPct}% confidence
            </span>
          )}
        </div>

        {/* ── Citation chips ── */}
        <div className="px-4 py-3 flex flex-wrap gap-1.5">
          {visibleCitations.map((cite, i) => {
            const dashIdx = cite.indexOf(' — ');
            const kbFile  = dashIdx !== -1 ? cite.slice(0, dashIdx).trim() : cite.trim();
            const kbNum   = kbFile.replace(/\.pdf$/i, '');
            const kbTitle = dashIdx !== -1 ? cite.slice(dashIdx + 3).trim() : null;
            const url     = citationUrls[cite] ?? null;

            const chipInner = (
              <>
                <span className="shrink-0 w-4 h-4 rounded-full bg-[var(--purple)] text-white text-[9px] font-bold flex items-center justify-center">
                  {i + 1}
                </span>
                <span className="shrink-0 font-semibold text-[11px]">{kbNum}</span>
                {kbTitle && (
                  <span className="text-[10px] opacity-75 truncate min-w-0" title={kbTitle}>
                    &nbsp;·&nbsp;{kbTitle}
                  </span>
                )}
                {url && (
                  <svg className="shrink-0 w-3 h-3 opacity-60 ml-0.5" viewBox="0 0 12 12" fill="none"
                       stroke="currentColor" strokeWidth="1.5">
                    <path d="M5 2H2a1 1 0 0 0-1 1v7a1 1 0 0 0 1 1h7a1 1 0 0 0 1-1V7M7 1h4m0 0v4m0-4L5 7"/>
                  </svg>
                )}
              </>
            );

            const chipClass =
              'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full ' +
              'bg-[var(--purple-soft)] text-[var(--purple)] ' +
              'border border-transparent max-w-[280px] overflow-hidden ' +
              (url
                ? 'cursor-pointer hover:border-[var(--purple)] hover:bg-[var(--purple)] hover:text-white transition-all duration-150'
                : '');

            return url ? (
              <a key={i} href={url} target="_blank" rel="noopener noreferrer"
                 className={chipClass} title={`Open source PDF: ${kbFile}`}>
                {chipInner}
              </a>
            ) : (
              <span key={i} className={chipClass} title={cite}>{chipInner}</span>
            );
          })}

          {!showAllSources && hiddenCount > 0 && (
            <button
              onClick={() => setShowAllSources(true)}
              className="inline-flex items-center px-2.5 py-1 rounded-full border border-dashed border-[var(--line)] text-[11px] text-[var(--muted)] hover:text-[var(--purple)] hover:border-[var(--purple)] transition-colors"
            >
              +{hiddenCount} more
            </button>
          )}
          {showAllSources && hiddenCount > 0 && (
            <button
              onClick={() => setShowAllSources(false)}
              className="inline-flex items-center px-2.5 py-1 rounded-full border border-dashed border-[var(--line)] text-[11px] text-[var(--muted)] hover:text-[var(--purple)] hover:border-[var(--purple)] transition-colors"
            >
              Show less
            </button>
          )}
        </div>
      </div>
    );
  }

  // Approval Required Card — agent output pending human sign-off
  if (type === 'approval_required') {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800 overflow-hidden shadow-[var(--shadow-md)] animate-[slideIn_0.3s_ease-out]">
        <div className="px-5 py-4 border-b border-amber-200 dark:border-amber-800 flex items-center gap-3">
          <span className="text-lg">⏳</span>
          <div>
            <h3 className="text-base font-bold text-amber-700 dark:text-amber-400">Approval Required</h3>
            <p className="text-[12px] text-amber-600 dark:text-amber-500 mt-0.5">
              Agent: {String(data.agent_id ?? 'unknown')}
            </p>
          </div>
        </div>
        <div className="px-5 py-3">
          <p className="text-[13px] text-[var(--text)] leading-relaxed">
            {String(data.summary ?? 'This action requires human approval before it can be executed.')}
          </p>
        </div>
        <div className="px-5 py-3 flex gap-2 border-t border-amber-200 dark:border-amber-800">
          <button className="px-4 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--green)] text-white hover:opacity-90 transition-all shadow-sm">
            ✓ Approve
          </button>
          <button className="px-4 py-1.5 rounded-lg text-[11px] font-semibold bg-[var(--red)] text-white hover:opacity-90 transition-all shadow-sm">
            ✕ Reject
          </button>
        </div>
      </div>
    );
  }

  // Generic fallback
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[var(--shadow-sm)]">
      <pre className="text-[12px] text-[var(--muted)] overflow-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="px-5 py-3 border-b border-[var(--line)] last:border-b-0">
      <h4 className="text-[12px] font-bold text-[var(--text)] uppercase tracking-wider mb-2">{title}</h4>
      <div className="text-[13px] leading-relaxed text-[var(--text)]">{children}</div>
    </div>
  );
}
