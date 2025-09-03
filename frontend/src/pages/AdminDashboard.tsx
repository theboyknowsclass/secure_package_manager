import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "react-query";
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from "@mui/material";
import { CheckCircle, Publish, Warning } from "@mui/icons-material";
import { api, endpoints } from "../services/api";

interface ValidatedPackage {
  id: number;
  name: string;
  version: string;
  security_score: number;
  validation_errors: string[];
  request: {
    id: number;
    application: {
      name: string;
      version: string;
    };
  };
}

export default function AdminDashboard() {
  const [selectedPackage, setSelectedPackage] =
    useState<ValidatedPackage | null>(null);
  const [approveDialogOpen, setApproveDialogOpen] = useState(false);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: "",
    severity: "success" as any,
  });

  const queryClient = useQueryClient();

  const {
    data: packages,
    isLoading,
    error,
  } = useQuery<ValidatedPackage[]>("validatedPackages", async () => {
    const response = await api.get(endpoints.admin.validatedPackages);
    return response.data.packages;
  });

  const approveMutation = useMutation(
    async (packageId: number) => {
      await api.post(endpoints.admin.approvePackage(packageId));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("validatedPackages");
        setSnackbar({
          open: true,
          message: "Package approved successfully!",
          severity: "success",
        });
        setApproveDialogOpen(false);
      },
      onError: () => {
        setSnackbar({
          open: true,
          message: "Failed to approve package",
          severity: "error",
        });
      },
    }
  );

  const publishMutation = useMutation(
    async (packageId: number) => {
      await api.post(endpoints.admin.publishPackage(packageId));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("validatedPackages");
        setSnackbar({
          open: true,
          message: "Package published successfully!",
          severity: "success",
        });
        setPublishDialogOpen(false);
      },
      onError: () => {
        setSnackbar({
          open: true,
          message: "Failed to publish package",
          severity: "error",
        });
      },
    }
  );

  const handleApprove = (pkg: ValidatedPackage) => {
    setSelectedPackage(pkg);
    setApproveDialogOpen(true);
  };

  const handlePublish = (pkg: ValidatedPackage) => {
    setSelectedPackage(pkg);
    setPublishDialogOpen(true);
  };

  const confirmApprove = () => {
    if (selectedPackage) {
      approveMutation.mutate(selectedPackage.id);
    }
  };

  const confirmPublish = () => {
    if (selectedPackage) {
      publishMutation.mutate(selectedPackage.id);
    }
  };

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
        Failed to load validated packages. Please try again.
      </Alert>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Admin Dashboard
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Review validated packages and manage the approval and publishing
        workflow.
      </Typography>

      {packages && packages.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Package</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Application</TableCell>
                <TableCell>Security Score</TableCell>
                <TableCell>Validation Errors</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {packages.map((pkg) => (
                <TableRow key={pkg.id}>
                  <TableCell>{pkg.name}</TableCell>
                  <TableCell>{pkg.version}</TableCell>
                  <TableCell>
                    {pkg.request.application.name} v
                    {pkg.request.application.version}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={`${pkg.security_score}/100`}
                      color={getScoreColor(pkg.security_score)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    {pkg.validation_errors &&
                    pkg.validation_errors.length > 0 ? (
                      <Chip
                        icon={<Warning />}
                        label={`${pkg.validation_errors.length} errors`}
                        color="warning"
                        size="small"
                      />
                    ) : (
                      <Chip label="No errors" color="success" size="small" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Box display="flex" gap={1}>
                      <Button
                        variant="outlined"
                        size="small"
                        startIcon={<CheckCircle />}
                        onClick={() => handleApprove(pkg)}
                        disabled={approveMutation.isLoading}
                      >
                        Approve
                      </Button>
                      <Button
                        variant="contained"
                        size="small"
                        startIcon={<Publish />}
                        onClick={() => handlePublish(pkg)}
                        disabled={publishMutation.isLoading}
                      >
                        Publish
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Paper sx={{ p: 3, textAlign: "center" }}>
          <Typography variant="h6" color="textSecondary">
            No validated packages found
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Packages will appear here after they have been validated and are
            ready for review.
          </Typography>
        </Paper>
      )}

      {/* Approve Dialog */}
      <Dialog
        open={approveDialogOpen}
        onClose={() => setApproveDialogOpen(false)}
      >
        <DialogTitle>Approve Package</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to approve{" "}
            <strong>
              {selectedPackage?.name}@{selectedPackage?.version}
            </strong>
            ?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            This will mark the package as approved and ready for publishing.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setApproveDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={confirmApprove}
            variant="contained"
            disabled={approveMutation.isLoading}
          >
            {approveMutation.isLoading ? "Approving..." : "Approve"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Publish Dialog */}
      <Dialog
        open={publishDialogOpen}
        onClose={() => setPublishDialogOpen(false)}
      >
        <DialogTitle>Publish Package</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to publish{" "}
            <strong>
              {selectedPackage?.name}@{selectedPackage?.version}
            </strong>{" "}
            to the secure repository?
          </Typography>
          <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
            This action cannot be undone. The package will be available in the
            secure repository.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPublishDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={confirmPublish}
            variant="contained"
            color="primary"
            disabled={publishMutation.isLoading}
          >
            {publishMutation.isLoading ? "Publishing..." : "Publish"}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          severity={snackbar.severity}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}

function getScoreColor(
  score: number
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  if (score >= 80) return "success";
  if (score >= 60) return "warning";
  return "error";
}
