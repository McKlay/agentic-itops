import { useSettingsStore } from '../../store/settingsStore';

export default function HelpModal() {
  const { helpOpen, setHelpOpen } = useSettingsStore();

  if (!helpOpen) return null;

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-[slideIn_0.2s_ease-out]" onClick={() => setHelpOpen(false)}>
      <div className="w-full max-w-xl rounded-2xl bg-[var(--surface)] border border-[var(--line)] shadow-[var(--shadow-lg)] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--line)]">
          <h2 className="text-lg font-bold text-[var(--text)]">Help</h2>
          <button
            type="button"
            onClick={() => setHelpOpen(false)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-6 space-y-4">
          <section>
            <h3 className="text-sm font-bold text-[var(--text)] mb-2">About SwiftAssist AI</h3>
            <p className="text-[13px] text-[var(--muted)] leading-relaxed">
              SwiftAssist AI is an approval-first, enterprise agentic IT Operations platform. It orchestrates 
              AI agents to triage incidents, retrieve knowledge, draft RCA reports, and manage ServiceNow records.
            </p>
          </section>

          <section>
            <h3 className="text-sm font-bold text-[var(--text)] mb-2">Approval-First Design</h3>
            <p className="text-[13px] text-[var(--muted)] leading-relaxed">
              All agent-generated actions require explicit human approval before any data is written to 
              production systems. No autonomous remediation, closure, publication, or production changes 
              are permitted.
            </p>
          </section>

          <section>
            <h3 className="text-sm font-bold text-[var(--text)] mb-2">Key Capabilities</h3>
            <ul className="list-disc pl-5 text-[13px] text-[var(--muted)] space-y-1">
              <li>Incident triage and resolution recommendations</li>
              <li>Knowledge base search and draft creation</li>
              <li>RCA/CAP report generation for problem management</li>
              <li>Blameless postmortem drafting</li>
              <li>Monitoring and governance alerting</li>
              <li>Multi-role persona support</li>
            </ul>
          </section>

          <section>
            <h3 className="text-sm font-bold text-[var(--text)] mb-2">Getting Started</h3>
            <p className="text-[13px] text-[var(--muted)] leading-relaxed">
              Use the chat interface to ask questions, or navigate to specific pages via the sidebar. 
              Quick action cards on the home page provide common starting points.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
