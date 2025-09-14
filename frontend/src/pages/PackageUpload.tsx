import React, { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Typography,
  Paper,
  Button,
  Alert,
  CircularProgress,
  Card,
  CardContent,
} from "@mui/material";
import { CloudUpload } from "@mui/icons-material";
import { api, endpoints } from "../services/api";

export default function PackageUpload() {
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
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
    setError("");
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await api.post(endpoints.packages.upload, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      setUploadResult(response.data);

      // Auto-redirect to status page after successful upload
      setTimeout(() => {
        navigate("/status");
      }, 1500); // 1.5 second delay to show success message
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

      {uploading && (
        <Box display="flex" alignItems="center" justifyContent="center" mt={2}>
          <CircularProgress size={20} sx={{ mr: 1 }} />
          <Typography>Uploading and processing package...</Typography>
        </Box>
      )}

      {uploadResult && (
        <Card sx={{ mt: 2 }}>
          <CardContent>
            <Typography variant="h6" color="success.main" gutterBottom>
              Upload Successful!
            </Typography>

            <Typography variant="body2" paragraph>
              <strong>Request ID:</strong> {uploadResult.request_id}
            </Typography>

            <Typography variant="body2" paragraph>
              <strong>Application:</strong> {uploadResult.application.name} v
              {uploadResult.application.version}
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
