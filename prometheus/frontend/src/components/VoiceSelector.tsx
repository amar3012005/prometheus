import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useBuildStore, VoiceCandidate } from '../store/buildStore';

interface VoiceSelectorProps {
    onSelectVoice: (voiceId: string) => void;
}

export function VoiceSelector({ onSelectVoice }: VoiceSelectorProps) {
    const { voiceCandidates, showVoiceSelector, isVoiceSelected } = useBuildStore();
    const [playingId, setPlayingId] = useState<string | null>(null);
    const audioRef = useRef<HTMLAudioElement | null>(null);

    // If voice is already selected or we shouldn't show the selector, return null
    if (!showVoiceSelector || voiceCandidates.length === 0 || isVoiceSelected) return null;

    const handlePlay = (voice: VoiceCandidate) => {
        if (!voice.preview_url) {
            console.warn(`No preview URL for voice: ${voice.name}`);
            // Briefly show playing state then reset if no URL to avoid stuck UI
            setPlayingId(voice.voice_id);
            setTimeout(() => setPlayingId(null), 1000);
            return;
        }

        if (playingId === voice.voice_id) {
            if (audioRef.current) {
                audioRef.current.pause();
                audioRef.current = null;
            }
            setPlayingId(null);
        } else {
            // Stop existing audio
            if (audioRef.current) {
                audioRef.current.pause();
            }

            const audio = new Audio(voice.preview_url);
            audio.onended = () => setPlayingId(null);
            audio.onerror = (e) => {
                console.error("Audio playback error:", e);
                setPlayingId(null);
            };

            audio.play().catch(err => {
                console.error("Audio.play() failed:", err);
                setPlayingId(null);
            });

            audioRef.current = audio;
            setPlayingId(voice.voice_id);
        }
    };

    const handleSelect = (voiceId: string) => {
        audioRef.current?.pause();
        audioRef.current = null;
        onSelectVoice(voiceId);
    };

    const topVoices = voiceCandidates.slice(0, 3);

    return (
        <AnimatePresence>
            {showVoiceSelector && !isVoiceSelected && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 20 }}
                    transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                    style={{
                        position: 'absolute',
                        top: '50%',
                        left: '24px',
                        right: '24px',
                        transform: 'translateY(-50%)',
                        background: '#FFFFFF',
                        borderRadius: '16px',
                        padding: '0',
                        boxShadow: '0 30px 60px rgba(0, 0, 0, 0.2)',
                        zIndex: 1000,
                        border: '1px solid #E5E5E5',
                        overflow: 'hidden'
                    }}
                >
                    {/* Top Accent Stripe */}
                    <div style={{
                        height: '4px',
                        background: 'repeating-linear-gradient(90deg, #FF4D00, #FF4D00 20px, #FF6B2C 20px, #FF6B2C 40px)'
                    }} />

                    <div style={{ padding: '24px' }}>
                        {/* Header */}
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            marginBottom: '20px',
                            paddingBottom: '16px',
                            borderBottom: '1px solid #F1F1F1'
                        }}>
                            <div>
                                <div style={{
                                    fontSize: '11px',
                                    fontWeight: '700',
                                    color: '#999',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.1em',
                                    marginBottom: '4px'
                                }}>
                                    AUDIO IDENTITY
                                </div>
                                <div style={{
                                    fontSize: '22px',
                                    fontWeight: '800',
                                    color: '#1A1A1A',
                                    letterSpacing: '-0.02em'
                                }}>
                                    Select Voice
                                </div>
                            </div>
                            <div style={{
                                width: '44px',
                                height: '44px',
                                borderRadius: '12px',
                                background: '#FFF5F0',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#FF4D00',
                                border: '1px solid #FFD6C2'
                            }}>
                                <span className="material-icons-round" style={{ fontSize: '24px' }}>graphic_eq</span>
                            </div>
                        </div>

                        {/* List */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                            {topVoices.map((voice, index) => (
                                <motion.div
                                    key={voice.voice_id}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.05 }}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '16px',
                                        padding: '16px',
                                        background: playingId === voice.voice_id ? '#FFF9F6' : '#FAFAFA',
                                        borderRadius: '12px',
                                        border: '1px solid',
                                        borderColor: playingId === voice.voice_id ? '#FF4D00' : 'transparent',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                    }}
                                    onClick={() => handlePlay(voice)}
                                >
                                    {/* Play Circle */}
                                    <div
                                        style={{
                                            width: '40px',
                                            height: '40px',
                                            borderRadius: '50%',
                                            background: playingId === voice.voice_id ? '#FF4D00' : '#E5E5E5',
                                            color: playingId === voice.voice_id ? '#FFF' : '#666',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            flexShrink: 0
                                        }}
                                    >
                                        <span className="material-icons-round" style={{ fontSize: '22px' }}>
                                            {playingId === voice.voice_id ? 'pause' : 'play_arrow'}
                                        </span>
                                    </div>

                                    {/* Info */}
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div style={{
                                            fontSize: '15px',
                                            fontWeight: '700',
                                            color: '#1A1A1A',
                                            marginBottom: '2px'
                                        }}>
                                            {voice.name}
                                        </div>
                                        <div style={{
                                            fontSize: '11px',
                                            fontWeight: '600',
                                            color: '#888',
                                            display: 'flex',
                                            gap: '6px',
                                            textTransform: 'uppercase'
                                        }}>
                                            <span style={{ color: '#FF4D00' }}>{voice.labels?.accent || 'Studio'}</span>
                                            <span>•</span>
                                            <span>{voice.labels?.gender || 'Voice'}</span>
                                        </div>
                                    </div>

                                    {/* Action */}
                                    <button
                                        onClick={(e) => { e.stopPropagation(); handleSelect(voice.voice_id); }}
                                        style={{
                                            padding: '10px 20px',
                                            background: '#1A1A1A',
                                            color: '#FFF',
                                            border: 'none',
                                            borderRadius: '8px',
                                            fontSize: '12px',
                                            fontWeight: '800',
                                            textTransform: 'uppercase',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        Select
                                    </button>
                                </motion.div>
                            ))}
                        </div>

                        {/* Footer Hint */}
                        <div style={{
                            marginTop: '20px',
                            textAlign: 'center',
                            fontSize: '11px',
                            fontWeight: '600',
                            color: '#AAA',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em'
                        }}>
                            Click to preview • Choose your brand voice
                        </div>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
