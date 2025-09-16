import React, { useState } from "react";
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Container,
} from "@mui/material";
import { Settings as SettingsIcon, Storage, Gavel } from "@mui/icons-material";
import RepositoryConfig from "../components/RepositoryConfig";
import LicenseManagementTab from "./LicenseManagementTab";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`settings-tabpanel-${index}`}
      aria-labelledby={`settings-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

function a11yProps(index: number) {
  return {
    id: `settings-tab-${index}`,
    'aria-controls': `settings-tabpanel-${index}`,
  };
}

export default function Settings() {
  const [tabValue, setTabValue] = useState(0);

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ mt: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
          <SettingsIcon sx={{ mr: 2, fontSize: 32 }} color="primary" />
          <Typography variant="h4" component="h1">
            System Settings
          </Typography>
        </Box>
        
        <Typography variant="body1" color="textSecondary" paragraph>
          Configure system settings and manage licenses for the secure package manager.
        </Typography>

        <Paper sx={{ width: '100%' }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs
              value={tabValue}
              onChange={handleTabChange}
              aria-label="settings tabs"
              variant="fullWidth"
            >
              <Tab
                icon={<Storage />}
                label="Repository Configuration"
                iconPosition="start"
                {...a11yProps(0)}
              />
              <Tab
                icon={<Gavel />}
                label="License Management"
                iconPosition="start"
                {...a11yProps(1)}
              />
            </Tabs>
          </Box>
          
          <TabPanel value={tabValue} index={0}>
            <RepositoryConfig />
          </TabPanel>
          
          <TabPanel value={tabValue} index={1}>
            <LicenseManagementTab />
          </TabPanel>
        </Paper>
      </Box>
    </Container>
  );
}
