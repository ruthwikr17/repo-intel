import { useState } from 'react';

interface Props {
  repoId: number;
  opportunityId: number;
  opportunityTitle: string;
}

export function AIHelperButtons({ repoId, opportunityId, opportunityTitle }: Props) {
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState('');

  const fetchContext = async (): Promise<string> => {
    const res = await fetch(`/api/repos/${repoId}/opportunities/${opportunityId}/ai-context`);
    const data = await res.json();
    return data.context_prompt;
  };

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const handleChatGPT = async () => {
    setLoading(true);
    try {
      const prompt = await fetchContext();
      const encoded = encodeURIComponent(prompt);
      // ChatGPT URL limit ~2000 chars - truncate if needed
      const safeEncoded = encoded.length > 2000
        ? encodeURIComponent(prompt.slice(0, 1400) + '\n\n[Context truncated - ask me for more details]')
        : encoded;
      window.open(`https://chat.openai.com/?q=${safeEncoded}`, '_blank');
      showToast('Opening ChatGPT with project context...');
    } catch (e) {
      showToast('Failed to load context. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleGemini = async () => {
    setLoading(true);
    try {
      const prompt = await fetchContext();
      await navigator.clipboard.writeText(prompt);
      window.open('https://gemini.google.com/app', '_blank');
      showToast('✅ Context copied! Paste in Gemini (Cmd+V / Ctrl+V)');
    } catch (e) {
      showToast('Failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClaude = async () => {
    setLoading(true);
    try {
      const prompt = await fetchContext();
      await navigator.clipboard.writeText(prompt);
      window.open('https://claude.ai', '_blank');
      showToast('✅ Context copied to clipboard! Paste it in Claude (Cmd+V / Ctrl+V)');
    } catch (e) {
      showToast('Failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const buttons = [
    {
      label: 'ChatGPT',
      icon: '🤖',
      color: '#10a37f',
      onClick: handleChatGPT,
      note: '(opens with context)',
    },
    {
      label: 'Gemini',
      icon: '✨',
      color: '#1a73e8',
      onClick: handleGemini,
      note: '(copies + opens)',
    },
    {
      label: 'Claude',
      icon: '🔮',
      color: '#d97757',
      onClick: handleClaude,
      note: '(copies + opens)',
    },
  ];


  return (
    <div>
      <p
        className="text-xs font-medium mb-2"
        style={{ color: '#57606a' }}
      >
        Get AI help implementing this:
      </p>

      <div className="flex gap-2 flex-wrap">
        {buttons.map((btn) => (
          <button
            key={btn.label}
            onClick={btn.onClick}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium text-white transition-opacity"
            style={{
              backgroundColor: btn.color,
              opacity: loading ? 0.6 : 1,
            }}
          >
            <span>{btn.icon}</span>
            <span>Ask {btn.label}</span>
            {btn.note && (
              <span style={{ opacity: 0.8, fontSize: '10px' }}>{btn.note}</span>
            )}
          </button>
        ))}
      </div>

      {toast && (
        <div
          className="mt-2 text-xs px-3 py-2 rounded"
          style={{
            backgroundColor: '#dafbe1',
            color: '#2ea44f',
            border: '1px solid #9be9a8',
          }}
        >
          {toast}
        </div>
      )}

      <p
        className="text-xs mt-2"
        style={{ color: '#8b949e' }}
      >
        Full project context + this task is passed to the AI automatically.
      </p>
    </div>
  );
}
