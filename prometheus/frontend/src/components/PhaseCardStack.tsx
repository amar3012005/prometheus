import { motion, AnimatePresence } from 'framer-motion';
import { BUILD_PHASES, PhaseStatus } from '../store/buildStore';

interface PhaseCardStackProps {
    phaseStatuses: PhaseStatus[];
}

const positionStyles = [
    { scale: 1, y: 0, zIndex: 7, opacity: 1 },
    { scale: 0.95, y: -20, zIndex: 6, opacity: 0.9 },
    { scale: 0.9, y: -40, zIndex: 5, opacity: 0.8 },
    { scale: 0.85, y: -55, zIndex: 4, opacity: 0.7 },
];

export function PhaseCardStack({ phaseStatuses }: PhaseCardStackProps) {
    // Sort phases: active first, then pending, then completed at back
    const sortedPhases = BUILD_PHASES.map((phase, i) => ({
        phase,
        index: i,
        status: phaseStatuses[i]
    })).sort((a, b) => {
        if (a.status === 'active') return -1;
        if (b.status === 'active') return 1;
        if (a.status === 'pending' && b.status === 'completed') return -1;
        if (a.status === 'completed' && b.status === 'pending') return 1;
        return a.index - b.index;
    });

    return (
        <div style={{
            position: 'relative',
            height: '300px',
            width: '100%',
            display: 'flex',
            alignItems: 'flex-end',
            justifyContent: 'center'
        }}>
            <AnimatePresence>
                {sortedPhases.slice(0, 4).map((item, displayIndex) => (
                    <PhaseCard
                        key={item.phase.id}
                        phase={item.phase}
                        status={item.status}
                        phaseNumber={item.index + 1}
                        displayIndex={displayIndex}
                    />
                ))}
            </AnimatePresence>
        </div>
    );
}

interface PhaseCardProps {
    phase: typeof BUILD_PHASES[number];
    status: PhaseStatus;
    phaseNumber: number;
    displayIndex: number;
}

function PhaseCard({ phase, status, phaseNumber, displayIndex }: PhaseCardProps) {
    const pos = positionStyles[Math.min(displayIndex, 3)];
    const isActive = status === 'active';
    const isCompleted = status === 'completed';
    const isPending = status === 'pending';

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 50 }}
            animate={{
                y: pos.y,
                scale: pos.scale,
                opacity: pos.opacity,
                zIndex: pos.zIndex
            }}
            exit={{ y: 100, opacity: 0, scale: 0.8 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            style={{
                position: 'absolute',
                bottom: 0,
                left: '50%',
                transform: 'translateX(-50%)',
                width: '340px',
                background: '#FFFFFF',
                borderRadius: '16px',
                overflow: 'hidden',
                border: isActive ? '2px solid #FF4D00' : '1px solid #E5E5E5',
                boxShadow: isActive
                    ? '0 20px 40px rgba(255, 77, 0, 0.15)'
                    : '0 10px 30px rgba(0, 0, 0, 0.08)',
                cursor: 'pointer'
            }}
        >
            {/* Diagonal Stripe Accent - Top */}
            <div style={{
                height: '6px',
                background: isActive
                    ? 'repeating-linear-gradient(45deg, #FF4D00, #FF4D00 4px, #FF6B2C 4px, #FF6B2C 8px)'
                    : isCompleted
                        ? '#22C55E'
                        : 'repeating-linear-gradient(45deg, #E5E5E5, #E5E5E5 4px, #F5F5F5 4px, #F5F5F5 8px)'
            }} />

            {/* Shimmer effect for pending cards */}
            {isPending && (
                <motion.div
                    animate={{
                        x: ['-100%', '200%']
                    }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: 'linear'
                    }}
                    style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
                        pointerEvents: 'none',
                        zIndex: 1
                    }}
                />
            )}

            {/* Card Content */}
            <div style={{ padding: '20px 24px', position: 'relative', zIndex: 2 }}>
                {/* Header Row */}
                <div style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    marginBottom: '14px'
                }}>
                    {/* Phase Icon Box */}
                    <motion.div
                        animate={isPending ? {
                            scale: [1, 1.05, 1],
                            opacity: [0.6, 1, 0.6]
                        } : {}}
                        transition={isPending ? {
                            duration: 1.5,
                            repeat: Infinity,
                            ease: 'easeInOut'
                        } : {}}
                        style={{
                            width: '56px',
                            height: '56px',
                            background: isActive
                                ? 'linear-gradient(135deg, #FF4D00 0%, #FF6B2C 100%)'
                                : isCompleted
                                    ? '#22C55E'
                                    : '#F5F5F5',
                            borderRadius: '12px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '28px',
                            boxShadow: isActive ? '0 8px 20px rgba(255, 77, 0, 0.3)' : 'none'
                        }}
                    >
                        {isCompleted ? (
                            <span className="material-icons-round" style={{ fontSize: '28px', color: 'white' }}>check</span>
                        ) : (
                            phase.icon
                        )}
                    </motion.div>

                    {/* Phase Number */}
                    <div style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: '11px',
                        color: '#999',
                        letterSpacing: '0.05em'
                    }}>
                        PHASE {String(phaseNumber).padStart(2, '0')}/07
                    </div>
                </div>

                {/* Phase Name */}
                <h3 style={{
                    fontSize: '18px',
                    fontWeight: '700',
                    color: '#0A0A0A',
                    margin: '0 0 6px 0',
                    letterSpacing: '-0.02em'
                }}>
                    {phase.name}
                </h3>

                {/* Description */}
                <p style={{
                    fontSize: '13px',
                    color: '#666',
                    margin: '0 0 16px 0',
                    lineHeight: '1.5'
                }}>
                    {phase.description}
                </p>

                {/* Progress Bar */}
                <div style={{
                    height: '4px',
                    background: '#F0F0F0',
                    borderRadius: '2px',
                    overflow: 'hidden'
                }}>
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{
                            width: isCompleted ? '100%' : isActive ? '60%' : '0%'
                        }}
                        transition={{
                            duration: isActive ? 3 : 0.5,
                            ease: isActive ? 'linear' : 'easeOut'
                        }}
                        style={{
                            height: '100%',
                            background: isCompleted
                                ? '#22C55E'
                                : 'linear-gradient(90deg, #FF4D00, #FF6B2C)',
                            borderRadius: '2px'
                        }}
                    />
                </div>

                {/* Status Text */}
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    marginTop: '10px'
                }}>
                    {isActive && (
                        <motion.div
                            animate={{ opacity: [1, 0.5, 1] }}
                            transition={{ repeat: Infinity, duration: 1.5 }}
                            style={{
                                width: '6px',
                                height: '6px',
                                borderRadius: '50%',
                                background: '#FF4D00'
                            }}
                        />
                    )}
                    {isPending && (
                        <motion.div
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                            style={{
                                width: '10px',
                                height: '10px',
                                border: '2px solid #E5E5E5',
                                borderTopColor: '#999',
                                borderRadius: '50%'
                            }}
                        />
                    )}
                    <span style={{
                        fontSize: '11px',
                        fontWeight: '600',
                        color: isCompleted ? '#22C55E' : isActive ? '#FF4D00' : '#999',
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em'
                    }}>
                        {isCompleted ? 'Completed' : isActive ? 'In Progress' : isPending ? 'Preparing...' : 'Pending'}
                    </span>
                </div>
            </div>
        </motion.div>
    );
}

