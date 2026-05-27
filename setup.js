#!/usr/bin/env node

const crypto = require('crypto');
const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const SUPPORTED_PYTHON_MIN_MINOR = 11;
const SUPPORTED_PYTHON_MAX_MINOR = 13;
const PREFERRED_PYTHON_MINORS = [12, 11, 13];

const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
};

class SmartMirrorSetup {
    constructor() {
        this.rootDir = __dirname;
        this.platform = os.platform();
        this.isWindows = this.platform === 'win32';
        this.args = new Set(process.argv.slice(2));
        this.frontendDir = path.join(this.rootDir, 'Frontend', 'nimrag-frontend');
        this.backendDir = path.join(this.rootDir, 'Backend');
        this.backendSrcDir = path.join(this.backendDir, 'src');
        this.backendRequirementsPath = path.join(this.backendDir, 'requirements.txt');
        this.backendVenvDir = path.join(this.backendDir, '.venv');
        this.backendStatePath = path.join(this.backendVenvDir, '.bootstrap-state.json');
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

    hasArg(...names) {
        return names.some((name) => this.args.has(name));
    }

    getNpmCommand() {
        return this.isWindows ? 'npm.cmd' : 'npm';
    }

    getBackendPythonPath() {
        return this.isWindows
            ? path.join(this.backendVenvDir, 'Scripts', 'python.exe')
            : path.join(this.backendVenvDir, 'bin', 'python');
    }

    requiresShell(command) {
        return this.isWindows && /\.(cmd|bat)$/i.test(command);
    }

    runCommandCapture(command, args = [], options = {}) {
        const result = spawnSync(command, args, {
            cwd: options.cwd || this.rootDir,
            env: { ...process.env, ...(options.env || {}) },
            encoding: 'utf8',
            shell: this.requiresShell(command),
        });

        if (result.error) {
            return null;
        }

        return {
            status: result.status,
            output: `${result.stdout || ''}${result.stderr || ''}`.trim(),
        };
    }

    async execCommand(command, args = [], options = {}) {
        return new Promise((resolve, reject) => {
            const child = spawn(command, args, {
                cwd: options.cwd || this.rootDir,
                env: { ...process.env, ...(options.env || {}) },
                stdio: options.stdio || 'inherit',
                shell: this.requiresShell(command),
            });

            child.on('error', reject);
            child.on('close', (code) => {
                if (code === 0) {
                    resolve();
                    return;
                }

                reject(new Error(`Command failed with code ${code}: ${command} ${args.join(' ')}`));
            });
        });
    }

    checkCommand(command, args = ['--version']) {
        const result = this.runCommandCapture(command, args);
        return Boolean(result && result.status === 0);
    }

    ensureDirectoryExists(directoryPath) {
        fs.mkdirSync(directoryPath, { recursive: true });
    }

    hashFile(filePath) {
        const contents = fs.readFileSync(filePath);
        return crypto.createHash('sha256').update(contents).digest('hex');
    }

    readBackendBootstrapState() {
        if (!fs.existsSync(this.backendStatePath)) {
            return null;
        }

        try {
            return JSON.parse(fs.readFileSync(this.backendStatePath, 'utf8'));
        } catch {
            return null;
        }
    }

    writeBackendBootstrapState(state) {
        this.ensureDirectoryExists(this.backendVenvDir);
        fs.writeFileSync(this.backendStatePath, JSON.stringify(state, null, 2));
    }

    readBackendRequirementLines() {
        return fs.readFileSync(this.backendRequirementsPath, 'utf8').split(/\r?\n/);
    }

    findRequirementLine(packageName) {
        const normalizedName = packageName.toLowerCase();
        return this.readBackendRequirementLines().find((line) => {
            const trimmed = line.trim().toLowerCase();
            return trimmed.length > 0 && !trimmed.startsWith('#') && trimmed.startsWith(normalizedName);
        }) || null;
    }

    buildBackendNativeEnv() {
        if (this.platform !== 'linux') {
            return {};
        }

        const extraFlags = ['-Wno-incompatible-pointer-types'];
        return {
            CFLAGS: [process.env.CFLAGS, ...extraFlags].filter(Boolean).join(' '),
        };
    }

    async installBackendPythonPackages(backendPython, args, options = {}) {
        await this.execCommand(
            backendPython.pythonPath,
            ['-m', 'pip', 'install', ...args],
            {
                cwd: this.backendDir,
                env: { ...this.buildBackendNativeEnv(), ...(options.env || {}) },
            }
        );
    }

    async installBackendRequirements(backendPython) {
        const numpyRequirement = this.findRequirementLine('numpy');
        const aubioRequirement = this.findRequirementLine('aubio');
        const filteredRequirementLines = this.readBackendRequirementLines().filter(
            (line) => !line.trim().toLowerCase().startsWith('aubio')
        );
        const tempRequirementsPath = path.join(os.tmpdir(), `nimrag-backend-requirements-${process.pid}.txt`);

        if (numpyRequirement) {
            await this.installBackendPythonPackages(backendPython, [numpyRequirement]);
        }

        if (aubioRequirement && !this.isWindows) {
            await this.installBackendPythonPackages(backendPython, ['--no-build-isolation', aubioRequirement]);
        } else if (aubioRequirement && this.isWindows) {
            this.info('Skipping aubio on Windows; the musical-audio feature remains unavailable until its native dependencies are installed manually.');
        }

        fs.writeFileSync(tempRequirementsPath, filteredRequirementLines.join('\n'));

        try {
            await this.installBackendPythonPackages(backendPython, ['-r', tempRequirementsPath]);
        } finally {
            if (fs.existsSync(tempRequirementsPath)) {
                fs.unlinkSync(tempRequirementsPath);
            }
        }
    }

    parsePythonVersion(output) {
        const match = /Python\s+(\d+)\.(\d+)\.(\d+)/i.exec(output);
        if (!match) {
            return null;
        }

        return {
            major: Number(match[1]),
            minor: Number(match[2]),
            patch: Number(match[3]),
        };
    }

    formatPythonVersion(version) {
        return `Python ${version.major}.${version.minor}.${version.patch}`;
    }

    isSupportedPythonVersion(version) {
        return (
            version.major === 3
            && version.minor >= SUPPORTED_PYTHON_MIN_MINOR
            && version.minor <= SUPPORTED_PYTHON_MAX_MINOR
        );
    }

    getPythonCandidates() {
        const candidates = [];
        const seen = new Set();

        const addCandidate = (command, args, label) => {
            const key = `${command}::${args.join(' ')}`;
            if (seen.has(key)) {
                return;
            }

            seen.add(key);
            candidates.push({ command, args, label });
        };

        if (process.env.SMART_MIRROR_PYTHON) {
            addCandidate(process.env.SMART_MIRROR_PYTHON, [], 'SMART_MIRROR_PYTHON');
        }

        if (this.isWindows) {
            for (const minor of PREFERRED_PYTHON_MINORS) {
                addCandidate('py', [`-3.${minor}`], `py -3.${minor}`);
            }

            addCandidate('py', ['-3'], 'py -3');
            addCandidate('python', [], 'python');
            return candidates;
        }

        for (const minor of PREFERRED_PYTHON_MINORS) {
            addCandidate(`python3.${minor}`, [], `python3.${minor}`);
        }

        addCandidate('python3', [], 'python3');
        addCandidate('python', [], 'python');
        return candidates;
    }

    detectSupportedPython() {
        const unsupported = [];

        for (const candidate of this.getPythonCandidates()) {
            const result = this.runCommandCapture(candidate.command, [...candidate.args, '--version']);
            if (!result || result.status !== 0) {
                continue;
            }

            const version = this.parsePythonVersion(result.output);
            if (!version) {
                continue;
            }

            if (this.isSupportedPythonVersion(version)) {
                return {
                    ...candidate,
                    version,
                };
            }

            unsupported.push(`${candidate.label} (${this.formatPythonVersion(version)})`);
        }

        const unsupportedHint = unsupported.length > 0
            ? `Gefunden, aber nicht unterstuetzt: ${unsupported.join(', ')}.`
            : 'Es wurde kein passender Python-Interpreter gefunden.';

        const followUpHint = this.isWindows
            ? 'Unter Windows pruefe `py -0p` und `py -3.12 --version`, oder setze SMART_MIRROR_PYTHON auf den absoluten Pfad zu python.exe.'
            : 'Falls der Interpreter an einem ungewoehnlichen Ort liegt, setze SMART_MIRROR_PYTHON auf den passenden Python-Pfad.';

        throw new Error(
            `${unsupportedHint} Unterstuetzt sind Python 3.11 bis 3.13, bevorzugt wird Python 3.12. `
            + `${followUpHint}`
        );
    }

    getExistingBackendVenvVersion() {
        const pythonPath = this.getBackendPythonPath();
        if (!fs.existsSync(pythonPath)) {
            return null;
        }

        const result = this.runCommandCapture(pythonPath, ['--version']);
        if (!result || result.status !== 0) {
            return null;
        }

        const version = this.parsePythonVersion(result.output);
        if (!version) {
            return null;
        }

        return {
            pythonPath,
            version,
        };
    }

    async ensureNodeTooling() {
        this.log('Checking Node.js prerequisites...');

        if (!this.checkCommand('node')) {
            throw new Error('Node.js wurde nicht gefunden. Installiere Node.js von https://nodejs.org/.');
        }

        if (!this.checkCommand(this.getNpmCommand())) {
            throw new Error('NPM wurde nicht gefunden. Bitte installiere Node.js inklusive NPM.');
        }

        this.success('Node.js und NPM sind verfuegbar');
    }

    async installFrontendDependencies(alwaysInstall = true) {
        if (!fs.existsSync(this.frontendDir) || !fs.existsSync(path.join(this.frontendDir, 'package.json'))) {
            this.warning('Frontend-Verzeichnis wurde nicht gefunden. Frontend-Schritt wird uebersprungen.');
            return false;
        }

        const nodeModulesPath = path.join(this.frontendDir, 'node_modules');
        if (!alwaysInstall && fs.existsSync(nodeModulesPath)) {
            this.success('Frontend dependencies sind bereits vorhanden');
            return true;
        }

        const installMode = fs.existsSync(path.join(this.frontendDir, 'package-lock.json')) ? 'ci' : 'install';
        this.log(`Installing Frontend dependencies via npm ${installMode}...`);
        await this.execCommand(this.getNpmCommand(), [installMode], { cwd: this.frontendDir });
        this.success('Frontend dependencies installiert');
        return true;
    }

    async ensureBackendVenv() {
        const existingVenv = this.getExistingBackendVenvVersion();
        if (existingVenv && this.isSupportedPythonVersion(existingVenv.version)) {
            return existingVenv;
        }

        const pythonCandidate = this.detectSupportedPython();

        if (fs.existsSync(this.backendVenvDir)) {
            const reason = existingVenv
                ? `${this.formatPythonVersion(existingVenv.version)} ist fuer dieses Projekt nicht unterstuetzt`
                : 'die bestehende virtuelle Umgebung ist unvollstaendig';
            this.warning(`Backend/.venv wird neu erstellt, weil ${reason}.`);
            fs.rmSync(this.backendVenvDir, { recursive: true, force: true });
        }

        this.log(
            `Creating Backend virtual environment with ${pythonCandidate.label} `
            + `(${this.formatPythonVersion(pythonCandidate.version)})...`
        );
        await this.execCommand(
            pythonCandidate.command,
            [...pythonCandidate.args, '-m', 'venv', this.backendVenvDir],
            { cwd: this.rootDir }
        );

        return {
            pythonPath: this.getBackendPythonPath(),
            version: pythonCandidate.version,
        };
    }

    async ensureBackendDependencies(forceInstall = false) {
        if (!fs.existsSync(this.backendDir) || !fs.existsSync(this.backendRequirementsPath)) {
            this.warning('Backend-Verzeichnis oder requirements.txt wurde nicht gefunden.');
            return null;
        }

        const backendPython = await this.ensureBackendVenv();
        const requirementsHash = this.hashFile(this.backendRequirementsPath);
        const state = this.readBackendBootstrapState();
        const pythonVersion = this.formatPythonVersion(backendPython.version);

        if (
            !forceInstall
            && state
            && state.requirementsHash === requirementsHash
            && state.pythonVersion === pythonVersion
        ) {
            this.success(`Backend virtual environment ist bereit (${pythonVersion})`);
            return backendPython;
        }

        this.log(`Installing Backend dependencies with ${pythonVersion}...`);

        try {
            await this.installBackendPythonPackages(backendPython, ['--upgrade', 'pip', 'setuptools', 'wheel']);
            await this.installBackendRequirements(backendPython);
        } catch (error) {
            this.printBackendDependencyHelp();
            throw error;
        }

        this.writeBackendBootstrapState({
            installedAt: new Date().toISOString(),
            pythonVersion,
            requirementsHash,
        });
        this.success('Backend dependencies installiert');
        return backendPython;
    }

    printBackendDependencyHelp() {
        if (this.isWindows) {
            this.warning(
                'Falls pip auf nativen Paketen scheitert, installiere Python 3.12 inklusive Python Launcher und pruefe `py -3.12 --version`.'
            );
            return;
        }

        if (this.platform === 'linux') {
            this.warning(
                'Unter Linux koennen fuer aubio Systempakete fehlen, zum Beispiel python3.12-devel oder python3.12-dev, pkg-config, aubio-devel, ffmpeg-devel, libsndfile-devel und libsamplerate-devel.'
            );
            return;
        }

        this.warning('Falls die Installation scheitert, installiere einen unterstuetzten Python-Interpreter 3.11 oder 3.12 und pruefe die nativen Abhaengigkeiten der Audio-Pakete.');
    }

    async startFrontend() {
        await this.ensureNodeTooling();
        await this.installFrontendDependencies(false);

        this.log('Starting Frontend development server...');
        this.info('Frontend: http://localhost:5173');
        this.info('Press Ctrl+C to stop the server');
        await this.execCommand(this.getNpmCommand(), ['run', 'dev'], { cwd: this.frontendDir });
    }

    async startBackend() {
        const backendPython = await this.ensureBackendDependencies(false);
        if (!backendPython) {
            return;
        }

        this.log('Starting Backend development server...');
        this.info('API: http://localhost:8000/api/v1');
        this.info('WebSocket: ws://localhost:8000/ws');
        this.info('Press Ctrl+C to stop the server');
        await this.execCommand(backendPython.pythonPath, ['main.py'], {
            cwd: this.backendSrcDir,
            env: { PYTHONUNBUFFERED: '1' },
        });
    }

    printHelp() {
        console.log(`
${colors.cyan}Smart Mirror Setup Commands${colors.reset}

  node setup.js
    Installiert Frontend-Dependencies und erstellt bei Bedarf Backend/.venv.

  node setup.js --setup-frontend
    Installiert nur die Frontend-Dependencies.

  node setup.js --setup-backend
    Erstellt nur das Backend-Venv und installiert requirements.txt.

  node setup.js --dev-frontend
    Startet nur das Frontend.

  node setup.js --dev-backend
    Startet nur das Backend ohne manuelle Venv-Aktivierung.

  node setup.js --force
    Erzwingt beim Setup eine Neuinstallation der Backend-Dependencies.
`);
    }

    async run() {
        console.log(`
${colors.cyan}
======================================
  Smart Mirror Project Setup
======================================${colors.reset}
`);

        try {
            if (this.hasArg('--help', '-h')) {
                this.printHelp();
                return;
            }

            if (this.hasArg('--dev-backend')) {
                await this.startBackend();
                return;
            }

            if (this.hasArg('--dev', '--dev-frontend', '--start')) {
                await this.startFrontend();
                return;
            }

            if (this.hasArg('--setup-frontend')) {
                await this.ensureNodeTooling();
                await this.installFrontendDependencies(true);
                return;
            }

            if (this.hasArg('--setup-backend')) {
                await this.ensureBackendDependencies(this.hasArg('--force'));
                return;
            }

            await this.ensureNodeTooling();
            await this.installFrontendDependencies(true);
            await this.ensureBackendDependencies(this.hasArg('--force'));

            console.log(`
${colors.green}
======================================
  Setup Complete!
======================================${colors.reset}

${colors.yellow}Quick commands:${colors.reset}
  ${colors.blue}-${colors.reset} Setup everything: ${colors.magenta}npm run setup${colors.reset}
  ${colors.blue}-${colors.reset} Setup only Backend: ${colors.magenta}npm run setup:backend${colors.reset}
  ${colors.blue}-${colors.reset} Start Frontend: ${colors.magenta}npm run dev${colors.reset}
  ${colors.blue}-${colors.reset} Start Backend: ${colors.magenta}npm run dev:backend${colors.reset}
`);
        } catch (error) {
            this.error(`Setup failed: ${error.message}`);
            process.exit(1);
        }
    }
}

const setup = new SmartMirrorSetup();
setup.run().catch((error) => {
    console.error(error);
    process.exit(1);
});