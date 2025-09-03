import React, { useState } from "react";
import { useQuery } from "react-query";
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
  Chip,
  IconButton,
  Collapse,
  CircularProgress,
  Alert,
} from "@mui/material";
import { KeyboardArrowDown, KeyboardArrowUp } from "@mui/icons-material";
import { api, endpoints } from "../services/api";

interface Package {
  id: number;
  name: string;
  version: string;
  status: string;
  security_score: number | null;
  validation_errors: string[];
}

interface PackageRequest {
  id: number;
  status: string;
  total_packages: number;
  validated_packages: number;
  created_at: string;
  application: {
    name: string;
    version: string;
  };
  packages: Package[];
}

function Row({ request }: { request: PackageRequest }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <TableRow sx={{ "& > *": { borderBottom: "unset" } }}>
        <TableCell>
          <IconButton size="small" onClick={() => setOpen(!open)}>
            {open ? <KeyboardArrowUp /> : <KeyboardArrowDown />}
          </IconButton>
        </TableCell>
        <TableCell>{request.id}</TableCell>
        <TableCell>{request.application.name}</TableCell>
        <TableCell>{request.application.version}</TableCell>
        <TableCell>
          <Chip
            label={request.status}
            color={getStatusColor(request.status)}
            size="small"
          />
        </TableCell>
        <TableCell>
          {request.validated_packages}/{request.total_packages}
        </TableCell>
        <TableCell>
          {new Date(request.created_at).toLocaleDateString()}
        </TableCell>
      </TableRow>

      <TableRow>
        <TableCell style={{ paddingBottom: 0, paddingTop: 0 }} colSpan={7}>
          <Collapse in={open} timeout="auto" unmountOnExit>
            <Box sx={{ margin: 1 }}>
              <Typography variant="h6" gutterBottom component="div">
                Packages
              </Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Name</TableCell>
                    <TableCell>Version</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Security Score</TableCell>
                    <TableCell>Errors</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {request.packages.map((pkg) => (
                    <TableRow key={pkg.id}>
                      <TableCell>{pkg.name}</TableCell>
                      <TableCell>{pkg.version}</TableCell>
                      <TableCell>
                        <Chip
                          label={pkg.status}
                          color={getStatusColor(pkg.status)}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>
                        {pkg.security_score !== null ? (
                          <Chip
                            label={`${pkg.security_score}/100`}
                            color={getScoreColor(pkg.security_score)}
                            size="small"
                          />
                        ) : (
                          "N/A"
                        )}
                      </TableCell>
                      <TableCell>
                        {pkg.validation_errors &&
                        pkg.validation_errors.length > 0 ? (
                          <Box>
                            {pkg.validation_errors.map((error, index) => (
                              <Typography
                                key={index}
                                variant="caption"
                                color="error"
                                display="block"
                              >
                                {error}
                              </Typography>
                            ))}
                          </Box>
                        ) : (
                          "None"
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          </Collapse>
        </TableCell>
      </TableRow>
    </>
  );
}

export default function PackageRequests() {
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

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Package Requests
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Track the status of your package validation requests and view detailed
        information about each package.
      </Typography>

      {requests && requests.length > 0 ? (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell />
                <TableCell>ID</TableCell>
                <TableCell>Application</TableCell>
                <TableCell>Version</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {requests.map((request) => (
                <Row key={request.id} request={request} />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
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

function getStatusColor(
  status: string
):
  | "default"
  | "primary"
  | "secondary"
  | "error"
  | "info"
  | "success"
  | "warning" {
  switch (status) {
    case "requested":
      return "primary";
    case "validating":
      return "warning";
    case "validated":
      return "success";
    case "approved":
      return "info";
    case "published":
      return "success";
    case "rejected":
      return "error";
    default:
      return "default";
  }
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
