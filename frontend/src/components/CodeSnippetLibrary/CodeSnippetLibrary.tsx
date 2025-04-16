import React, { useState, useEffect } from 'react';
import { 
  Box, 
  Paper, 
  Typography, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemSecondaryAction, 
  IconButton, 
  TextField, 
  InputAdornment,
  Divider,
  Tooltip,
  Chip,
  Collapse,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent
} from '@mui/material';
import { 
  Search, 
  ContentCopy, 
  Code,
  ExpandMore, 
  ExpandLess,
  Add,
  Edit,
  Delete,
  Save
} from '@mui/icons-material';
import Editor from '@monaco-editor/react';
import { CodeSnippet } from '../../types';

interface CodeSnippetLibraryProps {
  conversationId: string;
  snippets?: CodeSnippet[];
  onSaveSnippet?: (snippet: CodeSnippet) => void;
  onDeleteSnippet?: (snippetId: string) => void;
}

const CodeSnippetLibrary: React.FC<CodeSnippetLibraryProps> = ({ 
  conversationId, 
  snippets = [], 
  onSaveSnippet,
  onDeleteSnippet
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [filteredSnippets, setFilteredSnippets] = useState<CodeSnippet[]>(snippets);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSnippet, setEditingSnippet] = useState<CodeSnippet | null>(null);
  
  // Form state
  const [title, setTitle] = useState('');
  const [language, setLanguage] = useState('javascript');
  const [code, setCode] = useState('');
  const [tags, setTags] = useState('');

  // Update filtered snippets when snippets or search term changes
  useEffect(() => {
    if (searchTerm) {
      const lowercaseSearch = searchTerm.toLowerCase();
      setFilteredSnippets(
        snippets.filter(
          snippet => 
            snippet.title.toLowerCase().includes(lowercaseSearch) || 
            snippet.tags.some(tag => tag.toLowerCase().includes(lowercaseSearch)) ||
            snippet.code.toLowerCase().includes(lowercaseSearch)
        )
      );
    } else {
      setFilteredSnippets(snippets);
    }
  }, [snippets, searchTerm]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  const toggleExpand = (id: string) => {
    if (expandedItems.includes(id)) {
      setExpandedItems(expandedItems.filter(itemId => itemId !== id));
    } else {
      setExpandedItems([...expandedItems, id]);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const handleOpenDialog = (snippet?: CodeSnippet) => {
    if (snippet) {
      setEditingSnippet(snippet);
      setTitle(snippet.title);
      setLanguage(snippet.language);
      setCode(snippet.code);
      setTags(snippet.tags.join(', '));
    } else {
      setEditingSnippet(null);
      setTitle('');
      setLanguage('javascript');
      setCode('');
      setTags('');
    }
    setDialogOpen(true);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
  };

  const handleLanguageChange = (event: SelectChangeEvent) => {
    setLanguage(event.target.value);
  };

  const handleSaveSnippet = () => {
    const tagArray = tags.split(',').map(tag => tag.trim()).filter(tag => tag);
    
    const snippet: CodeSnippet = {
      id: editingSnippet?.id || Date.now().toString(),
      title,
      language,
      code,
      tags: tagArray,
      created_at: editingSnippet?.created_at || Date.now(),
      updated_at: Date.now(),
      conversation_id: conversationId
    };
    
    if (onSaveSnippet) {
      onSaveSnippet(snippet);
    }
    
    handleCloseDialog();
  };

  const handleDeleteSnippet = (id: string) => {
    if (onDeleteSnippet) {
      onDeleteSnippet(id);
    }
  };

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString();
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
            <Code sx={{ mr: 1 }} />
            Code Snippet Library
          </Typography>
          <Button 
            variant="contained" 
            startIcon={<Add />} 
            size="small"
            onClick={() => handleOpenDialog()}
          >
            New Snippet
          </Button>
        </Box>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Search snippets..."
          value={searchTerm}
          onChange={handleSearchChange}
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
      </Box>
      
      <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
        {filteredSnippets.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No code snippets found
            </Typography>
            <Button 
              variant="outlined" 
              startIcon={<Add />} 
              sx={{ mt: 2 }}
              onClick={() => handleOpenDialog()}
            >
              Create your first snippet
            </Button>
          </Box>
        ) : (
          <List disablePadding>
            {filteredSnippets.map((snippet, index) => (
              <React.Fragment key={snippet.id}>
                {index > 0 && <Divider />}
                <ListItem alignItems="flex-start">
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 0.5 }}>
                        <Typography
                          variant="subtitle1"
                          sx={{
                            fontWeight: 'medium',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            mr: 1,
                            flex: 1,
                          }}
                        >
                          {snippet.title}
                        </Typography>
                        <Chip 
                          label={snippet.language} 
                          size="small" 
                          color="primary"
                          variant="outlined"
                          sx={{ ml: 1 }}
                        />
                      </Box>
                    }
                    secondary={
                      <Box>
                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 0.5 }}>
                          {snippet.tags.map(tag => (
                            <Chip 
                              key={tag} 
                              label={tag} 
                              size="small" 
                              variant="outlined"
                              sx={{ mr: 0.5 }}
                            />
                          ))}
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          Updated: {formatDate(snippet.updated_at)}
                        </Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                          <IconButton 
                            size="small" 
                            onClick={() => toggleExpand(snippet.id)}
                            sx={{ mr: 1, p: 0.5 }}
                          >
                            {expandedItems.includes(snippet.id) ? <ExpandLess /> : <ExpandMore />}
                          </IconButton>
                          <Typography variant="caption" color="text.secondary">
                            {expandedItems.includes(snippet.id) ? 'Hide code' : 'Show code'}
                          </Typography>
                        </Box>
                        <Collapse in={expandedItems.includes(snippet.id)}>
                          <Box sx={{ mt: 1, mb: 1, border: 1, borderColor: 'divider', borderRadius: 1, height: 200 }}>
                            <Editor
                              height="200px"
                              language={snippet.language}
                              value={snippet.code}
                              theme="vs-dark"
                              options={{
                                readOnly: true,
                                minimap: { enabled: false },
                                scrollBeyondLastLine: false,
                                fontSize: 14,
                                wordWrap: 'on',
                              }}
                            />
                          </Box>
                        </Collapse>
                      </Box>
                    }
                  />
                  <ListItemSecondaryAction>
                    <Tooltip title="Copy code">
                      <IconButton edge="end" onClick={() => copyToClipboard(snippet.code)}>
                        <ContentCopy />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Edit snippet">
                      <IconButton edge="end" onClick={() => handleOpenDialog(snippet)}>
                        <Edit />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="Delete snippet">
                      <IconButton edge="end" onClick={() => handleDeleteSnippet(snippet.id)}>
                        <Delete />
                      </IconButton>
                    </Tooltip>
                  </ListItemSecondaryAction>
                </ListItem>
              </React.Fragment>
            ))}
          </List>
        )}
      </Box>

      {/* Add/Edit Snippet Dialog */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingSnippet ? 'Edit Snippet' : 'Add New Snippet'}
        </DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Title"
            fullWidth
            variant="outlined"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth variant="outlined" sx={{ mb: 2 }}>
            <InputLabel id="language-select-label">Language</InputLabel>
            <Select
              labelId="language-select-label"
              value={language}
              onChange={handleLanguageChange}
              label="Language"
            >
              <MenuItem value="javascript">JavaScript</MenuItem>
              <MenuItem value="typescript">TypeScript</MenuItem>
              <MenuItem value="python">Python</MenuItem>
              <MenuItem value="java">Java</MenuItem>
              <MenuItem value="csharp">C#</MenuItem>
              <MenuItem value="cpp">C++</MenuItem>
              <MenuItem value="go">Go</MenuItem>
              <MenuItem value="rust">Rust</MenuItem>
              <MenuItem value="html">HTML</MenuItem>
              <MenuItem value="css">CSS</MenuItem>
              <MenuItem value="json">JSON</MenuItem>
              <MenuItem value="markdown">Markdown</MenuItem>
              <MenuItem value="sql">SQL</MenuItem>
              <MenuItem value="shell">Shell</MenuItem>
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            label="Tags (comma separated)"
            fullWidth
            variant="outlined"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            sx={{ mb: 2 }}
          />
          <Typography variant="subtitle2" gutterBottom>
            Code
          </Typography>
          <Box sx={{ height: 300, border: 1, borderColor: 'divider', borderRadius: 1 }}>
            <Editor
              height="300px"
              language={language}
              value={code}
              onChange={(value) => setCode(value || '')}
              theme="vs-dark"
              options={{
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                fontSize: 14,
                wordWrap: 'on',
              }}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button 
            onClick={handleSaveSnippet} 
            variant="contained" 
            startIcon={<Save />}
            disabled={!title || !code}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

export default CodeSnippetLibrary;
