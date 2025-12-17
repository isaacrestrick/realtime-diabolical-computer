import React, { useEffect, useRef } from 'react';
import { Terminal as XTerm } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

interface TerminalProps {
  onInput?: (data: string) => void;
}

const Terminal: React.FC<TerminalProps> = ({ onInput }) => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<XTerm | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm.js
    const xterm = new XTerm({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: '#1e1e1e',
        foreground: '#d4d4d4',
        cursor: '#d4d4d4',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5'
      },
      convertEol: true,
      rows: 24,
      cols: 80
    });

    // Add fit addon
    const fitAddon = new FitAddon();
    xterm.loadAddon(fitAddon);

    // Open terminal
    xterm.open(terminalRef.current);
    fitAddon.fit();

    // Store references
    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    // Handle input
    xterm.onData((data) => {
      if (onInput) {
        onInput(data);
      }
    });

    // Welcome message
    xterm.writeln('Terminal Output');
    xterm.writeln('--------------------------------');
    xterm.writeln('');

    // Handle resize
    const handleResize = () => {
      fitAddon.fit();
    };
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      xterm.dispose();
    };
  }, [onInput]);

  // Expose write method for external use
  useEffect(() => {
    if (xtermRef.current) {
      (window as any).terminal = {
        write: (data: string) => xtermRef.current?.write(data),
        writeln: (data: string) => xtermRef.current?.writeln(data),
        clear: () => xtermRef.current?.clear()
      };
    }
  }, []);

  return (
    <div className="terminal-container">
      <div className="terminal-header">
        <div className="terminal-title">Terminal</div>
        <div className="terminal-controls">
          <button
            className="terminal-control-btn"
            onClick={() => xtermRef.current?.clear()}
            title="Clear terminal"
          >
            Clear
          </button>
        </div>
      </div>
      <div ref={terminalRef} className="terminal" />
    </div>
  );
};

export default Terminal;
