import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.tsx";
import { Box, CircularProgress, Typography } from "@mui/material";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({
  children,
  requireAdmin = false,
}: ProtectedRouteProps) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="50vh"
      >
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Loading...
        </Typography>
      </Box>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requireAdmin && !user.is_admin) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        minHeight="50vh"
      >
        <Typography variant="h4" color="error" gutterBottom>
          Access Denied
        </Typography>
        <Typography variant="h6" color="textSecondary">
          Admin privileges required to access this page.
        </Typography>
      </Box>
    );
  }

  return <>{children}</>;
}
