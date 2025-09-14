const express = require('express');
const multer = require('multer');
const tar = require('tar');
const fs = require('fs');
const path = require('path');
const cors = require('cors');
const compression = require('compression');

const app = express();
const PORT = process.env.PORT || 8080;

// Middleware
app.use(cors());
app.use(compression());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const packageName = req.params.package || 'unknown';
    const packageDir = path.join('/app/storage/packages', packageName);
    if (!fs.existsSync(packageDir)) {
      fs.mkdirSync(packageDir, { recursive: true });
    }
    cb(null, packageDir);
  },
  filename: (req, file, cb) => {
    cb(null, file.originalname);
  }
});

const upload = multer({ storage });

// In-memory storage for package metadata
const packages = new Map();
const packageVersions = new Map();

// Helper function to create package metadata
function createPackageMetadata(name, version, tarball) {
  const packageId = `${name}@${version}`;
  const now = new Date().toISOString();
  
  const packageData = {
    name,
    version,
    description: `Mock package ${name}`,
    main: 'index.js',
    scripts: {},
    keywords: ['mock', 'secure'],
    author: 'Secure Package Manager',
    license: 'MIT',
    dist: {
      shasum: 'mock-shasum',
      tarball: tarball || `http://localhost:${PORT}/${name}/-/${name}-${version}.tgz`
    },
    time: {
      created: now,
      modified: now,
      [version]: now
    },
    _id: packageId,
    _rev: '1-0'
  };

  return packageData;
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

// Mock authentication endpoints for npm
app.post('/-/user/org.couchdb.user:test', (req, res) => {
  // Mock user creation/login
  res.json({
    ok: true,
    id: 'org.couchdb.user:test',
    rev: '1-0',
    name: 'test',
    roles: [],
    type: 'user',
    password_scheme: 'pbkdf2',
    iterations: 10,
    derived_key: 'test',
    salt: 'test'
  });
});

app.put('/-/user/org.couchdb.user:test', (req, res) => {
  // Mock user login
  res.json({
    ok: true,
    id: 'org.couchdb.user:test',
    rev: '1-0',
    name: 'test',
    roles: [],
    type: 'user'
  });
});

app.get('/-/whoami', (req, res) => {
  // Mock whoami endpoint
  res.json({
    username: 'test'
  });
});

// Registry info endpoint
app.get('/', (req, res) => {
  res.json({
    db_name: 'mock-secure-registry',
    engine: 'mock',
    doc_count: packages.size,
    update_seq: packages.size,
    compact_running: false,
    sizes: {
      active: 0,
      external: 0,
      file: 0
    },
    purge_seq: 0,
    other: {
      data_size: 0
    },
    doc_del_count: 0,
    disk_size: 0,
    data_size: 0
  });
});

// Get package info
app.get('/:package', (req, res) => {
  const packageName = req.params.package;
  
  if (!packages.has(packageName)) {
    return res.status(404).json({
      error: 'not_found',
      reason: 'document not found'
    });
  }

  const packageData = packages.get(packageName);
  res.json(packageData);
});

// Get specific package version
app.get('/:package/:version', (req, res) => {
  const packageName = req.params.package;
  const version = req.params.version;
  const packageId = `${packageName}@${version}`;
  
  if (!packageVersions.has(packageId)) {
    return res.status(404).json({
      error: 'not_found',
      reason: 'version not found'
    });
  }

  const packageData = packageVersions.get(packageId);
  res.json(packageData);
});

// Publish package
app.put('/:package', upload.single('package'), (req, res) => {
  const packageName = req.params.package;
  const packageData = req.body;
  
  console.log(`Publishing package: ${packageName}`);
  console.log('Package data:', packageData);
  
  // Mock authentication - accept any request for testing
  // In production, this would validate JWT tokens or other auth mechanisms
  
  // Extract version from the npm publish format
  let version;
  if (packageData.versions && packageData['dist-tags'] && packageData['dist-tags'].latest) {
    version = packageData['dist-tags'].latest;
  } else if (packageData.version) {
    version = packageData.version;
  } else {
    return res.status(400).json({
      error: 'invalid_package',
      reason: 'version is required'
    });
  }

  const packageId = `${packageName}@${version}`;
  
  // Check if version already exists
  if (packageVersions.has(packageId)) {
    return res.status(409).json({
      error: 'conflict',
      reason: 'version already exists'
    });
  }

  // Create package metadata from npm publish format
  const tarballUrl = `http://localhost:${PORT}/${packageName}/-/${packageName}-${version}.tgz`;
  
  // Extract version data from the npm publish format
  let versionData;
  if (packageData.versions && packageData.versions[version]) {
    // Use the version data from npm publish
    const npmVersionData = packageData.versions[version];
    versionData = {
      name: packageName,
      version: version,
      description: npmVersionData.description || `Mock package ${packageName}`,
      main: npmVersionData.main || 'index.js',
      scripts: npmVersionData.scripts || {},
      keywords: npmVersionData.keywords || ['mock', 'secure'],
      author: npmVersionData.author || 'Secure Package Manager',
      license: npmVersionData.license || 'MIT',
      dist: {
        shasum: npmVersionData.dist?.shasum || 'mock-shasum',
        tarball: tarballUrl
      },
      time: {
        created: new Date().toISOString(),
        modified: new Date().toISOString(),
        [version]: new Date().toISOString()
      },
      _id: packageId,
      _rev: '1-0'
    };
  } else {
    // Fallback to creating metadata
    versionData = createPackageMetadata(packageName, version, tarballUrl);
  }
  
  // Store version data
  packageVersions.set(packageId, versionData);
  
  // Update or create package data
  if (!packages.has(packageName)) {
    packages.set(packageName, {
          name: packageName,
          'dist-tags': { latest: version },
          versions: {},
          time: {
            created: new Date().toISOString(),
            modified: new Date().toISOString()
          },
          _id: packageName,
          _rev: '1-0'
        });
  }
  
  const packageInfo = packages.get(packageName);
  packageInfo.versions[version] = versionData;
  packageInfo.time[version] = new Date().toISOString();
  packageInfo.time.modified = new Date().toISOString();
  packageInfo['dist-tags'].latest = version;
  
  // Save tarball if provided
  if (req.file) {
    console.log(`Tarball saved: ${req.file.path}`);
  } else if (packageData._attachments) {
    // Handle tarball from _attachments (npm publish format)
    const attachmentKeys = Object.keys(packageData._attachments);
    if (attachmentKeys.length > 0) {
      const tarballName = attachmentKeys[0];
      const attachment = packageData._attachments[tarballName];
      
      // Create package directory
      const packageDir = path.join('/app/storage/packages', packageName);
      if (!fs.existsSync(packageDir)) {
        fs.mkdirSync(packageDir, { recursive: true });
      }
      
      // Save tarball
      const tarballPath = path.join(packageDir, tarballName);
      const tarballData = Buffer.from(attachment.data, 'base64');
      fs.writeFileSync(tarballPath, tarballData);
      console.log(`Tarball saved: ${tarballPath}`);
    }
  }

  console.log(`Successfully published ${packageName}@${version}`);
  
  res.status(201).json({
    ok: true,
    id: packageId,
    rev: '1-0'
  });
});

// Download tarball
app.get('/:package/-/:filename', (req, res) => {
  const packageName = req.params.package;
  const filename = req.params.filename;
  const filePath = path.join('/app/storage/packages', packageName, filename);
  
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({
      error: 'not_found',
      reason: 'tarball not found'
    });
  }
  
  res.download(filePath);
});

