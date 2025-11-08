#!/usr/bin/env node

const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

// ANSI Colors
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m'
};

class SmartMirrorSetup {
    constructor() {
        this.platform = os.platform();
        this.isWindows = this.platform === 'win32';
        this.args = process.argv.slice(2);
    }

    log(message, color = 'cyan') {
        console.log(`${colors[color]}[SETUP]${colors.reset} ${message}`);
    }

    success(message) {
        console.log(`${colors.green}[SUCCESS] ${message}${colors.reset}`);
    }

    warning(message) {
        console.log(`${colors.yellow}[WARNING] ${message}${colors.reset}`);
    }

    error(message) {
        console.log(`${colors.red}[ERROR] ${message}${colors.reset}`);
    }

    info(message) {
        console.log(`${colors.blue}[INFO] ${message}${colors.reset}`);
    }

    async execCommand(command, cwd = process.cwd()) {
        return new Promise((resolve, reject) => {
            const child = spawn(command, { 
                shell: true, 
                cwd,
                stdio: 'inherit' 
            });

            child.on('close', (code) => {
                if (code === 0) {
                    resolve();
                } else {
                    reject(new Error(`Command failed with code ${code}`));
                }
            });

            child.on('error', reject);
        });
    }

    async checkCommand(command) {
        return new Promise((resolve) => {
            exec(`${command} --version`, (error) => {
                resolve(!error);
            });
        });
    }

    async checkPrerequisites() {
        this.log('Checking prerequisites...');
        
        // Check Node.js
        const hasNode = await this.checkCommand('node');
        if (!hasNode) {
            this.error('Node.js not found! Please install Node.js from https://nodejs.org/');
            process.exit(1);
        }
        this.success('Node.js is installed');

        // Check NPM
        const hasNpm = await this.checkCommand('npm');
        if (!hasNpm) {
            this.error('NPM not found! Please install NPM');
            process.exit(1);
        }
        this.success('NPM is installed');

        // Check Python (optional for backend)
        const hasPython = await this.checkCommand('python') || await this.checkCommand('python3');
        if (hasPython) {
            this.success('Python is installed');
        } else {
            this.warning('Python not found - Backend features may not work');
        }

        this.info(`Platform detected: ${this.platform}`);
    }

    async installFrontendDependencies() {
        const frontendPath = path.join(process.cwd(), 'Frontend', 'nimrag-frontend');
        
        if (!fs.existsSync(frontendPath)) {
            this.warning('Frontend directory not found');
            return false;
        }

        if (!fs.existsSync(path.join(frontendPath, 'package.json'))) {
            this.warning('Frontend package.json not found');
            return false;
        }

        this.log('Installing Frontend dependencies...');
        try {
            await this.execCommand('npm install', frontendPath);
            this.success('Frontend dependencies installed!');
            return true;
        } catch (error) {
            this.error('Failed to install Frontend dependencies');
            return false;
        }
    }

    async checkBackend() {
        const backendPath = path.join(process.cwd(), 'Backend');
        
        if (fs.existsSync(backendPath)) {
            this.info('Backend directory found');
            
            const requirementsPath = path.join(backendPath, 'requirements.txt');
            if (fs.existsSync(requirementsPath)) {
                this.info('To install Backend dependencies, run:');
                console.log(`  cd Backend && pip install -r requirements.txt`);
            }
        }
    }

    async startFrontend() {
        const frontendPath = path.join(process.cwd(), 'Frontend', 'nimrag-frontend');
        
        if (!fs.existsSync(frontendPath)) {
            this.error('Frontend not found! Run setup first.');
            return;
        }

        this.log('Starting Frontend development server...');
        this.info('Frontend will open in your browser automatically');
        this.info('Press Ctrl+C to stop the server');
        
        try {
            await this.execCommand('npm run dev', frontendPath);
        } catch (error) {
            this.error('Failed to start Frontend');
        }
    }

    async run() {
        console.log(`
${colors.cyan}
======================================
  Smart Mirror Project Setup
======================================${colors.reset}
`);

        try {
            // Check what to do based on arguments
            if (this.args.includes('--dev') || this.args.includes('--start')) {
                await this.startFrontend();
                return;
            }

            // Full setup process
            await this.checkPrerequisites();
            
            console.log('');
            this.log('Starting installation process...');
            
            const frontendInstalled = await this.installFrontendDependencies();
            await this.checkBackend();

            console.log(`
${colors.green}
======================================
  Setup Complete!
======================================${colors.reset}

${colors.yellow}Next steps:${colors.reset}
  ${colors.blue}-${colors.reset} Start Frontend: ${colors.magenta}npm run dev${colors.reset}
  ${colors.blue}-${colors.reset} Or use: ${colors.magenta}node setup.js --dev${colors.reset}
  ${colors.blue}-${colors.reset} Backend: ${colors.magenta}cd Backend && python main.py${colors.reset}

${colors.yellow}Quick commands:${colors.reset}
  ${colors.blue}-${colors.reset} Setup: ${colors.magenta}node setup.js${colors.reset}
  ${colors.blue}-${colors.reset} Start dev: ${colors.magenta}node setup.js --dev${colors.reset}
`);

            if (frontendInstalled) {
                this.info('Would you like to start the development server now? (y/n)');
                
                process.stdin.setRawMode(true);
                process.stdin.resume();
                process.stdin.on('data', async (key) => {
                    const input = key.toString().toLowerCase();
                    if (input === 'y' || input === '\r') {
                        console.log('\n');
                        await this.startFrontend();
                    } else {
                        console.log('\nSetup completed. Run "node setup.js --dev" to start later.');
                        process.exit(0);
                    }
                });
            }

        } catch (error) {
            this.error(`Setup failed: ${error.message}`);
            process.exit(1);
        }
    }
}

// Run the setup
const setup = new SmartMirrorSetup();
setup.run().catch(console.error);