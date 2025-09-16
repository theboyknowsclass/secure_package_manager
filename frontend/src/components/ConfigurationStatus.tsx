import React, { useState, useEffect, useCallback } from "react";
import {
  Box,
  Alert,
  Button,
  Typography,
  Card,
  CardContent,
  CardActions,
  CircularProgress,
  Chip,
} from "@mui/material";
import { Settings, Warning } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { api } from "../services/api";

interface ConfigStatus {
  is_complete: boolean;
  missing_keys: string[];
  requires_admin_setup: boolean;
}

export default function ConfigurationStatus() {
  const [configStatus, setConfigStatus] = useState<ConfigStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { user } = useAuth();

  const checkConfigurationStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const response = await api.get("/api/admin/config");
      setConfigStatus(response.data.status);

      // If user is admin and configuration is incomplete, redirect to settings
      if (user?.role === "admin" && !response.data.status.is_complete) {
        navigate("/settings");
        return;
      }
    } catch (err: unknown) {
      // If we can't check config status, assume it's incomplete for admin users
      if (user?.role === "admin") {
        setConfigStatus({
          is_complete: false,
          missing_keys: ["source_repository_url", "target_repository_url"],
          requires_admin_setup: true,
        });
        // Redirect admin to settings if we can't check status
        navigate("/settings");
        return;
      }
      const errorData = (err as { response?: { data?: { error?: string } } })
        ?.response?.data;
      setError(errorData?.error || "Failed to check configuration status");
    } finally {
      setLoading(false);
    }
  }, [user, navigate]);

  useEffect(() => {
    checkConfigurationStatus();
  }, [checkConfigurationStatus]);

  const handleConfigureClick = () => {
    navigate("/settings");
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={3}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!configStatus) {
    return null;
  }

  // If configuration is complete, don't show anything
  if (configStatus.is_complete) {
    return null;
  }

  // If user is admin, show configuration prompt
  if (user?.role === "admin") {
    return (
      <Card sx={{ m: 2, border: "2px solid", borderColor: "warning.main" }}>
        <CardContent>
          <Box display="flex" alignItems="center" mb={2}>
            <Warning color="warning" sx={{ mr: 1 }} />
            <Typography variant="h6" color="warning.main">
              Repository Configuration Required
            </Typography>
          </Box>
          <Typography variant="body1" paragraph>
            The package manager requires repository configuration before it can
            process packages. Please configure the following settings:
          </Typography>
          <Box display="flex" flexWrap="wrap" gap={1} mb={2}>
            {configStatus.missing_keys.map(key => (
              <Chip
                key={key}
                label={key
                  .replace(/_/g, " ")
                  .replace(/\b\w/g, l => l.toUpperCase())}
                color="warning"
                variant="outlined"
              />
            ))}
          </Box>
          <Typography variant="body2" color="text.secondary">
            Without proper configuration, package validation and publishing will
            not work correctly.
          </Typography>
        </CardContent>
        <CardActions>
          <Button
            variant="contained"
            startIcon={<Settings />}
            onClick={handleConfigureClick}
            color="warning"
          >
            Configure Now
          </Button>
        </CardActions>
      </Card>
    );
  }

  // If user is not admin and configuration is incomplete, redirect to configuration required page
  if (
    user &&
    (user.role === "user" || user.role === "approver") &&
    !configStatus.is_complete
  ) {
    navigate("/configuration-required");
    return null;
  }

  // This should not be reached for non-admin users, but just in case
  return null;
}
