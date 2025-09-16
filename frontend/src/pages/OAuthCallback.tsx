import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Container,
} from "@mui/material";
import { oauthService } from "../services/oauth";

export default function OAuthCallback() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const isProcessingRef = useRef(false);

  useEffect(() => {
    console.log("OAuthCallback page mounted, URL:", window.location.href);
    console.log("URL params:", new URLSearchParams(window.location.search));

    // Prevent duplicate processing
    if (isProcessingRef.current) {
      console.log("OAuthCallback: Already processing, skipping...");
      return;
    }

    isProcessingRef.current = true;
    handleOAuthCallback();
  }, []);

  const handleOAuthCallback = async () => {
    try {
      console.log("OAuthCallback page: Processing OAuth callback...");

      // Check if user is already authenticated
      if (oauthService.isAuthenticated()) {
        console.log(
          "OAuthCallback page: User already authenticated, redirecting to dashboard..."
        );
        navigate("/");
        return;
      }

      const result = await oauthService.handleCallback();
      console.log("OAuthCallback page: OAuth callback result:", result);

      if (result.success) {
        console.log(
          "OAuthCallback page: OAuth callback successful, redirecting to dashboard..."
        );
        // Redirect to dashboard after successful authentication
        navigate("/");
      } else {
        console.error(
          "OAuthCallback page: OAuth callback failed:",
          result.error
        );
        setError(result.error || "OAuth callback failed");
        // Redirect to login page on failure
        setTimeout(() => {
          navigate("/login");
        }, 3000);
      }
    } catch (err) {
      console.error("OAuthCallback page: OAuth callback error:", err);
      setError("OAuth callback failed. Please try again.");
      // Redirect to login page on error
      setTimeout(() => {
        navigate("/login");
      }, 3000);
    } finally {
      setLoading(false);
      // Reset processing state
      isProcessingRef.current = false;
    }
  };

  return (
    <Container component="main" maxWidth="sm">
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
              gap: 2,
            }}
          >
            {loading ? (
              <>
                <CircularProgress size={60} />
                <Typography variant="h5" component="h1" gutterBottom>
                  Authenticating...
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  textAlign="center"
                >
                  Please wait while we complete your authentication.
                </Typography>
              </>
            ) : error ? (
              <>
                <Typography
                  variant="h5"
                  component="h1"
                  gutterBottom
                  color="error"
                >
                  Authentication Failed
                </Typography>
                <Alert severity="error" sx={{ width: "100%" }}>
                  {error}
                </Alert>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  textAlign="center"
                >
                  Redirecting to login page...
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h5" component="h1" gutterBottom>
                  Authentication Successful
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  textAlign="center"
                >
                  Redirecting to dashboard...
                </Typography>
              </>
            )}
          </Box>
        </Paper>
      </Box>
    </Container>
  );
}
