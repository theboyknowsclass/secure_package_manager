import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  TextField,
  Button,
  Card,
  CardContent,
  Alert,
  CircularProgress,
} from "@mui/material";
import { Save, CheckCircle } from "@mui/icons-material";
import { api } from "../services/api";

interface RepositoryConfig {
  source_repository_url: string;
  target_repository_url: string;
}

export default function RepositoryConfiguration() {
  const [config, setConfig] = useState<RepositoryConfig>({
    source_repository_url: "",
    target_repository_url: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    loadConfiguration();
  }, []);

  const loadConfiguration = async () => {
    try {
      setLoading(true);
      setError("");
      const response = await api.get("/api/admin/repository-config");
      const configs = response.data.configs || [];
      
      // Convert array of configs to object
      const configObj: RepositoryConfig = {
        source_repository_url: "",
        target_repository_url: "",
      };
      
      configs.forEach((config: any) => {
        if (config.config_key === "source_repository_url") {
          configObj.source_repository_url = config.config_value;
        } else if (config.config_key === "target_repository_url") {
          configObj.target_repository_url = config.config_value;
        }
      });
      
      setConfig(configObj);
    } catch (err: any) {
      console.error("Failed to load configuration:", err);
      setError("Failed to load repository configuration");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError("");
      setSuccess("");
      
      // Convert object to array format expected by backend
      const configs = [
        {
          config_key: "source_repository_url",
          config_value: config.source_repository_url,
          description: "Source repository URL for package downloads"
        },
        {
          config_key: "target_repository_url", 
          config_value: config.target_repository_url,
          description: "Target repository URL for package publishing"
        }
      ];
      
      await api.put("/api/admin/repository-config", { configs });
      setSuccess("Repository configuration saved successfully!");
    } catch (err: any) {
      console.error("Failed to save configuration:", err);
      setError(err.response?.data?.error || "Failed to save repository configuration");
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (field: keyof RepositoryConfig) => (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setConfig(prev => ({
      ...prev,
      [field]: event.target.value
    }));
  };

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="50vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert 
          severity="success" 
          sx={{ mb: 3 }}
          icon={<CheckCircle />}
        >
          {success}
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <TextField
              label="Source Repository URL"
              value={config.source_repository_url}
              onChange={handleInputChange("source_repository_url")}
              fullWidth
              required
              placeholder="https://registry.npmjs.org/"
              helperText="The source repository where packages are downloaded from (e.g., npm registry)"
            />

            <TextField
              label="Target Repository URL"
              value={config.target_repository_url}
              onChange={handleInputChange("target_repository_url")}
              fullWidth
              required
              placeholder="https://your-company-registry.com/"
              helperText="The target repository where validated packages will be published"
            />

            <Box sx={{ display: "flex", justifyContent: "flex-end", mt: 2 }}>
              <Button
                variant="contained"
                startIcon={saving ? <CircularProgress size={20} /> : <Save />}
                onClick={handleSave}
                disabled={saving || !config.source_repository_url || !config.target_repository_url}
                size="large"
              >
                {saving ? "Saving..." : "Save Configuration"}
              </Button>
            </Box>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
}
