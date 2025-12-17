import React, { useRef, useEffect } from 'react';

interface TerminalProps {
  onInput?: (data: string) => void;
}

const Terminal: React.FC<TerminalProps> = ({ onInput }) => {
  const outputRef = useRef<HTMLDivElement>(null);
  const [lines, setLines] = React.useState<string[]>([
    'Terminal Output',
    '--------------------------------',
    '',
    'Ready for Claude Code output...'
  ]);

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [lines]);

  const handleClear = () => {
    setLines(['Terminal cleared.', '']);
  };

  return (
    <div className="terminal-container">
      <div className="terminal-header">
        <div className="terminal-title">Terminal</div>
        <div className="terminal-controls">
          <button className="terminal-control-btn" onClick={handleClear}>
            Clear
          </button>
        </div>
      </div>
      <div className="terminal-output" ref={outputRef}>
        {lines.map((line, i) => (
          <div key={i} className="terminal-line">{line || '\u00A0'}</div>
        ))}
      </div>
    </div>
  );
};

export default Terminal;
