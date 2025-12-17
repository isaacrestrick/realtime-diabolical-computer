import React, { useEffect, useRef, useState } from 'react';

interface VoiceIndicatorProps {
  isActive?: boolean;
  onToggle?: () => void;
}

const VoiceIndicator: React.FC<VoiceIndicatorProps> = ({
  isActive = false,
  onToggle
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const [audioLevel, setAudioLevel] = useState(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const width = canvas.width;
      const height = canvas.height;

      // Clear canvas
      ctx.fillStyle = '#1e1e1e';
      ctx.fillRect(0, 0, width, height);

      if (isActive) {
        // Draw waveform
        const barCount = 32;
        const barWidth = width / barCount;
        const centerY = height / 2;

        for (let i = 0; i < barCount; i++) {
          // Simulate audio activity with random values when active
          const randomHeight = Math.random() * audioLevel * height * 0.4;
          const barHeight = Math.max(2, randomHeight);

          // Gradient from center
          const gradient = ctx.createLinearGradient(0, centerY - barHeight / 2, 0, centerY + barHeight / 2);
          gradient.addColorStop(0, '#4a9eff');
          gradient.addColorStop(1, '#0066cc');

          ctx.fillStyle = gradient;
          ctx.fillRect(
            i * barWidth + barWidth * 0.1,
            centerY - barHeight / 2,
            barWidth * 0.8,
            barHeight
          );
        }

        // Simulate audio activity
        setAudioLevel(0.3 + Math.random() * 0.7);
      } else {
        // Draw idle line
        ctx.strokeStyle = '#444';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(0, height / 2);
        ctx.lineTo(width, height / 2);
        ctx.stroke();
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isActive, audioLevel]);

  return (
    <div className="voice-indicator">
      <div className="voice-visualization">
        <canvas
          ref={canvasRef}
          width={600}
          height={80}
          className="waveform-canvas"
        />
      </div>
      <button
        className={`mic-button ${isActive ? 'active' : ''}`}
        onClick={onToggle}
        aria-label={isActive ? 'Stop listening' : 'Start listening'}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      </button>
      <div className="voice-status">
        {isActive ? 'Listening...' : 'Click to speak'}
      </div>
    </div>
  );
};

export default VoiceIndicator;
