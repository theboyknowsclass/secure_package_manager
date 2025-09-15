import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Box, Container } from "@mui/material";
import { useAuth } from "./hooks/useAuth";
import Navbar from "./components/Navbar";
import ConfigurationStatus from "./components/ConfigurationStatus";
import Login from "./pages/Login";
import OAuthCallback from "./pages/OAuthCallback";
import Dashboard from "./pages/Dashboard";
import PackageUpload from "./pages/PackageUpload";
import RequestStatus from "./pages/RequestStatus";
import ApprovalDashboard from "./pages/ApprovalDashboard";
import Settings from "./pages/Settings";
import ConfigurationRequired from "./pages/ConfigurationRequired";
import ProtectedRoute from "./components/ProtectedRoute";

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        Loading...
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", minHeight: "100vh" }}>
      {user && <Navbar />}
      {user && <ConfigurationStatus />}
      <Container component="main" sx={{ mt: 4, mb: 4, flex: 1 }}>
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/" /> : <Login />}
          />
          <Route
            path="/oauth/callback"
            element={<OAuthCallback />}
          />
          <Route
            path="/configuration-required"
            element={
              <ProtectedRoute>
                <ConfigurationRequired />
              </ProtectedRoute>
            }
          />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/request"
            element={
              <ProtectedRoute>
                <PackageUpload />
              </ProtectedRoute>
            }
          />
          <Route
            path="/status"
            element={
              <ProtectedRoute>
                <RequestStatus />
              </ProtectedRoute>
            }
          />
          <Route
            path="/approve"
            element={
              <ProtectedRoute>
                <ApprovalDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute requireAdmin>
                <Settings />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Container>
    </Box>
  );
}

export default App;
