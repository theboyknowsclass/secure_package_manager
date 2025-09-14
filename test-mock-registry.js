#!/usr/bin/env node

const http = require('http');
const https = require('https');

const REGISTRY_URL = 'http://localhost:8080';

function makeRequest(url, options = {}) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    
    const req = client.request(url, options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          const jsonData = JSON.parse(data);
          resolve({ status: res.statusCode, data: jsonData });
        } catch (e) {
          resolve({ status: res.statusCode, data: data });
        }
      });
    });
    
    req.on('error', reject);
    req.end();
  });
}

async function testRegistry() {
  console.log('Testing Mock NPM Registry...\n');
  
  try {
    // Test health check
    console.log('1. Testing health check...');
    const health = await makeRequest(`${REGISTRY_URL}/health`);
    console.log(`   Status: ${health.status}`);
    console.log(`   Response:`, health.data);
    console.log('');
    
    // Test registry info
    console.log('2. Testing registry info...');
    const info = await makeRequest(`${REGISTRY_URL}/`);
    console.log(`   Status: ${info.status}`);
    console.log(`   Response:`, info.data);
    console.log('');
    
    // Test search (should be empty initially)
    console.log('3. Testing search...');
    const search = await makeRequest(`${REGISTRY_URL}/-/v1/search`);
    console.log(`   Status: ${search.status}`);
    console.log(`   Response:`, search.data);
    console.log('');
    
    // Test non-existent package
    console.log('4. Testing non-existent package...');
    const notFound = await makeRequest(`${REGISTRY_URL}/test-package`);
    console.log(`   Status: ${notFound.status}`);
    console.log(`   Response:`, notFound.data);
    console.log('');
    
    console.log('✅ All tests completed successfully!');
    console.log('\nTo test publishing, you can run:');
    console.log('npm config set registry http://localhost:8080');
    console.log('npm publish (in a directory with package.json)');
    
  } catch (error) {
    console.error('❌ Test failed:', error.message);
    process.exit(1);
  }
}

testRegistry();
