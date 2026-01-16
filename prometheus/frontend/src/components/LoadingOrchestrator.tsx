import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface LoadingOrchestratorProps {
    isActive: boolean;
}

export default function LoadingOrchestrator({ isActive }: LoadingOrchestratorProps) {
    const [scene, setScene] = useState(1);
    const [scanCount, setScanCount] = useState(0);

    useEffect(() => {
        if (!isActive) {
            setScene(1);
            setScanCount(0);
            return;
        }

        // Scene progression
        const sceneTimer = setTimeout(() => {
            if (scene < 3) setScene(scene + 1);
        }, scene === 1 ? 3000 : 5000);

        return () => clearTimeout(sceneTimer);
    }, [isActive, scene]);

    useEffect(() => {
        if (!isActive || scene !== 2) return;

        // Voice scanning counter animation
        const interval = setInterval(() => {
            setScanCount(prev => {
                if (prev >= 10000) return 10000;
                return prev + Math.floor(Math.random() * 500) + 100;
            });
        }, 50);

        return () => clearInterval(interval);
    }, [isActive, scene]);

    if (!isActive) return null;

    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            background: '#000',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            overflow: 'hidden'
        }}>
            {/* Grid Background */}
            <div style={{
                position: 'absolute',
                inset: 0,
                backgroundImage: `
                    linear-gradient(rgba(255, 77, 0, 0.1) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255, 77, 0, 0.1) 1px, transparent 1px)
                `,
                backgroundSize: '40px 40px',
                opacity: 0.3
            }} />

            <AnimatePresence mode="wait">
                {scene === 1 && <Scene1 key="scene1" />}
                {scene === 2 && <Scene2 key="scene2" scanCount={scanCount} />}
                {scene === 3 && <Scene3 key="scene3" />}
            </AnimatePresence>
        </div>
    );
}

function Scene1() {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '60px'
            }}
        >
            {/* Title */}
            <motion.div
                initial={{ y: 50, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2, type: 'spring', damping: 20 }}
                style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '14px',
                    letterSpacing: '0.4em',
                    color: 'var(--accent)',
                    fontWeight: '800',
                    textTransform: 'uppercase'
                }}
            >
                EXTRACTING AGENT DNA...
            </motion.div>

            {/* Pulsing Grid Nodes */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(5, 1fr)',
                gap: '20px'
            }}>
                {Array.from({ length: 15 }).map((_, i) => (
                    <motion.div
                        key={i}
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{
                            scale: [0, 1, 0.8, 1],
                            opacity: [0, 1, 0.6, 1]
                        }}
                        transition={{
                            delay: i * 0.05,
                            duration: 0.8,
                            repeat: Infinity,
                            repeatDelay: 2
                        }}
                        style={{
                            width: '12px',
                            height: '12px',
                            background: i % 3 === 0 ? 'var(--accent)' : '#444',
                            borderRadius: '2px',
                            boxShadow: i % 3 === 0 ? '0 0 20px var(--accent)' : 'none'
                        }}
                    />
                ))}
            </div>

            {/* Progress Bars */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', minWidth: '400px' }}>
                {['ORG_NAME', 'AGENT_NAME', 'PERSONA_VIBE', 'VOICE_PARAMS'].map((field, i) => (
                    <div key={field} style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span style={{
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: '10px',
                            color: '#666',
                            width: '120px',
                            textAlign: 'right'
                        }}>{field}</span>
                        <div style={{
                            flex: 1,
                            height: '3px',
                            background: '#222',
                            position: 'relative',
                            overflow: 'hidden'
                        }}>
                            <motion.div
                                initial={{ width: '0%' }}
                                animate={{ width: '100%' }}
                                transition={{ delay: i * 0.3, duration: 0.8, ease: 'easeOut' }}
                                style={{
                                    height: '100%',
                                    background: 'var(--accent)',
                                    boxShadow: '0 0 10px var(--accent)'
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </motion.div>
    );
}

function Scene2({ scanCount }: { scanCount: number }) {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '80px'
            }}
        >
            {/* Title with Counter */}
            <div style={{ textAlign: 'center' }}>
                <motion.div
                    initial={{ y: 30, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                    style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: '14px',
                        letterSpacing: '0.4em',
                        color: 'var(--accent)',
                        fontWeight: '800',
                        textTransform: 'uppercase',
                        marginBottom: '20px'
                    }}
                >
                    SEARCHING VOICE PROFILES...
                </motion.div>
                <motion.div
                    style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: '48px',
                        color: '#fff',
                        fontWeight: '800'
                    }}
                >
                    {scanCount.toLocaleString()}
                </motion.div>
            </div>

            {/* Waveform Visualization */}
            <div style={{ display: 'flex', gap: '4px', alignItems: 'flex-end', height: '100px' }}>
                {Array.from({ length: 40 }).map((_, i) => (
                    <motion.div
                        key={i}
                        animate={{
                            height: [
                                `${20 + Math.random() * 60}%`,
                                `${40 + Math.random() * 40}%`,
                                `${20 + Math.random() * 60}%`
                            ]
                        }}
                        transition={{
                            duration: 0.8,
                            repeat: Infinity,
                            delay: i * 0.02,
                            ease: 'easeInOut'
                        }}
                        style={{
                            width: '8px',
                            background: i % 5 === 0 ? 'var(--accent)' : '#333',
                            borderRadius: '2px',
                            boxShadow: i % 5 === 0 ? '0 0 10px var(--accent)' : 'none'
                        }}
                    />
                ))}
            </div>

            {/* Scanning Text */}
            <motion.div
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 2, repeat: Infinity }}
                style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '11px',
                    color: '#666',
                    letterSpacing: '0.2em'
                }}
            >
                ANALYZING VOCAL PATTERNS...
            </motion.div>
        </motion.div>
    );
}

function Scene3() {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
            style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: '60px'
            }}
        >
            {/* Title */}
            <motion.div
                initial={{ y: 30, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                transition={{ delay: 0.2 }}
                style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '14px',
                    letterSpacing: '0.4em',
                    color: 'var(--accent)',
                    fontWeight: '800',
                    textTransform: 'uppercase'
                }}
            >
                COMPILING CONVERSATIONAL LOGIC...
            </motion.div>

            {/* Geometric Morphing Shapes */}
            <div style={{ position: 'relative', width: '200px', height: '200px' }}>
                {[0, 1, 2, 3].map((i) => (
                    <motion.div
                        key={i}
                        animate={{
                            rotate: [0, 360],
                            scale: [1, 1.2, 1],
                            opacity: [0.2, 0.6, 0.2]
                        }}
                        transition={{
                            duration: 4,
                            repeat: Infinity,
                            delay: i * 0.5,
                            ease: 'linear'
                        }}
                        style={{
                            position: 'absolute',
                            inset: `${i * 20}px`,
                            border: '2px solid var(--accent)',
                            borderRadius: i % 2 === 0 ? '50%' : '0%',
                            opacity: 0.3
                        }}
                    />
                ))}

                <motion.div
                    animate={{
                        rotate: [0, -360]
                    }}
                    transition={{
                        duration: 6,
                        repeat: Infinity,
                        ease: 'linear'
                    }}
                    style={{
                        position: 'absolute',
                        inset: '40px',
                        border: '3px solid #fff',
                        borderRadius: '4px',
                        boxShadow: '0 0 30px rgba(255, 77, 0, 0.5)'
                    }}
                />
            </div>
        </motion.div>
    );
}
