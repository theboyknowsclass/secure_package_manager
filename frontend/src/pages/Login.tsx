import React, { useState } from "react";
import {
  Box,
  Paper,
  Button,
  Typography,
  Alert,
  Container,
  CircularProgress,
} from "@mui/material";
import { useAuth } from "../hooks/useAuth";

export default function Login() {
  const [error, setError] = useState("");
  const [loading] = useState(false);
  const { login } = useAuth();

  const handleLogin = () => {
    setError("");
    login();
  };

  if (loading) {
    return (
      <Container maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <CircularProgress />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Processing authentication...
          </Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="sm">
      <Box
        sx={{
          marginTop: 8,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <Paper
          elevation={3}
          sx={{
            padding: 4,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            width: "100%",
          }}
        >
          <Typography component="h1" variant="h4" gutterBottom>
            Secure Package Manager
          </Typography>
          <Typography
            component="h2"
            variant="h6"
            color="textSecondary"
            gutterBottom
          >
            Sign in with your enterprise account
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: "100%", mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box sx={{ mt: 1, width: "100%" }}>
            <Button
              fullWidth
              variant="contained"
              size="large"
              onClick={handleLogin}
              disabled={loading}
              sx={{ mt: 3, mb: 2, py: 1.5 }}
            >
              Sign In with Enterprise ID
            </Button>
          </Box>

          <Typography
            variant="body2"
            color="textSecondary"
            sx={{ mt: 2, textAlign: "center" }}
          >
            This will redirect you to your organization's identity provider for
            secure authentication.
          </Typography>
        </Paper>
      </Box>
    </Container>
  );
}
