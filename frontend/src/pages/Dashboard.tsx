import React from "react";
import { useQuery } from "react-query";
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Paper,
  CircularProgress,
  Alert,
} from "@mui/material";
import { useAuth } from "../hooks/useAuth";
import { api, endpoints } from "../services/api";
import { 
  PACKAGE_STATUS, 
  type PackageStatus,
  isPendingStatus,
  isCompletedStatus 
} from "../types/status";

interface PackageRequest {
  id: number;
  status: PackageStatus;
  total_packages: number;
  validated_packages: number;
  created_at: string;
  application: {
    name: string;
    version: string;
  };
}

export default function Dashboard() {
  const { user } = useAuth();

  const {
    data: requests,
    isLoading,
    error,
  } = useQuery<PackageRequest[]>("packageRequests", async () => {
    const response = await api.get(endpoints.packages.requests);
    return response.data.requests;
  });

  if (isLoading) {
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

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Failed to load package requests. Please try again.
      </Alert>
    );
  }

  const totalRequests = requests?.length || 0;
  const pendingRequests =
    requests?.filter(
      (r) => !isCompletedStatus(r.status)
    ).length || 0;
  const completedRequests =
    requests?.filter(
      (r) => isCompletedStatus(r.status)
    ).length || 0;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Dashboard
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Welcome back, {user?.full_name}! Here's an overview of your package
        requests.
      </Typography>

      {/* Statistics Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Total Requests
              </Typography>
              <Typography variant="h3" component="div">
                {totalRequests}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Pending Requests
              </Typography>
              <Typography variant="h3" component="div" color="warning.main">
                {pendingRequests}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} sm={4}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Completed Requests
              </Typography>
              <Typography variant="h3" component="div" color="success.main">
                {completedRequests}
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Requests */}
      <Typography variant="h5" gutterBottom sx={{ mt: 4 }}>
        Recent Package Requests
      </Typography>

      {requests && requests.length > 0 ? (
        <Grid container spacing={2}>
          {requests.slice(0, 6).map((request) => (
            <Grid item xs={12} md={6} key={request.id}>
              <Paper sx={{ p: 2 }}>
                <Box
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  mb={1}
                >
                  <Typography variant="h6">
                    {request.application.name} v{request.application.version}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      px: 1,
                      py: 0.5,
                      borderRadius: 1,
                      backgroundColor: getStatusColor(request.status),
                      color: "white",
                      textTransform: "capitalize",
                    }}
                  >
                    {request.status}
                  </Typography>
                </Box>

                <Typography variant="body2" color="textSecondary" gutterBottom>
                  ID: {request.id}
                </Typography>

                <Typography variant="body2" color="textSecondary">
                  Packages: {request.validated_packages}/
                  {request.total_packages} validated
                </Typography>

                <Typography variant="body2" color="textSecondary">
                  Created: {new Date(request.created_at).toLocaleDateString()}
                </Typography>
              </Paper>
            </Grid>
          ))}
        </Grid>
      ) : (
        <Paper sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="h6" color="textSecondary">
            No package requests found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Start by uploading a package-lock.json file to create your first
            request.
          </Typography>
        </Paper>
      )}
    </Box>
  );
}

function getStatusColor(status: PackageStatus): string {
  switch (status) {
    case PACKAGE_STATUS.REQUESTED:
      return "#757575"; // Grey
    case PACKAGE_STATUS.PERFORMING_LICENCE_CHECK:
    case PACKAGE_STATUS.PERFORMING_SECURITY_SCAN:
    case PACKAGE_STATUS.PENDING_APPROVAL:
      return "#ed6c02"; // Orange/Warning
    case PACKAGE_STATUS.LICENCE_CHECK_COMPLETE:
    case PACKAGE_STATUS.SECURITY_SCAN_COMPLETE:
      return "#1976d2"; // Blue/Info
    case PACKAGE_STATUS.APPROVED:
      return "#2e7d32"; // Green/Success
    case PACKAGE_STATUS.REJECTED:
      return "#d32f2f"; // Red/Error
    default:
      return "#757575"; // Grey
  }
}
