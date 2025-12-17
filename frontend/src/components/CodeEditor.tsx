import React, { useRef } from 'react';
import Editor from '@monaco-editor/react';
import type { editor } from 'monaco-editor';

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
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  };

  // Detect language from file extension or content
  const detectLanguage = (content: string): string => {
    // Simple language detection based on content
    if (content.includes('import React') || content.includes('jsx')) {
      return 'typescript';
    }
    if (content.includes('def ') || content.includes('import ')) {
      return 'python';
    }
    if (content.includes('const ') || content.includes('let ') || content.includes('var ')) {
      return 'javascript';
    }
    return language;
  };

  const detectedLanguage = detectLanguage(value);

  return (
    <div className="code-editor">
      <div className="editor-header">
        <div className="editor-title">Code Viewer</div>
        <div className="editor-language">{detectedLanguage}</div>
      </div>
      <Editor
        height="100%"
        defaultLanguage={detectedLanguage}
        language={detectedLanguage}
        value={value}
        onChange={onChange}
        theme="vs-dark"
        options={{
          readOnly,
          minimap: { enabled: true },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          automaticLayout: true,
          tabSize: 2,
          wordWrap: 'on',
          folding: true,
          glyphMargin: true,
          lineDecorationsWidth: 10,
          lineNumbersMinChars: 3,
          renderLineHighlight: 'all',
          scrollbar: {
            vertical: 'visible',
            horizontal: 'visible',
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10
          }
        }}
        onMount={handleEditorDidMount}
      />
    </div>
  );
};

export default CodeEditor;
