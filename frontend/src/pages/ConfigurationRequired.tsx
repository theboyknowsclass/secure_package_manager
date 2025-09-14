import React from "react";
import {
  Box,
  Container,
  Paper,
  Typography,
  Button,
  Alert,
  Card,
  CardContent,
} from "@mui/material";
import { Settings, Logout } from "@mui/icons-material";
import { useAuth } from "../hooks/useAuth";

export default function ConfigurationRequired() {
  const { logout } = useAuth();

  return (
    <Container component="main" maxWidth="md">
      <Box
        sx={{
          marginTop: 8,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <Paper elevation={3} sx={{ padding: 4, width: "100%" }}>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 3,
            }}
          >
            <Settings
              sx={{
                fontSize: 80,
                color: "warning.main",
                mb: 2,
              }}
            />

            <Typography variant="h4" component="h1" gutterBottom align="center">
              Service Configuration Required
            </Typography>

            <Alert severity="warning" sx={{ width: "100%", mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                The secure package manager service is not yet configured.
              </Typography>
              <Typography variant="body1">
                Please contact your system administrator to complete the initial setup
                before you can use this service.
              </Typography>
            </Alert>

            <Card sx={{ width: "100%", mb: 3 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  What needs to be configured?
                </Typography>
                <Typography variant="body2" color="text.secondary" component="div">
                  <ul>
                    <li>Repository configuration (source and target repositories)</li>
                    <li>License management settings</li>
                    <li>Security policies and validation rules</li>
                    <li>User permissions and access controls</li>
                  </ul>
                </Typography>
              </CardContent>
            </Card>

            <Typography variant="body1" color="text.secondary" align="center" sx={{ mb: 3 }}>
              Once the administrator completes the configuration, you will be able to:
            </Typography>

            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: 2,
                width: "100%",
                mb: 4,
              }}
            >
              <Card variant="outlined">
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="h6" gutterBottom>
                    Upload Packages
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Submit packages for validation and approval
                  </Typography>
                </CardContent>
              </Card>

              <Card variant="outlined">
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="h6" gutterBottom>
                    Track Requests
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Monitor the status of your package requests
                  </Typography>
                </CardContent>
              </Card>

              <Card variant="outlined">
                <CardContent sx={{ textAlign: "center" }}>
                  <Typography variant="h6" gutterBottom>
                    View Approvals
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    See approved packages and their details
                  </Typography>
                </CardContent>
              </Card>
            </Box>

            <Box sx={{ display: "flex", gap: 2, justifyContent: "center" }}>
              <Button
                variant="contained"
                color="primary"
                startIcon={<Logout />}
                onClick={logout}
                size="large"
              >
                Logout
              </Button>
            </Box>

            <Typography variant="caption" color="text.secondary" align="center" sx={{ mt: 2 }}>
              If you believe this is an error, please contact your system administrator.
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
