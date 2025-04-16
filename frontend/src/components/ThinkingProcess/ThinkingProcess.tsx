import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Card,
  CardContent,
  Chip,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText,
  Link
} from '@mui/material';
import {
  Psychology,
  ExpandMore,
  ExpandLess,
  CheckCircle,
  Error,
  Info
} from '@mui/icons-material';
import { ThinkingProcessStep } from '../../types';

interface ThinkingProcessProps {
  steps: ThinkingProcessStep[];
}

const ThinkingProcess: React.FC<ThinkingProcessProps> = ({ steps }) => {
  const [expandedSteps, setExpandedSteps] = useState<string[]>([]);
  const [expandedAlternatives, setExpandedAlternatives] = useState<string[]>([]);
  const [expandedReferences, setExpandedReferences] = useState<string[]>([]);
  const [processedSteps, setProcessedSteps] = useState<ThinkingProcessStep[]>(steps || []);

  // Update processed steps when steps prop changes
  useEffect(() => {
    console.log('ThinkingProcess: steps updated', steps?.length || 0);
    setProcessedSteps(steps || []);
  }, [steps]);

  const toggleAlternativesExpand = (id: string) => {
    if (expandedAlternatives.includes(id)) {
      setExpandedAlternatives(expandedAlternatives.filter(stepId => stepId !== id));
    } else {
      setExpandedAlternatives([...expandedAlternatives, id]);
    }
  };

  const toggleReferencesExpand = (id: string) => {
    if (expandedReferences.includes(id)) {
      setExpandedReferences(expandedReferences.filter(stepId => stepId !== id));
    } else {
      setExpandedReferences([...expandedReferences, id]);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'success';
    if (confidence >= 0.5) return 'warning';
    return 'error';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return <CheckCircle fontSize="small" />;
    if (confidence >= 0.5) return <Info fontSize="small" />;
    return <Error fontSize="small" />;
  };

  return (
    <Paper elevation={3} sx={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center' }}>
          <Psychology sx={{ mr: 1 }} />
          Thinking Process
        </Typography>
      </Box>

      <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2 }}>
        {processedSteps.length === 0 ? (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No thinking process data available
            </Typography>
          </Box>
        ) : (
          <Stepper orientation="vertical" nonLinear>
            {processedSteps.map((step) => (
              <Step key={step.id} active={true} completed={true}>
                <StepLabel
                  optional={
                    <Chip
                      label={`Confidence: ${(step.confidence * 100).toFixed(0)}%`}
                      size="small"
                      color={getConfidenceColor(step.confidence)}
                      icon={getConfidenceIcon(step.confidence)}
                      variant="outlined"
                    />
                  }
                >
                  <Typography variant="subtitle1">{step.description}</Typography>
                </StepLabel>
                <StepContent>
                  <Card variant="outlined" sx={{ mb: 2 }}>
                    <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                      <Typography variant="body2" component="div" sx={{ whiteSpace: 'pre-wrap' }}>
                        {step.reasoning}
                      </Typography>

                      {step.alternatives && step.alternatives.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              cursor: 'pointer'
                            }}
                            onClick={() => toggleAlternativesExpand(step.id)}
                          >
                            <IconButton size="small" sx={{ p: 0.5, mr: 1 }}>
                              {expandedAlternatives.includes(step.id) ? <ExpandLess /> : <ExpandMore />}
                            </IconButton>
                            <Typography variant="subtitle2" color="text.secondary">
                              Alternative Considerations
                            </Typography>
                          </Box>
                          <Collapse in={expandedAlternatives.includes(step.id)}>
                            <List dense disablePadding sx={{ pl: 4, mt: 1 }}>
                              {step.alternatives.map((alternative, index) => (
                                <ListItem key={index} disablePadding sx={{ py: 0.5 }}>
                                  <ListItemText
                                    primary={
                                      <Typography variant="body2">
                                        {alternative}
                                      </Typography>
                                    }
                                  />
                                </ListItem>
                              ))}
                            </List>
                          </Collapse>
                        </Box>
                      )}

                      {step.references && step.references.length > 0 && (
                        <Box sx={{ mt: 2 }}>
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              cursor: 'pointer'
                            }}
                            onClick={() => toggleReferencesExpand(step.id)}
                          >
                            <IconButton size="small" sx={{ p: 0.5, mr: 1 }}>
                              {expandedReferences.includes(step.id) ? <ExpandLess /> : <ExpandMore />}
                            </IconButton>
                            <Typography variant="subtitle2" color="text.secondary">
                              References
                            </Typography>
                          </Box>
                          <Collapse in={expandedReferences.includes(step.id)}>
                            <List dense disablePadding sx={{ pl: 4, mt: 1 }}>
                              {step.references.map((reference, index) => (
                                <ListItem key={index} disablePadding sx={{ py: 0.5 }}>
                                  <ListItemText
                                    primary={
                                      <Link href={reference} target="_blank" rel="noopener">
                                        {reference}
                                      </Link>
                                    }
                                  />
                                </ListItem>
                              ))}
                            </List>
                          </Collapse>
                        </Box>
                      )}
                    </CardContent>
                  </Card>
                </StepContent>
              </Step>
            ))}
          </Stepper>
        )}
      </Box>
    </Paper>
  );
};

export default ThinkingProcess;
