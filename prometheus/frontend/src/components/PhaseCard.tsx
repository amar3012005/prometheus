import { motion } from 'framer-motion';
import { BUILD_PHASES, PhaseStatus } from '../store/buildStore';

interface PhaseCardProps {
    phase: typeof BUILD_PHASES[number];
    status: PhaseStatus;
    index: number;
    totalCards: number;
    isTopCard: boolean;
}

export function PhaseCard({ phase, status, index, totalCards, isTopCard }: PhaseCardProps) {
    // Calculate card position in stack
    const stackOffset = isTopCard ? 0 : (index + 1) * 6;
    const scaleReduction = isTopCard ? 0 : (index + 1) * 0.02;
    const opacityReduction = isTopCard ? 0 : (index + 1) * 0.1;

    const getStatusColor = () => {
        switch (status) {
            case 'completed': return '#22C55E';
            case 'active': return '#FF4D00';
            case 'error': return '#EF4444';
            default: return '#E5E5E5';
        }
    };

    const getStatusIcon = () => {
        switch (status) {
            case 'completed': return 'check_circle';
            case 'active': return 'sync';
            case 'error': return 'error';
            default: return 'radio_button_unchecked';
        }
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{
                y: -stackOffset,
                scale: 1 - scaleReduction,
                opacity: 1 - opacityReduction,
                zIndex: totalCards - index
            }}
            transition={{
                type: 'spring',
                stiffness: 300,
                damping: 30
            }}
            style={{
                position: index === 0 && isTopCard ? 'relative' : 'absolute',
                top: 0,
                left: 0,
                right: 0,
                background: '#FFFFFF',
                border: `2px solid ${status === 'active' ? '#FF4D00' : '#E5E5E5'}`,
                borderRadius: '12px',
                padding: '16px 20px',
                boxShadow: status === 'active'
                    ? '0 8px 24px rgba(255, 77, 0, 0.15)'
                    : '0 4px 12px rgba(0, 0, 0, 0.05)',
                cursor: 'default'
            }}
        >
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '14px'
            }}>
                {/* Phase Icon */}
                <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: '10px',
                    background: status === 'active'
                        ? 'rgba(255, 77, 0, 0.1)'
                        : status === 'completed'
                            ? 'rgba(34, 197, 94, 0.1)'
                            : '#F5F5F5',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '22px'
                }}>
                    {phase.icon}
                </div>

                {/* Phase Info */}
                <div style={{ flex: 1 }}>
                    <div style={{
                        fontSize: '15px',
                        fontWeight: '600',
                        color: '#0A0A0A',
                        marginBottom: '2px'
                    }}>
                        {phase.name}
                    </div>
                    <div style={{
                        fontSize: '12px',
                        color: '#666'
                    }}>
                        {phase.description}
                    </div>
                </div>

                {/* Status Indicator */}
                <motion.div
                    animate={status === 'active' ? { rotate: 360 } : { rotate: 0 }}
                    transition={status === 'active' ? { repeat: Infinity, duration: 2, ease: 'linear' } : {}}
                >
                    <span className="material-icons-round" style={{
                        fontSize: '24px',
                        color: getStatusColor()
                    }}>
                        {getStatusIcon()}
                    </span>
                </motion.div>
            </div>

            {/* Progress bar for active phase */}
            {status === 'active' && (
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    transition={{ duration: 3, ease: 'linear' }}
                    style={{
                        height: '3px',
                        background: '#FF4D00',
                        borderRadius: '2px',
                        marginTop: '12px'
                    }}
                />
            )}
        </motion.div>
    );
}
