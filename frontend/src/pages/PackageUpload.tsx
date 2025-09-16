import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  Card,
  CardContent,
  LinearProgress,
} from "@mui/material";
import { CloudUpload, CheckCircle, Visibility } from "@mui/icons-material";
import { api, endpoints } from "../services/api";

export default function PackageUpload() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];
    if (!file.name.endsWith(".json")) {
      setError("Please upload a JSON file (package-lock.json)");
      return;
    }

    setUploading(true);
    setUploadProgress(0);
    setError("");
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post(endpoints.packages.upload, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
        onUploadProgress: progressEvent => {
          if (progressEvent.total) {
            const progress = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total
            );
            setUploadProgress(progress);
          }
        },
      });

      // Set progress to 100% when upload completes
      setUploadProgress(100);
      setUploadResult(response.data);

      // Auto-redirect to status page after successful upload
      setTimeout(() => {
        navigate("/status");
      }, 2000); // 2 second delay to show success message
    } catch (err: any) {
      const errorData = err.response?.data;
      setError(errorData?.error || "Upload failed. Please try again.");
      setErrorDetails(errorData?.details || "");
    } finally {
      setUploading(false);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/json": [".json"],
    },
    multiple: false,
  });

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Request Package Validation
      </Typography>

      <Typography variant="body1" color="textSecondary" paragraph>
        Upload your package-lock.json file to start the package validation
        process.
      </Typography>

      <Paper
        {...getRootProps()}
        sx={{
          p: 4,
          textAlign: "center",
          cursor: "pointer",
          border: "2px dashed",
          borderColor: isDragActive ? "primary.main" : "grey.300",
          backgroundColor: isDragActive ? "primary.50" : "grey.50",
          "&:hover": {
            borderColor: "primary.main",
            backgroundColor: "primary.50",
          },
        }}
      >
        <input {...getInputProps()} />

        <CloudUpload sx={{ fontSize: 48, color: "primary.main", mb: 2 }} />

        <Typography variant="h6" gutterBottom>
          {isDragActive
            ? "Drop the file here"
            : "Drag & drop package-lock.json here"}
        </Typography>

        <Typography variant="body2" color="textSecondary" paragraph>
          or click to select a file
        </Typography>

        <Button variant="outlined" component="span">
          Select File
        </Button>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <Typography variant="body1" gutterBottom>
            {error}
          </Typography>
          {errorDetails && (
            <Typography variant="body2" color="error.light">
              {errorDetails}
            </Typography>
          )}
        </Alert>
      )}

      {uploading && uploadProgress < 100 && (
        <Box mt={2}>
          <Box
            display="flex"
            alignItems="center"
            justifyContent="space-between"
            mb={1}
          >
            <Typography variant="body2" color="textSecondary">
              Uploading package-lock.json...
            </Typography>
            <Typography variant="body2" color="textSecondary">
              {uploadProgress}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={uploadProgress}
            sx={{ height: 8, borderRadius: 4 }}
          />
        </Box>
      )}

      {uploading && uploadProgress === 100 && (
        <Alert
          severity="success"
          sx={{ mt: 2 }}
          action={
            <Button
              color="inherit"
              size="small"
              startIcon={<Visibility />}
              onClick={() => navigate("/status")}
            >
              View Status
            </Button>
          }
        >
          <Typography variant="body2">
            Package uploaded successfully!
          </Typography>
        </Alert>
      )}

      {uploadResult && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Box display="flex" alignItems="center" mb={2}>
              <CheckCircle sx={{ color: "success.main", mr: 1 }} />
              <Typography variant="h6" color="success.main">
                Package uploaded successfully!
              </Typography>
            </Box>

            <Typography variant="body2" paragraph>
              <strong>ID:</strong> {uploadResult.request_id}
            </Typography>

            <Typography variant="body2" paragraph>
              <strong>Application:</strong> {uploadResult.application_name} v
              {uploadResult.version}
            </Typography>

            <Typography variant="body2" color="textSecondary">
              Your package-lock.json file has been uploaded and is being
              processed. You will be redirected to the Status page in a few
              seconds.
            </Typography>
          </CardContent>
        </Card>
      )}
    </Box>
  );
}
