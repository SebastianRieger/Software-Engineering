#!/usr/bin/env node

const { spawn, exec } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');
const http = require('http');
const net = require('net');

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
        this.rootPath = process.cwd();
        this.frontendPath = path.join(this.rootPath, 'Frontend', 'nimrag-frontend');
        this.backendPath = path.join(this.rootPath, 'Backend');
        this.backendSrcPath = path.join(this.backendPath, 'src');
        this.backendVenvPath = path.join(this.backendPath, 'venv_py312');
        this.children = [];
        this.systemPythonCommand = null;
        this.isShuttingDown = false;
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

    shellEnvPrefix(env) {
        if (this.isWindows) {
            return Object.entries(env)
                .map(([key, value]) => `set ${key}=${value}&&`)
                .join(' ');
        }

        return Object.entries(env)
            .map(([key, value]) => `${key}='${String(value).replace(/'/g, `'\\''`)}'`)
            .join(' ');
    }

    async checkCommand(command) {
        return new Promise((resolve) => {
            exec(`${command} --version`, (error) => {
                resolve(!error);
            });
        });
    }

    async commandSucceeds(command, cwd = process.cwd()) {
        return new Promise((resolve) => {
            exec(command, { cwd, shell: true }, (error) => {
                resolve(!error);
            });
        });
    }

    async captureCommand(command, cwd = process.cwd()) {
        return new Promise((resolve, reject) => {
            exec(command, { cwd, shell: true }, (error, stdout, stderr) => {
                if (error) {
                    reject(new Error(stderr || error.message));
                    return;
                }
                resolve(stdout.trim());
            });
        });
    }

    backendPythonPath() {
        return this.isWindows
            ? path.join(this.backendVenvPath, 'Scripts', 'python.exe')
            : path.join(this.backendVenvPath, 'bin', 'python');
    }

    backendPipPath() {
        return this.isWindows
            ? path.join(this.backendVenvPath, 'Scripts', 'pip.exe')
            : path.join(this.backendVenvPath, 'bin', 'pip');
    }

    async resolveSystemPython() {
        if (this.systemPythonCommand) {
            return this.systemPythonCommand;
        }

        const candidates = this.isWindows ? ['py -3', 'python'] : ['python3', 'python'];
        for (const candidate of candidates) {
            if (await this.commandSucceeds(`${candidate} --version`)) {
                this.systemPythonCommand = candidate;
                return candidate;
            }
        }

        throw new Error('Python wurde nicht gefunden. Bitte Python 3 installieren.');
    }

    async ensureBackendVenv() {
        const pythonPath = this.backendPythonPath();
        if (fs.existsSync(pythonPath)) {
            this.success(`Backend-Venv gefunden: ${this.backendVenvPath}`);
            return;
        }

        const systemPython = await this.resolveSystemPython();
        this.log(`Erzeuge Backend-Venv unter ${this.backendVenvPath}...`);
        await this.execCommand(`${systemPython} -m venv "${this.backendVenvPath}"`, this.rootPath);
        this.success('Backend-Venv wurde erstellt');
    }

    async installBackendDependencies() {
        const requirementsPath = path.join(this.backendPath, 'requirements.txt');
        if (!fs.existsSync(requirementsPath)) {
            throw new Error('Backend/requirements.txt wurde nicht gefunden.');
        }

        await this.ensureAubioBuildPrerequisites();

        this.log('Installiere aubio-Build-Basis fuer Python 3.12...');
        await this.execCommand(`"${this.backendPipPath()}" install "numpy>=1.26.1,<2" wheel setuptools`, this.backendPath);

        this.log('Baue aubio im Backend-Venv mit kompatiblen GCC-Flags...');
        const aubioBuildEnv = this.shellEnvPrefix({
            CFLAGS: '-Wno-error=incompatible-pointer-types -Wno-incompatible-pointer-types'
        });
        const aubioCommand = `${aubioBuildEnv} "${this.backendPipPath()}" install --no-build-isolation "aubio>=0.4.9"`;
        await this.execCommand(aubioCommand, this.backendPath);

        this.log('Installiere Backend-Abhaengigkeiten aus requirements.txt...');
        await this.execCommand(`"${this.backendPipPath()}" install -r requirements.txt`, this.backendPath);
        this.success('Backend-Abhaengigkeiten sind aktuell');
    }

    async ensureAubioBuildPrerequisites() {
        if (this.isWindows) {
            this.warning('aubio wird auf Windows nicht automatisch mit nativen Systempaketen vorbereitet. Fuer den produktiven Musical-Audio-Pfad Linux/Fedora verwenden.');
            return;
        }

        const pythonInclude = await this.captureCommand(`"${this.backendPythonPath()}" -c "import sysconfig; print(sysconfig.get_config_var('INCLUDEPY'))"`, this.backendPath);
        const pythonHeader = path.join(pythonInclude, 'Python.h');
        if (!fs.existsSync(pythonHeader)) {
            throw new Error(
                `Python-Header fuer das Backend-Venv fehlen: ${pythonHeader}\n` +
                'Auf Fedora installieren mit: sudo dnf install -y python3.12-devel aubio-devel aubio-lib'
            );
        }

        if (!(await this.commandSucceeds('pkg-config --modversion aubio', this.backendPath))) {
            throw new Error(
                'Native aubio-Entwicklungsdateien fehlen oder pkg-config findet aubio.pc nicht.\n' +
                'Auf Fedora installieren mit: sudo dnf install -y python3.12-devel aubio-devel aubio-lib'
            );
        }
    }

    async installFrontendDependencies() {
        if (!fs.existsSync(path.join(this.frontendPath, 'package.json'))) {
            throw new Error('Frontend package.json wurde nicht gefunden.');
        }

        this.log('Installiere Frontend-Abhaengigkeiten...');
        await this.execCommand('npm install', this.frontendPath);
        this.success('Frontend-Abhaengigkeiten sind aktuell');
    }

    async isPortOpen(port, host = '127.0.0.1') {
        return new Promise((resolve) => {
            const socket = new net.Socket();
            socket.setTimeout(1000);
            socket.once('connect', () => {
                socket.destroy();
                resolve(true);
            });
            socket.once('timeout', () => {
                socket.destroy();
                resolve(false);
            });
            socket.once('error', () => {
                resolve(false);
            });
            socket.connect(port, host);
        });
    }

    async stopDockerContainersPublishingPort(port) {
        if (!(await this.commandSucceeds('docker ps --format "{{.ID}}"', this.rootPath))) {
            return;
        }

        let containerIds = '';
        try {
            containerIds = await this.captureCommand(`docker ps --filter publish=${port} --format "{{.ID}}"`, this.rootPath);
        } catch {
            return;
        }

        if (!containerIds) {
            return;
        }

        const ids = containerIds.split(/\s+/).filter(Boolean);
        for (const id of ids) {
            this.warning(`Stoppe Docker-Container ${id}, weil er Port ${port} belegt...`);
            await new Promise((resolve) => {
                exec(`docker stop ${id}`, { cwd: this.rootPath, shell: true }, () => resolve());
            });
        }
    }

    async waitUntilPortIsFree(port, timeoutMs = 15000) {
        const deadline = Date.now() + timeoutMs;
        while (Date.now() < deadline) {
            if (!(await this.isPortOpen(port))) {
                return;
            }
            await new Promise((resolve) => setTimeout(resolve, 500));
        }

        throw new Error(`Port ${port} konnte nicht freigegeben werden.`);
    }

    async killPort(port) {
        this.log(`Bereinige Port ${port} vor dem Start...`);

        const commands = this.isWindows
            ? [
                `for /f "tokens=5" %a in ('netstat -ano ^| findstr :${port} ^| findstr LISTENING') do taskkill /F /PID %a`,
            ]
            : [
                `fuser -k ${port}/tcp`,
                `lsof -ti tcp:${port} | xargs -r kill -9`,
            ];

        for (const command of commands) {
            await new Promise((resolve) => {
                exec(command, { cwd: this.rootPath, shell: true }, () => resolve());
            });
        }

        if (await this.isPortOpen(port)) {
            await this.stopDockerContainersPublishingPort(port);
        }

        if (await this.isPortOpen(port)) {
            for (const command of commands) {
                await new Promise((resolve) => {
                    exec(command, { cwd: this.rootPath, shell: true }, () => resolve());
                });
            }
        }

        await this.waitUntilPortIsFree(port);
    }

    async waitForBackendReady(url, timeoutMs = 30000) {
        const deadline = Date.now() + timeoutMs;

        while (Date.now() < deadline) {
            const result = await new Promise((resolve) => {
                const request = http.get(url, (response) => {
                    let body = '';
                    response.setEncoding('utf8');
                    response.on('data', (chunk) => {
                        body += chunk;
                    });
                    response.on('end', () => {
                        resolve({ statusCode: response.statusCode ?? 0, body });
                    });
                });

                request.on('error', () => resolve(null));
                request.setTimeout(1500, () => {
                    request.destroy();
                    resolve(null);
                });
            });

            if (result && result.statusCode === 200) {
                try {
                    const payload = JSON.parse(result.body);
                    if (payload && payload.status === 'running' && typeof payload.version === 'string') {
                        return;
                    }
                } catch {
                    // ignore non-Nimrag responses until timeout
                }
            }

            if (result && result.statusCode >= 400 && result.statusCode < 500) {
                await new Promise((resolve) => setTimeout(resolve, 500));
                continue;
            }

            if (await this.isPortOpen(8000) === false) {
                await new Promise((resolve) => setTimeout(resolve, 500));
                continue;
            }

            await new Promise((resolve) => setTimeout(resolve, 500));
        }

        throw new Error(`Nimrag-Backend unter ${url} wurde nicht korrekt erreichbar.`);
    }

    async waitForFrontendReady(url, timeoutMs = 30000) {
        const deadline = Date.now() + timeoutMs;
        while (Date.now() < deadline) {
            const reachable = await new Promise((resolve) => {
                const request = http.get(url, (response) => {
                    response.resume();
                    resolve((response.statusCode ?? 0) < 500);
                });

                request.on('error', () => resolve(false));
                request.setTimeout(1500, () => {
                    request.destroy();
                    resolve(false);
                });
            });

            if (reachable) {
                return;
            }

            await new Promise((resolve) => setTimeout(resolve, 500));
        }

        throw new Error(`Frontend unter ${url} wurde nicht rechtzeitig erreichbar.`);
    }

    spawnManagedProcess(command, cwd, label) {
        const child = spawn(command, {
            cwd,
            shell: true,
            stdio: 'inherit',
            env: process.env,
        });

        child.on('exit', (code, signal) => {
            if (this.isShuttingDown) {
                return;
            }

            if (code !== 0 && code !== null) {
                this.error(`${label} wurde mit Exit-Code ${code} beendet.`);
            } else if (signal) {
                this.warning(`${label} wurde durch Signal ${signal} beendet.`);
            }

            this.shutdownAll(code ?? 1);
        });

        this.children.push(child);
        return child;
    }

    registerSignalHandlers() {
        const shutdown = () => this.shutdownAll(0);
        process.on('SIGINT', shutdown);
        process.on('SIGTERM', shutdown);
    }

    shutdownAll(exitCode = 0) {
        if (this.isShuttingDown) {
            return;
        }

        this.isShuttingDown = true;
        for (const child of this.children) {
            if (!child.killed) {
                child.kill('SIGTERM');
            }
        }

        setTimeout(() => process.exit(exitCode), 200);
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

        await this.resolveSystemPython();
        this.success(`Python ist installiert (${this.systemPythonCommand})`);

        this.info(`Platform detected: ${this.platform}`);
    }

    async installAllDependencies() {
        await this.installFrontendDependencies();
        await this.ensureBackendVenv();
        await this.installBackendDependencies();
    }

    async startFrontendOnly() {
        await this.checkPrerequisites();
        await this.installFrontendDependencies();
        await this.killPort(5173);
        this.log('Starte Frontend auf Port 5173...');
        this.registerSignalHandlers();
        this.spawnManagedProcess('npm run dev -- --host 0.0.0.0 --port 5173 --strictPort', this.frontendPath, 'Frontend');
    }

    async startBackendOnly() {
        await this.checkPrerequisites();
        await this.ensureBackendVenv();
        await this.installBackendDependencies();
        await this.killPort(8000);
        this.log('Starte Backend auf Port 8000...');
        this.registerSignalHandlers();
        this.spawnManagedProcess(`"${this.backendPythonPath()}" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`, this.backendSrcPath, 'Backend');
        await this.waitForBackendReady('http://127.0.0.1:8000/api/v1/system/status');
        this.success('Backend ist erreichbar unter http://localhost:8000');
    }

    async startFullStack() {
        await this.checkPrerequisites();
        await this.installAllDependencies();
        await this.killPort(8000);
        await this.killPort(5173);

        this.registerSignalHandlers();

        this.log('Starte Backend auf Port 8000...');
        this.spawnManagedProcess(`"${this.backendPythonPath()}" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000`, this.backendSrcPath, 'Backend');
        await this.waitForBackendReady('http://127.0.0.1:8000/api/v1/system/status');
        this.success('Backend ist erreichbar unter http://localhost:8000');

        this.log('Starte Frontend auf Port 5173...');
        this.spawnManagedProcess('npm run dev -- --host 0.0.0.0 --port 5173 --strictPort', this.frontendPath, 'Frontend');
        await this.waitForFrontendReady('http://127.0.0.1:5173/');

        this.success('Stack ist gestartet');
        this.info('Frontend: http://localhost:5173/');
        this.info('Backend: http://localhost:8000/api/v1/system/status');
    }

    async run() {
        console.log(`
${colors.cyan}
======================================
  Smart Mirror Project Setup
======================================${colors.reset}
`);

        try {
            if (this.args.includes('--frontend-only')) {
                await this.startFrontendOnly();
                return;
            }

            if (this.args.includes('--backend-only')) {
                await this.startBackendOnly();
                return;
            }

            if (this.args.includes('--dev') || this.args.includes('--start')) {
                await this.startFullStack();
                return;
            }

            await this.checkPrerequisites();
            console.log('');
            this.log('Starting installation process...');

            await this.installAllDependencies();

            console.log(`
${colors.green}
======================================
  Setup Complete!
======================================${colors.reset}

${colors.yellow}Next steps:${colors.reset}
    ${colors.blue}-${colors.reset} Full stack starten: ${colors.magenta}npm run dev${colors.reset}
    ${colors.blue}-${colors.reset} Nur Backend: ${colors.magenta}node setup.js --backend-only${colors.reset}
    ${colors.blue}-${colors.reset} Nur Frontend: ${colors.magenta}node setup.js --frontend-only${colors.reset}

${colors.yellow}Quick commands:${colors.reset}
  ${colors.blue}-${colors.reset} Setup: ${colors.magenta}node setup.js${colors.reset}
    ${colors.blue}-${colors.reset} Start dev: ${colors.magenta}node setup.js --dev${colors.reset}
`);

        } catch (error) {
            this.error(`Setup failed: ${error.message}`);
            process.exit(1);
        }
    }
}

// Run the setup
const setup = new SmartMirrorSetup();
setup.run().catch(console.error);