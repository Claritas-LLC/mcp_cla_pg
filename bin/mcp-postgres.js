#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const serverPath = path.join(__dirname, '..', 'server.py');

// Try to find python
const pythonCmds = ['python3', 'python'];
let pythonCmd = null;

for (const cmd of pythonCmds) {
    try {
        require('child_process').execSync(`${cmd} --version`, { stdio: 'ignore' });
        pythonCmd = cmd;
        break;
    } catch (e) {
        // continue
    }
}

if (!pythonCmd) {
    console.error('Error: Python not found. Please install Python 3.12 or later.');
    process.exit(1);
}

const args = [serverPath, ...process.argv.slice(2)];
const pythonProcess = spawn(pythonCmd, args, {
    stdio: 'inherit',
    env: process.env
});

pythonProcess.on('close', (code) => {
    process.exit(code);
});

pythonProcess.on('error', (err) => {
    console.error(`Failed to start python process: ${err.message}`);
    process.exit(1);
});
