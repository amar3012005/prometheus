import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useBuildStore } from '../store/buildStore';
import { useBuildSession } from '../hooks/useBuildSession';
import { PhaseCardStack } from './PhaseCardStack';
import { TerminalConsole } from './TerminalConsole';
import { VoiceSelector } from './VoiceSelector';
import BoxLoader from './ui/box-loader';

interface BuilderSheetProps {
    isOpen: boolean;
    onSelectVoice: (voiceId: string) => void;
}

export default function BuilderSheet({ isOpen, onSelectVoice }: BuilderSheetProps) {
    const [isDragging, setIsDragging] = useState(false);
    const dragRef = useRef<HTMLDivElement>(null);

    const {
        missionName,
        isReadyToTest,
        phaseStatuses,
        showVoiceSelector,
        voiceCandidates,
        builderWidth,
        setBuilderWidth,
        checklistTags,
        extractedFields,
        contextComplete,
        isPipelineStarted,
        isVoiceSelected,
        isKbReady
    } = useBuildStore();

    const { launchPipeline } = useBuildSession();

    // Compute if all requirements are met for building
    const readyToBuild = contextComplete && isVoiceSelected && isKbReady;

    // Debug: Log voice selector state
    console.log('[BuilderSheet] showVoiceSelector:', showVoiceSelector, 'candidates:', voiceCandidates?.length);

    // Handle drag resize
    useEffect(() => {
        const handleMouseMove = (e: MouseEvent) => {
            if (!isDragging) return;
            const newWidth = window.innerWidth - e.clientX;
            const maxWidth = Math.max(700, window.innerWidth * 0.5);
            setBuilderWidth(Math.max(380, Math.min(maxWidth, newWidth)));
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
    }, [isDragging]);

    const completedPhases = phaseStatuses.filter(s => s === 'completed').length;

    return (
        <AnimatePresence>
            {isOpen && (
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
                        background: '#FAFAFA',
                        borderLeft: '1px solid #E5E5E5',
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden',
                        zIndex: 100,
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
                            background: isDragging ? '#FF4D00' : 'transparent',
                            transition: 'background 0.2s',
                            zIndex: 10
                        }}
                    />

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* HEADER - Swiss Brutalist Style */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    <div style={{
                        background: '#FFFFFF',
                        borderBottom: '1px solid #E5E5E5'
                    }}>
                        {/* Top Accent Bar */}
                        <div style={{
                            height: '4px',
                            background: isReadyToTest
                                ? '#22C55E'
                                : 'repeating-linear-gradient(90deg, #FF4D00, #FF4D00 20px, #FF6B2C 20px, #FF6B2C 40px)'
                        }} />

                        <div style={{
                            padding: '20px 24px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between'
                        }}>
                            {/* Left: Agent Info */}
                            <div>
                                <div style={{
                                    fontSize: '11px',
                                    fontWeight: '600',
                                    color: '#999',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.1em',
                                    marginBottom: '4px'
                                }}>
                                    BUILD PIPELINE
                                </div>
                                <div style={{
                                    fontSize: '20px',
                                    fontWeight: '800',
                                    color: '#0A0A0A',
                                    letterSpacing: '-0.02em'
                                }}>
                                    {missionName || 'New Agent'}
                                </div>
                            </div>

                            {/* Right: Progress Counter */}
                            <div style={{
                                display: 'flex',
                                alignItems: 'baseline',
                                gap: '4px'
                            }}>
                                <span style={{
                                    fontSize: '36px',
                                    fontWeight: '800',
                                    color: '#FF4D00',
                                    fontFamily: 'JetBrains Mono, monospace',
                                    lineHeight: 1
                                }}>
                                    {completedPhases}
                                </span>
                                <span style={{
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    color: '#999'
                                }}>
                                    /7
                                </span>
                            </div>
                        </div>

                        {/* Phase Progress Dots */}
                        <div style={{
                            padding: '0 24px 16px',
                            display: 'flex',
                            gap: '8px'
                        }}>
                            {phaseStatuses.map((status, i) => (
                                <motion.div
                                    key={i}
                                    animate={{
                                        background: status === 'completed' ? '#22C55E'
                                            : status === 'active' ? '#FF4D00'
                                                : '#E5E5E5',
                                        scale: status === 'active' ? 1.3 : 1
                                    }}
                                    style={{
                                        width: '8px',
                                        height: '8px',
                                        borderRadius: '50%'
                                    }}
                                />
                            ))}
                        </div>

                        {/* New Extraction Checklist */}
                        <div style={{
                            padding: '0 24px 20px',
                            borderBottom: '1px solid #F0F0F0'
                        }}>
                            <div style={{
                                fontSize: '10px',
                                fontWeight: '800',
                                color: '#999',
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                marginBottom: '10px'
                            }}>
                                Extracted Intelligence
                            </div>
                            <div style={{
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '8px',
                            }}>
                                {[
                                    { id: 'org', label: 'Organization', key: 'org_name' },
                                    { id: 'agent', label: 'Agent Name', key: 'agent_name' },
                                    { id: 'vibe', label: 'Persona', key: 'persona_vibe' },
                                    { id: 'voice', label: 'Voice Pref', key: 'voice_parameters' },
                                    { id: 'url', label: 'URL', key: 'knowledge_url' }
                                ].map((item) => {
                                    const value = extractedFields?.[item.key];
                                    const isFilled = value &&
                                        (typeof value === 'object' ?
                                            Object.keys(value).length > 2 : // Stricter check for objects (voice_params)
                                            value.toString().trim().length > 0);

                                    return (
                                        <div key={item.id} style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                            padding: '5px 10px',
                                            borderRadius: '6px',
                                            background: isFilled ? '#DEF7EC' : '#F3F4F6',
                                            color: isFilled ? '#03543F' : '#6B7280',
                                            fontSize: '11px',
                                            fontWeight: '700',
                                            transition: 'all 0.2s ease'
                                        }}>
                                            <div style={{
                                                width: '12px',
                                                height: '12px',
                                                borderRadius: '50%',
                                                background: isFilled ? '#057A55' : '#D1D5DB',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center'
                                            }}>
                                                {isFilled && (
                                                    <svg width="8" height="8" viewBox="0 0 10 10" fill="none">
                                                        <path d="M2 5L4 7L8 3" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                                    </svg>
                                                )}
                                            </div>
                                            {item.label}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* MAIN CONTENT AREA */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    <div style={{
                        flex: 1,
                        display: 'flex',
                        flexDirection: 'column',
                        overflow: 'hidden'
                    }}>
                        {/* Card Stack Section */}
                        <div style={{
                            flex: 1,
                            padding: '24px',
                            overflow: 'hidden',
                            display: 'flex',
                            flexDirection: 'column',
                            position: 'relative' // Required for absolute VoiceSelector
                        }}>
                            {/* Voice Selector Overlay with Backdrop */}
                            <AnimatePresence>
                                {(showVoiceSelector && !isVoiceSelected) && (
                                    <>
                                        {/* Backdrop */}
                                        <motion.div
                                            initial={{ opacity: 0 }}
                                            animate={{ opacity: 1 }}
                                            exit={{ opacity: 0 }}
                                            style={{
                                                position: 'absolute',
                                                inset: 0,
                                                background: 'rgba(255, 255, 255, 0.85)',
                                                backdropFilter: 'blur(8px)',
                                                zIndex: 99
                                            }}
                                        />
                                        <VoiceSelector onSelectVoice={onSelectVoice} />
                                    </>
                                )}
                            </AnimatePresence>

                            {/* Information Gathering State - Checklist & Spinner */}
                            {/* Show this when pipeline hasn't started AND not all requirements are met */}
                            {(!isPipelineStarted && !readyToBuild) && (
                                <div style={{
                                    flex: 1,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    paddingBottom: '20px',
                                    gap: '16px'
                                }}>
                                    {/* Stacking Checklist Tags */}
                                    <div style={{
                                        display: 'flex',
                                        flexDirection: 'column',
                                        gap: '10px',
                                        width: '100%',
                                        maxWidth: '320px',
                                        marginBottom: '16px'
                                    }}>
                                        <AnimatePresence>
                                            {checklistTags.map((tag, index) => (
                                                <motion.div
                                                    key={tag.id}
                                                    initial={{ opacity: 0, x: -30 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    exit={{ opacity: 0, x: 30 }}
                                                    transition={{ delay: index * 0.15, type: 'spring', damping: 20, stiffness: 200 }}
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '10px',
                                                        padding: '10px 14px',
                                                        background: tag.status === 'done' ? '#F0FDF4' : '#FFFFFF',
                                                        border: `1px solid ${tag.status === 'done' ? '#22C55E' : '#E5E5E5'}`,
                                                        borderRadius: '8px',
                                                        boxShadow: '0 2px 8px rgba(0,0,0,0.04)'
                                                    }}
                                                >
                                                    {/* Icon */}
                                                    {tag.status === 'active' ? (
                                                        <motion.div
                                                            animate={{ rotate: 360 }}
                                                            transition={{ repeat: Infinity, duration: 1.2, ease: 'linear' }}
                                                            style={{
                                                                width: '18px',
                                                                height: '18px',
                                                                border: '2px solid #FF4D00',
                                                                borderTopColor: 'transparent',
                                                                borderRadius: '50%'
                                                            }}
                                                        />
                                                    ) : (
                                                        <span className="material-icons-round" style={{ fontSize: '18px', color: '#22C55E' }}>
                                                            check_circle
                                                        </span>
                                                    )}
                                                    {/* Label */}
                                                    <span style={{
                                                        fontSize: '13px',
                                                        fontWeight: '500',
                                                        color: tag.status === 'done' ? '#15803D' : '#333'
                                                    }}>
                                                        {tag.label}
                                                    </span>
                                                </motion.div>
                                            ))}
                                        </AnimatePresence>
                                    </div>

                                    {/* BoxLoader */}
                                    <div style={{ transform: 'scale(0.8)', opacity: 0.8 }}>
                                        <BoxLoader />
                                    </div>
                                </div>
                            )}

                            {/* Ready to Build State - "Let's Build" Button */}
                            {(readyToBuild && !isPipelineStarted) && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    style={{
                                        flex: 1,
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        padding: '0 40px',
                                        gap: '24px',
                                        textAlign: 'center'
                                    }}
                                >
                                    <div style={{
                                        width: '64px',
                                        height: '64px',
                                        background: '#DEF7EC',
                                        borderRadius: '50%',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: '#057A55'
                                    }}>
                                        <span className="material-icons-round" style={{ fontSize: '40px' }}>verified</span>
                                    </div>
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        <div style={{
                                            fontSize: '22px',
                                            fontWeight: '800',
                                            color: '#0A0A0A',
                                            letterSpacing: '-0.02em'
                                        }}>
                                            Context Collected
                                        </div>
                                        <div style={{
                                            fontSize: '14px',
                                            fontWeight: '500',
                                            color: '#666',
                                            lineHeight: 1.5
                                        }}>
                                            The architect has gathered all required intelligence.<br />Ready to initialize the build pipeline.
                                        </div>
                                    </div>
                                    <button
                                        onClick={launchPipeline}
                                        style={{
                                            padding: '18px 48px',
                                            background: '#FF4D00',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '12px',
                                            fontSize: '16px',
                                            fontWeight: '800',
                                            cursor: 'pointer',
                                            boxShadow: '0 8px 24px rgba(255, 77, 0, 0.25)',
                                            textTransform: 'uppercase',
                                            letterSpacing: '0.05em',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '12px'
                                        }}
                                    >
                                        Let's Build
                                        <span className="material-icons-round">rocket_launch</span>
                                    </button>
                                </motion.div>
                            )}

                            {/* Phase Card Stack - Only show once pipeline started */}
                            <AnimatePresence>
                                {isPipelineStarted && (
                                    <motion.div
                                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                                        animate={{ opacity: 1, scale: 1, y: 0 }}
                                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                                        transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                                    >
                                        <PhaseCardStack
                                            phaseStatuses={phaseStatuses}
                                        />
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>


                        {/* ═══════════════════════════════════════════════════════════ */}
                        {/* TERMINAL CONSOLE - Bottom Section */}
                        {/* ═══════════════════════════════════════════════════════════ */}
                        <div style={{
                            height: '200px',
                            borderTop: '1px solid #E5E5E5',
                            background: '#0A0A0A'
                        }}>
                            <TerminalConsole />
                        </div>
                    </div>

                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {/* BOTTOM ACTION BAR */}
                    {/* ═══════════════════════════════════════════════════════════════ */}
                    {isReadyToTest && (
                        <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            style={{
                                padding: '16px 24px',
                                background: '#FFFFFF',
                                borderTop: '1px solid #E5E5E5'
                            }}
                        >
                            <button
                                style={{
                                    width: '100%',
                                    padding: '16px',
                                    background: '#0A0A0A',
                                    color: 'white',
                                    border: 'none',
                                    borderRadius: '12px',
                                    fontSize: '14px',
                                    fontWeight: '700',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '10px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em'
                                }}
                            >
                                <span className="material-icons-round" style={{ fontSize: '20px' }}>play_arrow</span>
                                Test Agent
                            </button>
                        </motion.div>
                    )}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
