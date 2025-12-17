import React, { useState } from 'react';
import VoiceIndicator from './components/VoiceIndicator';
import CodeEditor from './components/CodeEditor';
import Terminal from './components/Terminal';

const App: React.FC = () => {
  const [isVoiceActive, setIsVoiceActive] = useState(false);
  const [code, setCode] = useState(`// Voice-Controlled Claude Code Assistant
// Speak your commands and watch the magic happen!

function greet(name: string): string {
  return \`Hello, \${name}! Welcome to the voice-controlled coding assistant.\`;
}

console.log(greet("Developer"));
`);

  const handleVoiceToggle = () => {
    setIsVoiceActive(!isVoiceActive);
    // TODO: Connect to backend voice API
    console.log('Voice active:', !isVoiceActive);
  };

  const handleCodeChange = (value: string | undefined) => {
    if (value !== undefined) {
      setCode(value);
    }
  };

  const handleTerminalInput = (data: string) => {
    // TODO: Handle terminal input
    console.log('Terminal input:', data);
  };

  return (
    <div className="app">
      <div className="voice-panel">
        <VoiceIndicator
          isActive={isVoiceActive}
          onToggle={handleVoiceToggle}
        />
      </div>
      <div className="main-content">
        <div className="editor-panel">
          <CodeEditor
            value={code}
            onChange={handleCodeChange}
            readOnly={false}
          />
        </div>
        <div className="terminal-panel">
          <Terminal onInput={handleTerminalInput} />
        </div>
      </div>
    </div>
  );
};

export default App;
