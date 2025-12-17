import React from 'react';

interface CodeEditorProps {
  value?: string;
  onChange?: (value: string | undefined) => void;
  language?: string;
  readOnly?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({
  value = '',
  onChange,
  language = 'typescript',
  readOnly = false
}) => {
  return (
    <div className="code-editor">
      <div className="editor-header">
        <div className="editor-title">Code Viewer</div>
        <div className="editor-language">{language}</div>
      </div>
      <textarea
        className="code-textarea"
        value={value}
        onChange={(e) => onChange?.(e.target.value)}
        readOnly={readOnly}
        spellCheck={false}
      />
    </div>
  );
};

export default CodeEditor;
