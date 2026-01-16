/**
 * PetalOrb - A 2D animated orb with petal/flower-like segments
 * Inspired by ElevenLabs agent orb visualization
 * Uses orange/gray color theme to match the app
 */
import { motion } from 'framer-motion';

export type AgentState = 'idle' | 'listening' | 'talking' | null;

interface PetalOrbProps {
    agentState: AgentState;
    size?: number;
}

export function PetalOrb({ agentState, size = 200 }: PetalOrbProps) {
    const numPetals = 6;
    const petals = Array.from({ length: numPetals });

    // Color based on state - orange theme
    const getColors = () => {
        switch (agentState) {
            case 'listening':
                return { primary: '#FF4D00', secondary: '#FF8C42', glow: 'rgba(255, 77, 0, 0.3)' };
            case 'talking':
                return { primary: '#FF6B2C', secondary: '#FFB347', glow: 'rgba(255, 107, 44, 0.4)' };
            case 'idle':
            default:
                return { primary: '#9CA3AF', secondary: '#D1D5DB', glow: 'rgba(156, 163, 175, 0.2)' };
        }
    };

    const colors = getColors();

    // Animation variants for petals
    const getPetalAnimation = (index: number) => {
        const baseDelay = index * 0.1;

        if (agentState === 'talking') {
            // Rapid pulsing when talking
            return {
                scaleX: [1, 0.6, 1.1, 0.7, 1],
                scaleY: [1, 1.3, 0.8, 1.2, 1],
                rotate: [0, 5, -3, 2, 0],
                transition: {
                    duration: 0.4,
                    repeat: Infinity,
                    delay: baseDelay,
                    ease: 'easeInOut'
                }
            };
        } else if (agentState === 'listening') {
            // Gentle breathing when listening
            return {
                scaleX: [1, 0.9, 1.05, 0.95, 1],
                scaleY: [1, 1.1, 0.95, 1.08, 1],
                transition: {
                    duration: 2,
                    repeat: Infinity,
                    delay: baseDelay,
                    ease: 'easeInOut'
                }
            };
        } else {
            // Idle - very subtle pulse
            return {
                scaleX: [1, 0.98, 1.02, 1],
                scaleY: [1, 1.02, 0.98, 1],
                transition: {
                    duration: 3,
                    repeat: Infinity,
                    delay: baseDelay,
                    ease: 'easeInOut'
                }
            };
        }
    };

    return (
        <div style={{
            width: size,
            height: size,
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        }}>
            {/* Outer glow ring */}
            <motion.div
                animate={{
                    boxShadow: agentState === 'talking'
                        ? `0 0 60px ${colors.glow}, inset 0 0 30px ${colors.glow}`
                        : agentState === 'listening'
                            ? `0 0 40px ${colors.glow}, inset 0 0 20px ${colors.glow}`
                            : `0 0 20px ${colors.glow}`
                }}
                transition={{ duration: 0.3 }}
                style={{
                    position: 'absolute',
                    width: size,
                    height: size,
                    borderRadius: '50%',
                    background: 'radial-gradient(circle, rgba(255,255,255,0.9) 0%, #F3F4F6 100%)',
                    border: '1px solid #E5E5E5'
                }}
            />

            {/* Petals container */}
            <svg
                width={size * 0.8}
                height={size * 0.8}
                viewBox="0 0 100 100"
                style={{ position: 'relative', zIndex: 1 }}
            >
                <defs>
                    <linearGradient id="petalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor={colors.primary} />
                        <stop offset="100%" stopColor={colors.secondary} />
                    </linearGradient>
                    <filter id="petalShadow" x="-20%" y="-20%" width="140%" height="140%">
                        <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor={colors.primary} floodOpacity="0.3" />
                    </filter>
                </defs>

                <g transform="translate(50, 50)">
                    {petals.map((_, index) => {
                        const angle = (360 / numPetals) * index;
                        return (
                            <motion.ellipse
                                key={index}
                                cx="0"
                                cy="-20"
                                rx="18"
                                ry="28"
                                fill="url(#petalGradient)"
                                filter="url(#petalShadow)"
                                style={{
                                    transformOrigin: '0 0',
                                    opacity: 0.85
                                }}
                                initial={{ rotate: angle }}
                                animate={{
                                    rotate: angle,
                                    ...getPetalAnimation(index)
                                }}
                            />
                        );
                    })}
                </g>

                {/* Center circle */}
                <motion.circle
                    cx="50"
                    cy="50"
                    r="12"
                    fill={colors.primary}
                    animate={{
                        scale: agentState === 'talking' ? [1, 1.2, 0.9, 1.1, 1] : [1, 1.05, 1],
                        opacity: agentState ? 1 : 0.7
                    }}
                    transition={{
                        duration: agentState === 'talking' ? 0.5 : 2,
                        repeat: Infinity,
                        ease: 'easeInOut'
                    }}
                    style={{ filter: 'url(#petalShadow)' }}
                />
            </svg>

            {/* State indicator */}
            <motion.div
                animate={{
                    scale: agentState === 'talking' ? [1, 1.3, 1] : [1, 1.1, 1]
                }}
                transition={{
                    duration: agentState === 'talking' ? 0.3 : 1.5,
                    repeat: Infinity
                }}
                style={{
                    position: 'absolute',
                    bottom: 0,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    padding: '4px 12px',
                    background: colors.primary,
                    borderRadius: '12px',
                    fontSize: '10px',
                    fontWeight: '700',
                    color: 'white',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px'
                }}
            >
                {agentState || 'Ready'}
            </motion.div>
        </div>
    );
}

export default PetalOrb;
