import { useEffect, useRef } from 'react';
import { useChatStore } from '../../store/chatStore';
import MessageBubble from './MessageBubble';
import ArtifactCard from './ArtifactCard';

export default function Conversation() {
  const { activeSessionId, conversations } = useChatStore();
  const messages = conversations[activeSessionId] || [];
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages.length]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="max-w-[760px] mx-auto space-y-5">
        {messages.map((msg) => {
          // Check if message has artifacts
          if (msg.artifacts && msg.artifacts.length > 0) {
            return (
              <div key={msg.id}>
                <MessageBubble message={msg} />
                {msg.artifacts.map((artifact, i) => (
                  <div key={`${msg.id}-artifact-${i}`} className="ml-11 mt-2">
                    <ArtifactCard artifact={artifact} />
                  </div>
                ))}
              </div>
            );
          }
          return <MessageBubble key={msg.id} message={msg} />;
        })}
        <div ref={endRef} />
      </div>
    </div>
  );
}
