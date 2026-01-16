import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useBuildStore } from '../store/buildStore';
import { Orb } from './ui/orb';
import { Message, MessageContent, MessageAvatar, Conversation, ConversationContent } from './ui/message';
import BoxLoader from './ui/box-loader';

export default function DeploySheet() {
    const {
        showDeploySheet,
        setShowDeploySheet,
        missionName,
        deployedAgentId,
        agentState,
        setAgentState,
        builderWidth,
        setBuilderWidth
    } = useBuildStore();

    const [isDragging, setIsDragging] = useState(false);
    const [isOrbLoading, setIsOrbLoading] = useState(true);
    const [isCallActive, setIsCallActive] = useState(false);
    const [transcript, setTranscript] = useState<{ role: 'user' | 'agent', text: string }[]>([]);
    const [callDuration, setCallDuration] = useState(0);
    const dragRef = useRef<HTMLDivElement>(null);
    const transcriptEndRef = useRef<HTMLDivElement>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const audioContextRef = useRef<AudioContext | null>(null);
    const audioQueueRef = useRef<string[]>([]);
    const isPlayingRef = useRef(false);
    const processorRef = useRef<ScriptProcessorNode | null>(null);
    const streamRef = useRef<MediaStream | null>(null);
    const callTimerRef = useRef<number | null>(null);

    // Auto-scroll to bottom of transcript
    useEffect(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [transcript]);

    // Initial Simulated Orb loading
    useEffect(() => {
        if (showDeploySheet) {
            setIsOrbLoading(true);
            const timer = setTimeout(() => setIsOrbLoading(false), 1500);
            return () => clearTimeout(timer);
        }
    }, [showDeploySheet]);

    // Call duration timer
    useEffect(() => {
        if (isCallActive) {
            callTimerRef.current = window.setInterval(() => {
                setCallDuration(prev => prev + 1);
            }, 1000);
        } else {
            if (callTimerRef.current) window.clearInterval(callTimerRef.current);
            setCallDuration(0);
        }
        return () => {
            if (callTimerRef.current) window.clearInterval(callTimerRef.current);
        };
    }, [isCallActive]);

    // Handle drag resize
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging) return;
            const newWidth = window.innerWidth - e.clientX;
            const maxWidth = Math.max(700, window.innerWidth * 0.5);
            setBuilderWidth(Math.max(420, Math.min(maxWidth, newWidth)));
        };

        const handleMouseUp = () => setIsDragging(false);

        if (isDragging) {
            document.addEventListener('mousemove', handleMouseMove);
            document.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
        };
    }, [isDragging, setBuilderWidth]);

    const formatDuration = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    const playNextAudio = async () => {
        if (isPlayingRef.current || audioQueueRef.current.length === 0 || !audioContextRef.current) return;

        isPlayingRef.current = true;
        setAgentState('talking');

        try {
            const chunkBase64 = audioQueueRef.current.shift();
            if (!chunkBase64) {
                isPlayingRef.current = false;
                return;
            }

            const binaryString = window.atob(chunkBase64);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }

            const numSamples = bytes.length / 2;
            const pcm16 = new Int16Array(bytes.buffer);
            const float32 = new Float32Array(numSamples);

            for (let i = 0; i < numSamples; i++) {
                float32[i] = pcm16[i] / 32768.0;
            }

            const sampleRate = 16000;
            const audioBuffer = audioContextRef.current.createBuffer(1, numSamples, sampleRate);
            audioBuffer.copyToChannel(float32, 0);

            const source = audioContextRef.current.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(audioContextRef.current.destination);

            source.onended = () => {
                isPlayingRef.current = false;
                if (audioQueueRef.current.length === 0) {
                    setAgentState('listening');
                }
                playNextAudio();
            };

            source.start(0);
            console.log(`[Audio] Playing chunk: ${numSamples} samples`);

        } catch (error) {
            console.error("[Audio] Playback error:", error);
            isPlayingRef.current = false;
            setAgentState('listening');
            playNextAudio();
        }
    };

    const handleStartCall = async () => {
        if (!deployedAgentId) return;

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            streamRef.current = stream;

            const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 16000 });
            audioContextRef.current = audioContext;

            const source = audioContext.createMediaStreamSource(stream);
            const processor = audioContext.createScriptProcessor(4096, 1, 1);
            processorRef.current = processor;

            source.connect(processor);
            processor.connect(audioContext.destination);

            const wsUrl = `ws://127.0.0.1:8099/v1/convai/${deployedAgentId}`;
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('Connected to Agent Relay');
                setIsCallActive(true);
                setAgentState('listening');
                setTranscript([]);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[WS] Received event type:', data.type);

                    if (data.type === 'audio') {
                        if (data.audio_event?.audio_base_64) {
                            audioQueueRef.current.push(data.audio_event.audio_base_64);
                            playNextAudio();
                        }
                    } else if (data.type === 'user_transcript') {
                        const text = data.user_transcription_event?.user_transcript || data.user_transcript_event?.user_transcript || '';
                        if (text) {
                            setTranscript(prev => [...prev, { role: 'user', text }]);
                        }
                    } else if (data.type === 'agent_response') {
                        const text = data.agent_response_event?.agent_response || '';
                        if (text) {
                            setTranscript(prev => [...prev, { role: 'agent', text }]);
                        }
                    } else if (data.type === 'interruption') {
                        audioQueueRef.current = [];
                        isPlayingRef.current = false;
                        setAgentState('listening');
                    }
                } catch (parseError) {
                    console.error('[WS] Failed to parse message:', parseError);
                }
            };

            ws.onerror = (e) => {
                console.error("WebSocket Error:", e);
                setAgentState(null);
                setIsCallActive(false);
            };

            ws.onclose = () => {
                console.log('Disconnected from Agent');
                setAgentState(null);
                setIsCallActive(false);
            };

            processor.onaudioprocess = (e) => {
                if (ws.readyState === WebSocket.OPEN) {
                    const inputData = e.inputBuffer.getChannelData(0);
                    const pcmData = new Int16Array(inputData.length);
                    for (let i = 0; i < inputData.length; i++) {
                        pcmData[i] = Math.max(-1, Math.min(1, inputData[i])) * 0x7FFF;
                    }
                    const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcmData.buffer)));
                    ws.send(JSON.stringify({ user_audio_chunk: base64Audio }));
                }
            };

        } catch (err) {
            console.error("Failed to start call:", err);
            alert("Could not access microphone. Please allow permissions.");
        }
    };

    const handleEndCall = () => {
        if (wsRef.current) wsRef.current.close();
        if (streamRef.current) streamRef.current.getTracks().forEach(track => track.stop());
        if (processorRef.current) processorRef.current.disconnect();
        if (audioContextRef.current) audioContextRef.current.close();

        wsRef.current = null;
        streamRef.current = null;
        processorRef.current = null;
        audioContextRef.current = null;
        audioQueueRef.current = [];
        isPlayingRef.current = false;

        setIsCallActive(false);
        setAgentState(null);
    };

    // Map agent state for orb (orb uses 'thinking' but we use 'idle')
    const orbAgentState = agentState === 'idle' ? null : agentState;

    return (
        <AnimatePresence>
            {showDeploySheet && (
                <motion.div
                    initial={{ x: '100%', opacity: 0 }}
                    animate={{ x: 0, opacity: 1 }}
                    exit={{ x: '100%', opacity: 0 }}
                    transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                    style={{
                        position: 'absolute',
                        top: 0,
                        right: 0,
                        bottom: 0,
                        width: `${builderWidth}px`,
                        background: '#FFFFFF',
                        borderLeft: '1px solid #E5E5E5',
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden',
                        zIndex: 200,
                        boxShadow: '-12px 0 40px rgba(0, 0, 0, 0.08)'
                    }}
                >
                    {/* Drag Handle */}
                    <div
                        ref={dragRef}
                        onMouseDown={(e) => { e.preventDefault(); setIsDragging(true); }}
                        style={{
                            position: 'absolute',
                            left: 0,
                            top: 0,
                            bottom: 0,
                            width: '6px',
                            cursor: 'ew-resize',
                            background: isDragging ? '#CADCFC' : 'transparent',
                            transition: 'background 0.2s',
                            zIndex: 10
                        }}
                    />

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* HEADER */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    <div style={{ background: '#FAFAFA', borderBottom: '1px solid #E5E5E5' }}>
                        <div style={{
                            padding: '16px 24px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                        }}>
                            <div>
                                <div style={{
                                    fontSize: '11px',
                                    fontWeight: '600',
                                    color: '#9CA3AF',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.1em',
                                    marginBottom: '4px'
                                }}>
                                    TEST FLIGHT
                                </div>
                                <div style={{
                                    fontSize: '18px',
                                    fontWeight: '700',
                                    color: '#1F2937',
                                    letterSpacing: '-0.02em'
                                }}>
                                    {missionName || 'Agent'}
                                </div>
                            </div>

                            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                                {isCallActive && (
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '6px 12px',
                                        background: '#DEF7EC',
                                        borderRadius: '20px',
                                        fontFamily: 'JetBrains Mono, monospace',
                                        fontSize: '14px',
                                        fontWeight: '600',
                                        color: '#15803D'
                                    }}>
                                        <div style={{
                                            width: '8px',
                                            height: '8px',
                                            borderRadius: '50%',
                                            background: '#22C55E',
                                            animation: 'pulse 1.5s infinite'
                                        }} />
                                        {formatDuration(callDuration)}
                                    </div>
                                )}
                                <button
                                    onClick={() => setShowDeploySheet(false)}
                                    style={{
                                        border: '1px solid #E5E5E5',
                                        background: 'white',
                                        color: '#6B7280',
                                        width: '36px',
                                        height: '36px',
                                        borderRadius: '8px',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}
                                >
                                    <span className="material-icons-round" style={{ fontSize: '20px' }}>close</span>
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* ORB SECTION */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    <div style={{
                        padding: '24px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        gap: '24px',
                        borderBottom: '1px solid #F3F4F6'
                    }}>
                        {/* Agent ID Badge */}
                        <div style={{
                            padding: '6px 14px',
                            background: '#F9FAFB',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontFamily: 'JetBrains Mono, monospace',
                            color: '#9CA3AF',
                            border: '1px solid #F3F4F6'
                        }}>
                            {deployedAgentId ? `ID: ${deployedAgentId.substring(0, 24)}...` : 'No agent deployed'}
                        </div>

                        {/* Official ElevenLabs Blue Orb */}
                        <div style={{
                            width: '200px',
                            height: '200px',
                            position: 'relative'
                        }}>
                            <AnimatePresence mode="wait">
                                {isOrbLoading ? (
                                    <motion.div
                                        key="loader"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        style={{
                                            width: '100%',
                                            height: '100%',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            flexDirection: 'column'
                                        }}
                                    >
                                        <BoxLoader />
                                        <p style={{ color: '#9CA3AF', fontSize: '12px', marginTop: '16px' }}>
                                            Initializing...
                                        </p>
                                    </motion.div>
                                ) : (
                                    <motion.div
                                        key="orb"
                                        initial={{ scale: 0.8, opacity: 0 }}
                                        animate={{ scale: 1, opacity: 1 }}
                                        transition={{ type: 'spring', damping: 15 }}
                                        style={{ width: '100%', height: '100%' }}
                                    >
                                        {/* Official ElevenLabs Blue Colors */}
                                        <Orb
                                            agentState={orbAgentState}
                                            colors={["#CADCFC", "#A0B9D1"]}
                                        />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>

                        {/* Controls */}
                        <div style={{ width: '100%', maxWidth: '280px' }}>
                            {!isCallActive ? (
                                <button
                                    onClick={handleStartCall}
                                    disabled={!deployedAgentId}
                                    style={{
                                        width: '100%',
                                        padding: '16px',
                                        background: deployedAgentId
                                            ? 'linear-gradient(135deg, #CADCFC, #A0B9D1)'
                                            : '#E5E5E5',
                                        border: 'none',
                                        borderRadius: '12px',
                                        color: deployedAgentId ? '#1F2937' : '#9CA3AF',
                                        fontSize: '15px',
                                        fontWeight: '600',
                                        cursor: deployedAgentId ? 'pointer' : 'not-allowed',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px',
                                        boxShadow: deployedAgentId ? '0 4px 14px rgba(160, 185, 209, 0.4)' : 'none',
                                        transition: 'all 0.2s ease'
                                    }}
                                >
                                    <span className="material-icons-round" style={{ fontSize: '20px' }}>mic</span>
                                    Start Conversation
                                </button>
                            ) : (
                                <button
                                    onClick={handleEndCall}
                                    style={{
                                        width: '100%',
                                        padding: '16px',
                                        background: '#1F2937',
                                        border: 'none',
                                        borderRadius: '12px',
                                        color: 'white',
                                        fontSize: '15px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '10px'
                                    }}
                                >
                                    <span className="material-icons-round" style={{ fontSize: '20px', color: '#EF4444' }}>call_end</span>
                                    End Session
                                </button>
                            )}
                        </div>
                    </div>

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* CONVERSATION AREA */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    <div style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden'
                    }}>
                        <div style={{
                            padding: '12px 24px',
                            borderBottom: '1px solid #F3F4F6',
                            fontSize: '11px',
                            fontWeight: '600',
                            color: '#9CA3AF',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em'
                        }}>
                            Conversation
                        </div>

                        <Conversation>
                            <ConversationContent style={{
                                flex: 1,
                                overflowY: 'auto',
                                padding: '20px 24px',
                                gap: '16px'
                            }}>
                                {transcript.length === 0 && (
                                    <div style={{
                                        flex: 1,
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#D1D5DB',
                                        fontSize: '14px',
                                        textAlign: 'center',
                                        padding: '40px'
                                    }}>
                                        {isCallActive ? 'Listening...' : 'Start a conversation to begin'}
                                    </div>
                                )}

                                {transcript.map((msg, i) => (
                                    <Message key={i} from={msg.role === 'user' ? 'user' : 'assistant'}>
                                        <MessageAvatar
                                            name={msg.role === 'user' ? 'You' : missionName || 'AI'}
                                            isAgent={msg.role === 'agent'}
                                        />
                                        <MessageContent
                                            variant="contained"
                                            style={{
                                                background: msg.role === 'user'
                                                    ? '#F3F4F6'
                                                    : 'linear-gradient(135deg, rgba(202, 220, 252, 0.3), rgba(160, 185, 209, 0.2))',
                                                border: msg.role === 'user'
                                                    ? '1px solid #E5E5E5'
                                                    : '1px solid rgba(160, 185, 209, 0.3)',
                                                color: '#374151'
                                            }}
                                        >
                                            {msg.text}
                                        </MessageContent>
                                    </Message>
                                ))}
                                <div ref={transcriptEndRef} />
                            </ConversationContent>
                        </Conversation>
                    </div>

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* FOOTER */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    <div style={{
                        padding: '12px 24px',
                        background: '#FAFAFA',
                        borderTop: '1px solid #E5E5E5',
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: '11px',
                        color: '#9CA3AF'
                    }}>
                        <div style={{ display: 'flex', gap: '16px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span className="material-icons-round" style={{ fontSize: '14px' }}>memory</span>
                                CONV-AI v1.0
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span className="material-icons-round" style={{ fontSize: '14px' }}>speed</span>
                                16kHz
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <div style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                background: isCallActive ? '#22C55E' : '#D1D5DB'
                            }} />
                            {isCallActive ? 'Connected' : 'Ready'}
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
