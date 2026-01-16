import { motion, AnimatePresence } from 'framer-motion';
import { BUILD_PHASES, useBuildStore } from '../store/buildStore';
import { PhaseCard } from './PhaseCard';

export function PhaseCardDeck() {
    const { phaseStatuses } = useBuildStore();

    // Reorder phases: active first, then pending, then completed at bottom
    const orderedPhases = BUILD_PHASES.map((phase, i) => ({
        phase,
        originalIndex: i,
        status: phaseStatuses[i]
    })).sort((a, b) => {
        const statusOrder = { active: 0, pending: 1, completed: 2, error: 3 };
        return statusOrder[a.status] - statusOrder[b.status];
    });

    return (
        <div style={{
            position: 'relative',
            minHeight: '140px',
            marginBottom: '20px'
        }}>
            <AnimatePresence>
                {orderedPhases.map((item, displayIndex) => (
                    <PhaseCard
                        key={item.phase.id}
                        phase={item.phase}
                        status={item.status}
                        index={displayIndex}
                        totalCards={7}
                        isTopCard={displayIndex === 0}
                    />
                ))}
            </AnimatePresence>

            {/* Phase Counter */}
            <div style={{
                position: 'absolute',
                bottom: '-28px',
                left: '50%',
                transform: 'translateX(-50%)',
                display: 'flex',
                gap: '6px'
            }}>
                {BUILD_PHASES.map((_, i) => (
                    <motion.div
                        key={i}
                        animate={{
                            background: phaseStatuses[i] === 'completed'
                                ? '#22C55E'
                                : phaseStatuses[i] === 'active'
                                    ? '#FF4D00'
                                    : '#E5E5E5',
                            scale: phaseStatuses[i] === 'active' ? 1.2 : 1
                        }}
                        style={{
                            width: '8px',
                            height: '8px',
                            borderRadius: '50%'
                        }}
                    />
                ))}
            </div>
        </div>
    );
}
