import React, { useState, useEffect, useRef } from 'react';
import { Box, Paper, Typography, TextField, IconButton, Tabs, Tab, Tooltip } from '@mui/material';
import { Send, ContentCopy, Close, Add } from '@mui/icons-material';
import Editor from '@monaco-editor/react';
import { TerminalCommand } from '../../types';

interface TerminalEditorProps {
  conversationId: string;
  onExecuteCommand?: (command: string) => Promise<string>;
}

interface TabData {
  id: string;
  title: string;
  content: string;
  language: string;
}

const TerminalEditor: React.FC<TerminalEditorProps> = ({ conversationId, onExecuteCommand }) => {
  const [command, setCommand] = useState('');
  const [commandHistory, setCommandHistory] = useState<TerminalCommand[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const [tabs, setTabs] = useState<TabData[]>([
    { id: '1', title: 'Terminal', content: '', language: 'shell' },
  ]);
  const [activeTab, setActiveTab] = useState('1');
  const terminalRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom when command history updates
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [commandHistory]);

  const handleCommandChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setCommand(e.target.value);
  };

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim()) return;

    // Add command to history
    const newCommand: TerminalCommand = {
      id: Date.now().toString(),
      command: command.trim(),
      output: 'Executing...',
      timestamp: Date.now(),
      conversation_id: conversationId,
    };

    setCommandHistory([...commandHistory, newCommand]);
    setCommand('');
    setHistoryIndex(-1);

    // Execute command if handler provided
    if (onExecuteCommand) {
      try {
        const output = await onExecuteCommand(newCommand.command);
        
        // Update command with output
        setCommandHistory(prev => 
          prev.map(cmd => 
            cmd.id === newCommand.id ? { ...cmd, output } : cmd
          )
        );
      } catch (error) {
        // Update command with error
        setCommandHistory(prev => 
          prev.map(cmd => 
            cmd.id === newCommand.id ? { ...cmd, output: `Error: ${error}` } : cmd
          )
        );
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Handle up/down arrows for command history
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        const newIndex = historyIndex + 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[commandHistory.length - 1 - newIndex].command);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex > 0) {
        const newIndex = historyIndex - 1;
        setHistoryIndex(newIndex);
        setCommand(commandHistory[commandHistory.length - 1 - newIndex].command);
      } else if (historyIndex === 0) {
        setHistoryIndex(-1);
        setCommand('');
      }
    }
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setActiveTab(newValue);
  };

  const handleAddTab = () => {
    const newId = (tabs.length + 1).toString();
    setTabs([...tabs, { id: newId, title: `Code ${tabs.length}`, content: '', language: 'javascript' }]);
    setActiveTab(newId);
  };

  const handleCloseTab = (id: string) => {
    if (tabs.length === 1) return;
    const newTabs = tabs.filter(tab => tab.id !== id);
    setTabs(newTabs);
    if (activeTab === id) {
      setActiveTab(newTabs[0].id);
    }
  };

  const handleEditorChange = (value: string | undefined) => {
    if (value === undefined) return;
    setTabs(tabs.map(tab => 
      tab.id === activeTab ? { ...tab, content: value } : tab
    ));
  };

  const handleLanguageChange = (language: string) => {
    setTabs(tabs.map(tab => 
      tab.id === activeTab ? { ...tab, language } : tab
    ));
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const activeTabData = tabs.find(tab => tab.id === activeTab) || tabs[0];

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs 
          value={activeTab} 
          onChange={handleTabChange} 
          variant="scrollable"
          scrollButtons="auto"
        >
          {tabs.map(tab => (
            <Tab 
              key={tab.id} 
              label={
                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography variant="body2">{tab.title}</Typography>
                  {tabs.length > 1 && (
                    <IconButton 
                      size="small" 
                      onClick={(e) => { e.stopPropagation(); handleCloseTab(tab.id); }}
                      sx={{ ml: 1, p: 0.5 }}
                    >
                      <Close fontSize="small" />
                    </IconButton>
                  )}
                </Box>
              } 
              value={tab.id} 
            />
          ))}
          <Tab 
            icon={<Add />} 
            aria-label="add tab" 
            value="add" 
            onClick={handleAddTab}
            sx={{ minWidth: 40 }}
          />
        </Tabs>
      </Box>

      {activeTabData.id === '1' ? (
        // Terminal tab
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', p: 2, overflow: 'hidden' }}>
          <Box 
            ref={terminalRef}
            sx={{ 
              flexGrow: 1, 
              overflowY: 'auto', 
              fontFamily: 'monospace', 
              whiteSpace: 'pre-wrap', 
              p: 1, 
              backgroundColor: 'background.paper',
              borderRadius: 1,
              mb: 2
            }}
          >
            {commandHistory.map((cmd) => (
              <Box key={cmd.id} sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                  <Typography 
                    component="span" 
                    sx={{ 
                      color: 'primary.main', 
                      fontWeight: 'bold', 
                      mr: 1 
                    }}
                  >
                    $
                  </Typography>
                  <Typography component="span">{cmd.command}</Typography>
                  <Tooltip title="Copy command">
                    <IconButton 
                      size="small" 
                      onClick={() => copyToClipboard(cmd.command)}
                      sx={{ ml: 1 }}
                    >
                      <ContentCopy fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </Box>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    pl: 3, 
                    color: cmd.output.includes('Error') ? 'error.main' : 'text.primary' 
                  }}
                >
                  {cmd.output}
                </Typography>
              </Box>
            ))}
          </Box>
          <Box component="form" onSubmit={handleCommandSubmit} sx={{ display: 'flex' }}>
            <TextField
              fullWidth
              variant="outlined"
              placeholder="Enter command..."
              value={command}
              onChange={handleCommandChange}
              onKeyDown={handleKeyDown}
              size="small"
              InputProps={{
                startAdornment: (
                  <Typography 
                    component="span" 
                    sx={{ 
                      color: 'primary.main', 
                      fontWeight: 'bold', 
                      mr: 1 
                    }}
                  >
                    $
                  </Typography>
                ),
              }}
              sx={{ mr: 1 }}
            />
            <IconButton type="submit" color="primary">
              <Send />
            </IconButton>
          </Box>
        </Box>
      ) : (
        // Code editor tab
        <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ p: 1, borderBottom: 1, borderColor: 'divider' }}>
            <Tabs 
              value={activeTabData.language} 
              onChange={(e, val) => handleLanguageChange(val)}
              variant="scrollable"
              scrollButtons="auto"
              sx={{ minHeight: 36 }}
            >
              <Tab label="JavaScript" value="javascript" sx={{ minHeight: 36, py: 0 }} />
              <Tab label="TypeScript" value="typescript" sx={{ minHeight: 36, py: 0 }} />
              <Tab label="Python" value="python" sx={{ minHeight: 36, py: 0 }} />
              <Tab label="HTML" value="html" sx={{ minHeight: 36, py: 0 }} />
              <Tab label="CSS" value="css" sx={{ minHeight: 36, py: 0 }} />
              <Tab label="JSON" value="json" sx={{ minHeight: 36, py: 0 }} />
            </Tabs>
          </Box>
          <Box sx={{ flexGrow: 1 }}>
            <Editor
              height="100%"
              language={activeTabData.language}
              value={activeTabData.content}
              onChange={handleEditorChange}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                wordWrap: 'on',
                automaticLayout: true,
                folding: true,
                lineNumbers: 'on',
                tabSize: 2,
              }}
            />
          </Box>
        </Box>
      )}
    </Paper>
  );
};

export default TerminalEditor;
