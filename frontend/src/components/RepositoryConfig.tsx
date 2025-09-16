import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Info as InfoIcon,
  Security as SecurityIcon,
  Storage as StorageIcon,
  Settings as SettingsIcon,
  BugReport as BugReportIcon,
} from '@mui/icons-material';
import { api, endpoints } from '../services/api';

interface ConfigData {
  repository: {
    source_repository_url: string;
    target_repository_url: string;
  };
  services: {
    api_url: string;
    frontend_url: string;
    database_url: string;
    idp_url: string;
    trivy_url: string;
  };
  security: {
    jwt_secret_configured: boolean;
    flask_secret_configured: boolean;
    oauth_audience: string;
    oauth_issuer: string;
  };
  trivy: {
    timeout: string;
    max_retries: string;
  };
  environment: {
    flask_env: string;
    flask_debug: string;
    max_content_length: string;
  };
}

interface ConfigStatus {
  is_complete: boolean;
  missing_keys: string[];
  requires_admin_setup: boolean;
  note: string;
}

export default function RepositoryConfig() {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [configStatus, setConfigStatus] = useState<ConfigStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchConfig = async () => {
      try {
        setLoading(true);
        const response = await api.get(endpoints.admin.config);
        
        setConfig(response.data.config);
        setConfigStatus(response.data.status);
        setError(null);
      } catch (err: any) {
        setError(err.response?.data?.error || 'Failed to load configuration');
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, []);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="200px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!config || !configStatus) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        No configuration data available
      </Alert>
    );
  }

  const getStatusChip = (isConfigured: boolean) => (
    <Chip
      icon={isConfigured ? <CheckCircleIcon /> : <ErrorIcon />}
      label={isConfigured ? 'Configured' : 'Not Configured'}
      color={isConfigured ? 'success' : 'error'}
      size="small"
    />
  );

  const formatBytes = (bytes: string) => {
    const size = parseInt(bytes);
    if (size >= 1024 * 1024) {
      return `${(size / (1024 * 1024)).toFixed(1)} MB`;
    } else if (size >= 1024) {
      return `${(size / 1024).toFixed(1)} KB`;
    }
    return `${size} bytes`;
  };

  return (
    <Box>
      {/* Configuration Status Alert */}
      <Alert 
        severity={configStatus.is_complete ? 'success' : 'warning'} 
        sx={{ mb: 3 }}
        icon={configStatus.is_complete ? <CheckCircleIcon /> : <ErrorIcon />}
      >
        <Typography variant="h6" gutterBottom>
          Configuration Status
        </Typography>
        <Typography variant="body2">
          {configStatus.is_complete 
            ? 'All required configuration is complete and the system is ready to use.'
            : 'Some configuration is missing. Please check the missing keys below.'
          }
        </Typography>
        {configStatus.missing_keys.length > 0 && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2" fontWeight="bold">
              Missing Configuration:
            </Typography>
            {configStatus.missing_keys.map((key) => (
              <Chip key={key} label={key} size="small" sx={{ mr: 1, mt: 0.5 }} />
            ))}
          </Box>
        )}
        <Typography variant="caption" display="block" sx={{ mt: 1, fontStyle: 'italic' }}>
          {configStatus.note}
        </Typography>
      </Alert>

      {/* Configuration Details */}
      <Grid container spacing={3}>
        {/* Repository Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <StorageIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Repository Configuration</Typography>
              </Box>
              
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="Source Repository URL"
                    secondary={config.repository.source_repository_url}
                  />
                  {getStatusChip(config.repository.source_repository_url !== 'Not configured')}
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Target Repository URL"
                    secondary={config.repository.target_repository_url}
                  />
                  {getStatusChip(config.repository.target_repository_url !== 'Not configured')}
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Services Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SettingsIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Services Configuration</Typography>
              </Box>
              
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="API URL"
                    secondary={config.services.api_url}
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Frontend URL"
                    secondary={config.services.frontend_url}
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Database URL"
                    secondary={config.services.database_url}
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Identity Provider URL"
                    secondary={config.services.idp_url}
                  />
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Trivy URL"
                    secondary={config.services.trivy_url}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Security Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <SecurityIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Security Configuration</Typography>
              </Box>
              
              <List dense>
                <ListItem>
                  <ListItemText
                    primary="JWT Secret"
                    secondary="Authentication token signing"
                  />
                  {getStatusChip(config.security.jwt_secret_configured)}
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="Flask Secret Key"
                    secondary="Session encryption"
                  />
                  {getStatusChip(config.security.flask_secret_configured)}
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="OAuth Audience"
                    secondary={config.security.oauth_audience}
                  />
                  {getStatusChip(config.security.oauth_audience !== 'Not configured')}
                </ListItem>
                
                <ListItem>
                  <ListItemText
                    primary="OAuth Issuer"
                    secondary={config.security.oauth_issuer}
                  />
                  {getStatusChip(config.security.oauth_issuer !== 'Not configured')}
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Advanced Configuration */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <BugReportIcon color="primary" sx={{ mr: 1 }} />
                <Typography variant="h6">Advanced Configuration</Typography>
              </Box>
              
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle1">Trivy Security Scanner</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    <ListItem>
                      <ListItemText
                        primary="Timeout"
                        secondary={`${config.trivy.timeout} seconds`}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Max Retries"
                        secondary={config.trivy.max_retries}
                      />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>
              
              <Accordion>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Typography variant="subtitle1">Environment Settings</Typography>
                </AccordionSummary>
                <AccordionDetails>
                  <List dense>
                    <ListItem>
                      <ListItemText
                        primary="Flask Environment"
                        secondary={config.environment.flask_env}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Debug Mode"
                        secondary={config.environment.flask_debug === '1' ? 'Enabled' : 'Disabled'}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Max Content Length"
                        secondary={formatBytes(config.environment.max_content_length)}
                      />
                    </ListItem>
                  </List>
                </AccordionDetails>
              </Accordion>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Information Alert */}
      <Alert severity="info" sx={{ mt: 3 }} icon={<InfoIcon />}>
        <Typography variant="body2">
          <strong>Note:</strong> Configuration is managed via environment variables. 
          To modify these settings, update the environment variables in your deployment configuration 
          and restart the services.
        </Typography>
      </Alert>
    </Box>
  );
}
