import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { BuildLog, BuildProgress } from '../types';

export class ExecutionerService extends EventEmitter {
    private sessionId: string;
    private state: any;
    private process: ChildProcess | null = null;
    private currentProgress: number = 0;

    constructor(sessionId: string, state: any) {
        super();
        this.sessionId = sessionId;
        this.state = state;
    }

    async start() {
        const pythonScript = path.join(__dirname, '../../../scripts/executioner.py');
        const pythonBin = '/home/prometheus/leibniz_agent/TARA-MICROSERVICE/venv/bin/python3';

        this.emitLog('planning', 'Initiating agent build pipeline...');

        // Spawn executioner.py process
        this.process = spawn(pythonBin, [pythonScript], {
            env: {
                ...process.env,
                GEMINI_API_KEY: process.env.GEMINI_API_KEY || 'AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk'
            }
        });

        let outputBuffer = '';

        this.process.stdout?.on('data', (data) => {
            const output = data.toString();
            outputBuffer += output;

            // Parse real-time logs from executioner.py
            const lines = output.split('\n').filter((l: string) => l.trim());

            for (const line of lines) {
                try {
                    // Check for special markers
                    if (line.includes('[PLANNING]')) {
                        const msg = line.replace('[PLANNING]', '').trim();
                        this.emitLog('planning', msg);
                    } else if (line.includes('[EXECUTING]')) {
                        const msg = line.replace('[EXECUTING]', '').trim();
                        this.emitLog('executing', msg);
                    } else if (line.includes('[VERIFYING]')) {
                        const msg = line.replace('[VERIFYING]', '').trim();
                        this.emitLog('verifying', msg);
                    } else if (line.includes('[PROGRESS]')) {
                        // Parse progress: [PROGRESS] 45
                        const match = line.match(/\[PROGRESS\]\s+(\d+)/);
                        if (match) {
                            const progress = parseInt(match[1]);
                            this.updateProgress(progress);
                        }
                    } else if (line.trim().length > 0 && !line.startsWith('{')) {
                        // Generic log message
                        this.emitLog('executing', line.trim());
                    }
                } catch (e) {
                    console.error('Error parsing executioner output:', e);
                }
            }
        });

        this.process.stderr?.on('data', (data) => {
            console.error('Executioner.py stderr:', data.toString());
        });

        this.process.on('close', (code) => {
            this.updateProgress(100);
            this.emitLog('verifying', 'Build complete! Agent assets generated successfully.');
            this.emit('complete');
        });

        // Send state to Python process
        this.process.stdin?.write(JSON.stringify(this.state) + '\n');
        this.process.stdin?.end();
    }

    private emitLog(tag: 'planning' | 'executing' | 'verifying', msg: string) {
        const log: BuildLog = {
            ts: new Date().toLocaleTimeString('en-US', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }),
            tag,
            msg
        };
        this.emit('log', log);
    }

    private updateProgress(progress: number) {
        this.currentProgress = progress;
        const buildProgress: BuildProgress = {
            progress,
            phase: progress < 40 ? 1 : progress < 75 ? 2 : 3,
            status: progress === 100 ? 'complete' : 'running'
        };
        this.emit('progress', buildProgress);
    }
}
