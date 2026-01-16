import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import cors from 'cors';
import { BuilderService } from './services/builder';
import { ExecutionerService } from './services/executioner';

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: 'http://localhost:5173',
        methods: ['GET', 'POST']
    }
});

app.use(cors());
app.use(express.json());

// Session storage
const sessions = new Map<string, any>();

// REST API Routes
app.post('/api/chat', async (req, res) => {
    try {
        const { message, session_id } = req.body;

        if (!sessions.has(session_id)) {
            sessions.set(session_id, {
                builder: new BuilderService(session_id),
                state: {}
            });
        }

        const session = sessions.get(session_id);
        console.log(`[CHAT] Session: ${session_id} | Message: ${message}`);
        const response = await session.builder.sendMessage(message);
        console.log(`[CHAT] Response: score=${response.completeness_score} next=${response.next_question}`);
        session.state = response;

        res.json(response);
    } catch (error) {
        console.error('❌ Chat error:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// WebSocket Connection
io.on('connection', (socket) => {
    console.log('✅ Client connected:', socket.id);

    socket.on('build:start', async (data) => {
        const { session_id } = data;

        if (!sessions.has(session_id)) {
            socket.emit('build:error', { message: 'No session found' });
            return;
        }

        const session = sessions.get(session_id);
        const executioner = new ExecutionerService(session_id, session.state);

        // Listen to executioner events and forward to client
        executioner.on('log', (log) => {
            socket.emit('build:log', log);
        });

        executioner.on('progress', (progress) => {
            socket.emit('build:progress', progress);
        });

        executioner.on('complete', () => {
            socket.emit('build:complete', { session_id });
        });

        executioner.on('error', (error) => {
            socket.emit('build:error', error);
        });

        await executioner.start();
    });

    socket.on('disconnect', () => {
        console.log('❌ Client disconnected:', socket.id);
    });
});

const PORT = process.env.PORT || 3001;

httpServer.listen(PORT, () => {
    console.log('🔥 PROMETHEUS Backend');
    console.log(`   Server: http://localhost:${PORT}`);
    console.log(`   WebSocket: ws://localhost:${PORT}`);
});
