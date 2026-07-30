import { useSettingsStore } from '../../store/settingsStore';
import { useUiStore } from '../../store/uiStore';
import { profileInitials } from '../../utils/helpers';

export default function ProfileModal() {
  const { profileOpen, setProfileOpen } = useSettingsStore();
  const currentRole = useUiStore((s) => s.currentRole);

  if (!profileOpen) return null;

  const userName = 'John Doe';
  const email = 'john.doe@example.com';

  return (
    <div className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-[slideIn_0.2s_ease-out]" onClick={() => setProfileOpen(false)}>
      <div className="w-full max-w-md rounded-2xl bg-[var(--surface)] border border-[var(--line)] shadow-[var(--shadow-lg)] overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--line)]">
          <h2 className="text-lg font-bold text-[var(--text)]">Profile</h2>
          <button
            type="button"
            onClick={() => setProfileOpen(false)}
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[var(--muted)] hover:text-[var(--text)] hover:bg-[var(--surface-soft)] transition-all"
          >
            ✕
          </button>
        </div>

        <div className="px-6 py-6 flex flex-col items-center text-center">
          <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--purple)] to-[#a855f7] flex items-center justify-center text-white text-xl font-bold mb-4 shadow-lg">
            {profileInitials(userName)}
          </div>
          <h3 className="text-lg font-bold text-[var(--text)]">{userName}</h3>
          <p className="text-[13px] text-[var(--muted)] mt-1">{email}</p>
          <div className="mt-4 grid grid-cols-2 gap-3 w-full">
            <div className="rounded-xl bg-[var(--surface-soft)] border border-[var(--line)] px-4 py-3">
              <div className="text-[11px] text-[var(--muted)] uppercase tracking-wider">Role</div>
              <div className="text-[13px] font-semibold text-[var(--text)] mt-1">{currentRole}</div>
            </div>
            <div className="rounded-xl bg-[var(--surface-soft)] border border-[var(--line)] px-4 py-3">
              <div className="text-[11px] text-[var(--muted)] uppercase tracking-wider">Status</div>
              <div className="text-[13px] font-semibold text-[var(--green)] mt-1">Logged in</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
