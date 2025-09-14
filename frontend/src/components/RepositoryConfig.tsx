import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  CardHeader,
  Grid,
  Alert,
  Snackbar,
  CircularProgress,
  Divider,
} from "@mui/material";
import { Save, Refresh } from "@mui/icons-material";
import { api } from "../services/api";

interface RepositoryConfig {
  id: number;
  config_key: string;
  config_value: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export default function RepositoryConfigComponent() {
  const [configs, setConfigs] = useState<RepositoryConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  // Load repository configuration
  const loadConfigs = async () => {
    try {
      setLoading(true);
      const response = await api.get("/admin/repository-config");
      // Filter to only show source and target URLs
      const filteredConfigs = response.data.configs.filter((config: any) => 
        config.config_key === 'source_repository_url' || 
        config.config_key === 'target_repository_url'
      );
      setConfigs(filteredConfigs);
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to load repository configuration");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConfigs();
  }, []);

  // Handle configuration value change
  const handleConfigChange = (configKey: string, value: string) => {
    setConfigs(prevConfigs =>
      prevConfigs.map(config =>
        config.config_key === configKey
          ? { ...config, config_value: value }
          : config
      )
    );
  };

  // Save configuration
  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      
      await api.put("/admin/repository-config", {
        configs: configs.map(config => ({
          config_key: config.config_key,
          config_value: config.config_value,
          description: config.description
        }))
      });
      
      setSuccess("Repository configuration saved successfully");
      await loadConfigs(); // Reload to get updated timestamps
    } catch (err: any) {
      setError(err.response?.data?.error || "Failed to save repository configuration");
    } finally {
      setSaving(false);
    }
  };

  // Reset to original values
  const handleReset = () => {
    loadConfigs();
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h5" component="h2">
          Repository Configuration
        </Typography>
        <Box>
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={handleReset}
            disabled={saving}
            sx={{ mr: 1 }}
          >
            Reset
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? <CircularProgress size={20} /> : "Save Configuration"}
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {configs.map((config) => (
          <Grid item xs={12} md={6} key={config.config_key}>
            <Card>
              <CardHeader
                title={config.config_key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                subheader={config.description}
              />
              <CardContent>
                <TextField
                  fullWidth
                  variant="outlined"
                  value={config.config_value}
                  onChange={(e) => handleConfigChange(config.config_key, e.target.value)}
                  disabled={saving}
                  multiline={config.config_value.length > 50}
                  rows={config.config_value.length > 50 ? 3 : 1}
                />
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Snackbar
        open={!!error}
        autoHideDuration={6000}
        onClose={() => setError("")}
      >
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!success}
        autoHideDuration={4000}
        onClose={() => setSuccess("")}
      >
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      </Snackbar>
    </Box>
  );
}
