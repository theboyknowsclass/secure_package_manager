import React from "react";
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Paper,
  Alert,
} from "@mui/material";
import { useAuth } from "../hooks/useAuth";
import { usePackageRequests } from "../services/api/packageService";
import { type PackageRequest, isCompletedStatus } from "../types";
import { LoadingSpinner, PackageStatusChip } from "../components/atoms";

export default function Dashboard() {
  const { user } = useAuth();

  const { data: requests, isLoading, error } = usePackageRequests();

  if (isLoading) {
    return <LoadingSpinner message="Loading package requests..." />;
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
    requests?.filter((r: PackageRequest) => !isCompletedStatus(r.status))
      .length || 0;
  const completedRequests =
    requests?.filter((r: PackageRequest) => isCompletedStatus(r.status))
      .length || 0;

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
          {requests.slice(0, 6).map((request: PackageRequest) => (
            <Grid item xs={12} md={6} key={request.id}>
              <Paper sx={{ p: 2 }}>
                <Box
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  mb={1}
                >
                  <Typography variant="h6">
                    {request.application_name} v{request.version}
                  </Typography>
                  <PackageStatusChip
                    status={request.status}
                    size="small"
                    showTooltip={true}
                  />
                </Box>

                <Typography variant="body2" color="textSecondary" gutterBottom>
                  ID: {request.id}
                </Typography>

                <Typography variant="body2" color="textSecondary">
                  Packages: {request.completion_percentage}% complete (
                  {request.total_packages} total)
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
