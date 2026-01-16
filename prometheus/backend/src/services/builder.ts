import { EventEmitter } from 'events';
import { spawn, ChildProcess } from 'child_process';
import path from 'path';
import { BuilderResponse } from '../types';

export class BuilderService extends EventEmitter {
    private sessionId: string;
    private conversationHistory: Array<{ role: string; content: string }> = [];
    private currentState: any = {};

    constructor(sessionId: string) {
        super();
        this.sessionId = sessionId;
    }

    async sendMessage(message: string): Promise<BuilderResponse> {
        this.conversationHistory.push({ role: 'user', content: message });

        return new Promise((resolve, reject) => {
            const pythonScript = path.join(__dirname, '../../../scripts/builder.py');
            const pythonBin = '/home/prometheus/leibniz_agent/TARA-MICROSERVICE/venv/bin/python3';

            // Spawn Python process
            const pythonProcess = spawn(pythonBin, [pythonScript], {
                env: {
                    ...process.env,
                    GEMINI_API_KEY: process.env.GEMINI_API_KEY || 'AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk'
                }
            });

            let outputBuffer = '';
            let errorBuffer = '';

            pythonProcess.stdout.on('data', (data) => {
                outputBuffer += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                errorBuffer += data.toString();
                console.error('Builder.py stderr:', data.toString());
            });

            pythonProcess.on('close', (code) => {
                if (code !== 0) {
                    console.error('Builder.py error:', errorBuffer);
                    // Return fallback response
                    resolve({
                        identity: { name: 'Agent' },
                        knowledge: { orgName: 'Organization' },
                        missing_fields: [],
                        next_question: 'DONE',
                        completeness_score: 100
                    });
                    return;
                }

                try {
                    // Parse JSON output from builder.py
                    const lines = outputBuffer.split('\n').filter(l => l.trim());
                    let response: BuilderResponse | null = null;

                    // Find the JSON response line
                    for (const line of lines) {
                        if (line.startsWith('{') && line.includes('identity')) {
                            response = JSON.parse(line);
                            break;
                        }
                    }

                    if (!response) {
                        throw new Error('No valid JSON response from builder.py');
                    }

                    this.currentState = response;
                    resolve(response);
                } catch (error) {
                    console.error('Failed to parse builder.py output:', error);
                    resolve({
                        identity: { name: 'Agent' },
                        knowledge: { orgName: 'Organization' },
                        missing_fields: [],
                        next_question: 'DONE',
                        completeness_score: 100
                    });
                }
            });

            // Send message to Python process via stdin
            pythonProcess.stdin.write(JSON.stringify({
                message,
                history: this.conversationHistory
            }) + '\n');
            pythonProcess.stdin.end();
        });
    }

    getState() {
        return this.currentState;
    }
}