// Search packages
app.get('/-/v1/search', (req, res) => {
  const query = req.query.text || '';
  const size = parseInt(req.query.size) || 20;
  const from = parseInt(req.query.from) || 0;
  
  const results = [];
  let index = 0;
  
  for (const [packageName, packageData] of packages) {
    if (packageName.toLowerCase().includes(query.toLowerCase())) {
      if (index >= from && results.length < size) {
        results.push({
          package: {
            name: packageName,
            version: packageData['dist-tags'].latest,
            description: packageData.versions[packageData['dist-tags'].latest]?.description || '',
            keywords: packageData.versions[packageData['dist-tags'].latest]?.keywords || [],
            date: packageData.time.modified,
            author: packageData.versions[packageData['dist-tags'].latest]?.author || {},
            publisher: {
              username: 'mock-user',
              email: 'mock@example.com'
            },
            maintainers: []
          },
          score: {
            final: 1.0,
            detail: {
              quality: 1.0,
              popularity: 1.0,
              maintenance: 1.0
            }
          },
          searchScore: 1.0
        });
      }
      index++;
    }
  }
  
  res.json({
    objects: results,
    total: results.length,
    time: new Date().toISOString()
  });
});

// List all packages (for debugging)
app.get('/-/all', (req, res) => {
  const allPackages = {};
  for (const [packageName, packageData] of packages) {
    allPackages[packageName] = {
      name: packageName,
      'dist-tags': packageData['dist-tags'],
      time: packageData.time
    };
  }
  res.json(allPackages);
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error('Error:', err);
  res.status(500).json({
    error: 'internal_server_error',
    reason: err.message
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({
    error: 'not_found',
    reason: 'endpoint not found'
  });
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Mock Secure NPM Registry running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
  console.log(`Registry info: http://localhost:${PORT}/`);
});
