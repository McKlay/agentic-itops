import AppShell from './components/layout/AppShell';
import WorkspaceHeader from './components/layout/WorkspaceHeader';
import { useUiStore } from './store/uiStore';
import HomePage from './components/pages/HomePage';
import IncidentsPage from './components/pages/IncidentsPage';
import ProblemsPage from './components/pages/ProblemsPage';
import ChangesPage from './components/pages/ChangesPage';
import ObservabilityPage from './components/pages/ObservabilityPage';
import PerformancePage from './components/pages/PerformancePage';
import Conversation from './components/chat/Conversation';
import Composer from './components/chat/Composer';
import SettingsModal from './components/modals/SettingsModal';
import ProfileModal from './components/modals/ProfileModal';
import HelpModal from './components/modals/HelpModal';

function PageContent() {
  const currentView = useUiStore((s) => s.currentView);

  switch (currentView) {
    case 'home':
      return <HomePage />;
    case 'incidents':
      return <IncidentsPage />;
    case 'problems':
      return <ProblemsPage />;
    case 'changes':
      return <ChangesPage />;
    case 'observability':
      return <ObservabilityPage />;
    case 'performance':
      return <PerformancePage />;
    case 'conversation':
      return <Conversation />;
    default:
      return <HomePage />;
  }
}

const composerViews = new Set<string>(['home', 'conversation']);

function Workspace() {
  const currentView = useUiStore((s) => s.currentView);
  const showComposer = composerViews.has(currentView);

  return (
    <>
      <WorkspaceHeader />
      <div className="relative flex-1 flex flex-col overflow-hidden">
        <div className={`flex-1 overflow-y-auto ${showComposer ? 'pb-28' : ''}`}>
          <PageContent />
        </div>
        {showComposer && (
          <div className="absolute bottom-0 left-0 right-0 z-10">
            <Composer />
          </div>
        )}
      </div>
    </>
  );
}

function App() {
  return (
    <>
      <AppShell>
        <Workspace />
      </AppShell>
      <SettingsModal />
      <ProfileModal />
      <HelpModal />
    </>
  );
}

export default App;
