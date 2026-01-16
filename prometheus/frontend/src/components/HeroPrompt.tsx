import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { PromptInputBox } from './ui/ai-prompt-box';
import { useBuildStore } from '../store/buildStore';
import { useBuildSession } from '../hooks/useBuildSession';
import TypingHighlightedText from './TypingHighlightedText';

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

const POPULAR_VOICE_SUGGESTIONS = [
    { label: 'British Male', value: 'British Male Voice' },
    { label: 'American Female', value: 'American Female Voice' },
    { label: 'Neutral German', value: 'Neutral German Voice' },
    { label: 'Professional Tone', value: 'Professional, technical tone' },
    { label: 'Warm & Friendly', value: 'Warm, friendly and inviting' },
    { label: 'Indian English', value: 'Indian English Accent' }
];

export default function HeroPrompt({ onSubmit }: { onSubmit: (prompt: string) => void }) {
    const [promptValue, setPromptValue] = useState("");
    const {
        isBuilding,
        isReadyToTest,
        hasError,
        buildHistory,
        isArchitectThinking,
        suggestions
    } = useBuildStore();
    const { sendClarification } = useBuildSession();

    // Internal state to sequence the transition
    const [showChatUI, setShowChatUI] = useState(false);
    const [hideTemplates, setHideTemplates] = useState(false);

    const [visibleMessages, setVisibleMessages] = useState<Message[]>([]);
    const [isTyping, setIsTyping] = useState(false);
    const processingIndices = useRef(new Set<number>());
    const chatEndRef = useRef<HTMLDivElement>(null);
    const chatContainerRef = useRef<HTMLDivElement>(null);

    const isChatMode = isBuilding || isReadyToTest || hasError;

    // --- SEQUENCING ENGINE ---
    useEffect(() => {
        if (isChatMode && !showChatUI) {
            const runSequence = async () => {
                await new Promise(r => setTimeout(r, 1200));
                setHideTemplates(true);
                await new Promise(r => setTimeout(r, 300));
                setShowChatUI(true);
            };
            runSequence();
        } else if (!isChatMode) {
            setShowChatUI(false);
            setHideTemplates(false);
            setVisibleMessages([]);
            processingIndices.current.clear();
        }
    }, [isChatMode]);

    const isWaitingForUser = isChatMode && !isTyping &&
        visibleMessages.length > 0 &&
        visibleMessages[visibleMessages.length - 1].role === 'assistant';

    // Process buildHistory and stagger addition to visibleMessages
    useEffect(() => {
        if (!showChatUI) return;

        const processQueue = async () => {
            for (let i = 0; i < buildHistory.length; i++) {
                if (processingIndices.current.has(i)) continue;
                processingIndices.current.add(i);

                const msg = buildHistory[i];

                if (i === 0) {
                    await new Promise(r => setTimeout(r, 600));
                }

                if (i > 0 || msg.role === 'assistant') {
                    setIsTyping(true);
                    const delay = msg.role === 'assistant' ? 800 : 500; // Shorter base delay, component handles typing
                    await new Promise(r => setTimeout(r, delay));
                    setIsTyping(false);
                }

                setVisibleMessages(prev => {
                    if (prev.some((m, idx) => m.content === msg.content && m.role === msg.role && idx === i)) {
                        return prev;
                    }
                    return [...prev, msg];
                });
            }
        };

        processQueue();
    }, [buildHistory, showChatUI]);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [visibleMessages, isTyping]);

    const handleSend = (message: string) => {
        if (!message.trim() || isTyping) return;

        if (isChatMode) {
            sendClarification(message);
        } else {
            onSubmit(message);
        }
        setPromptValue("");
    };

    const quickTemplates = [
        { label: 'Real Estate Agent', icon: 'home', prompt: 'Build a real estate agent for my luxury property business' },
        { label: 'IT Support', icon: 'support_agent', prompt: 'Build an IT support agent for my tech company' },
        { label: 'Executive Assistant', icon: 'work', prompt: 'Build an executive assistant agent for busy professionals' },
    ];

    return (
        <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
            width: '100%',
            position: 'relative',
            background: 'transparent',
            zIndex: 10,
            overflow: 'hidden'
        }}>
            {/* Watermark Header Layer - Relative when starting to stack, Absolute when chatting to backdrop */}
            <motion.div
                layout
                style={{
                    position: showChatUI ? 'absolute' : 'relative',
                    ...(showChatUI ? {
                        top: 0, left: 0, right: 0, bottom: 0
                    } : {
                        marginBottom: '48px'
                    }),
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    textAlign: 'center',
                    pointerEvents: 'none',
                    zIndex: 1
                }}
            >
                <motion.div
                    initial={false}
                    animate={{
                        opacity: showChatUI ? 0.04 : 1,
                        scale: showChatUI ? 1.4 : 1,
                        filter: showChatUI ? 'blur(1px)' : 'blur(0px)',
                    }}
                    transition={{ type: 'spring', damping: 25, stiffness: 100 }}
                    style={{
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        whiteSpace: 'nowrap',
                    }}
                >
                    <h1 style={{
                        fontFamily: 'Outfit, sans-serif',
                        fontSize: '48px',
                        fontWeight: '800',
                        letterSpacing: '-0.04em',
                        lineHeight: '1.1',
                        margin: 0,
                        color: '#0A0A0A',
                        textTransform: 'uppercase'
                    }}>
                        Build Human-Like Voice Agents
                    </h1>
                    <AnimatePresence>
                        {!showChatUI && (
                            <motion.p
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                style={{
                                    fontSize: '17px',
                                    color: '#666',
                                    marginTop: '16px',
                                    fontWeight: '400',
                                    maxWidth: '500px'
                                }}
                            >
                                Describe your agent's purpose and personality.
                            </motion.p>
                        )}
                    </AnimatePresence>
                </motion.div>
            </motion.div>

            {/* Main Content Area */}
            <div style={{
                width: '100%',
                maxWidth: showChatUI ? '100%' : '700px',
                height: showChatUI ? '100%' : 'auto',
                display: 'flex',
                flexDirection: 'column',
                position: 'relative',
                zIndex: 5
            }}>
                {/* Chat History Area */}
                <AnimatePresence>
                    {showChatUI && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            ref={chatContainerRef}
                            style={{
                                flex: 1,
                                width: '100%',
                                overflowY: 'auto',
                                padding: '100px 10% 160px',
                                display: 'flex',
                                flexDirection: 'column',
                                gap: '32px',
                                scrollbarWidth: 'none',
                                msOverflowStyle: 'none'
                            }}
                        >
                            {visibleMessages.map((msg, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, y: 30, scale: 0.95 }}
                                    animate={{ opacity: 1, y: 0, scale: 1 }}
                                    transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                                    style={{
                                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                        maxWidth: '650px',
                                        width: '100%',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
                                    }}
                                >
                                    {msg.role === 'assistant' && (
                                        <div style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '10px',
                                            marginBottom: '12px'
                                        }}>
                                            <div style={{
                                                width: '28px',
                                                height: '28px',
                                                borderRadius: '8px',
                                                background: '#0A0A0A',
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                            }}>
                                                <span className="material-icons-round" style={{ fontSize: '16px', color: 'white' }}>
                                                    bolt
                                                </span>
                                            </div>
                                            <span style={{ fontSize: '13px', fontWeight: '700', color: '#0A0A0A' }}>Prometheus</span>
                                        </div>
                                    )}

                                    <div style={{
                                        padding: '18px 26px',
                                        borderRadius: msg.role === 'user' ? '24px 24px 4px 24px' : '4px 24px 24px 24px',
                                        background: msg.role === 'user' ? '#FFFFFF' : '#FAFAFA',
                                        color: '#1A1A1A',
                                        fontSize: '15.5px',
                                        lineHeight: '1.7',
                                        boxShadow: msg.role === 'user' ? '0 10px 40px rgba(0,0,0,0.04)' : 'none',
                                        border: '1px solid #EEEEEE',
                                        width: 'fit-content'
                                    }}>
                                        {msg.role === 'assistant' ? (
                                            <TypingHighlightedText text={msg.content} speed={25} />
                                        ) : (
                                            msg.content
                                        )}
                                    </div>
                                </motion.div>
                            ))}

                            {(isTyping || isArchitectThinking) && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0 }}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '12px',
                                        marginLeft: '4px',
                                        padding: '12px 16px',
                                        background: isArchitectThinking ? 'linear-gradient(135deg, #FFF5EB 0%, #FFEDE0 100%)' : 'transparent',
                                        borderRadius: '12px',
                                        border: isArchitectThinking ? '1px solid #FFD9C0' : 'none'
                                    }}
                                >
                                    <div style={{ display: 'flex', gap: '4px' }}>
                                        {[0, 1, 2].map(i => (
                                            <motion.div
                                                key={i}
                                                animate={{ scale: [1, 1.3, 1], opacity: [0.3, 1, 0.3] }}
                                                transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
                                                style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#FF4D00' }}
                                            />
                                        ))}
                                    </div>
                                    <span style={{
                                        fontSize: '13px',
                                        color: isArchitectThinking ? '#C04000' : '#999',
                                        fontWeight: isArchitectThinking ? '600' : '500'
                                    }}>
                                        {isArchitectThinking ? 'Prometheus is analyzing...' : 'Thinking...'}
                                    </span>
                                </motion.div>
                            )}
                            <div ref={chatEndRef} style={{ height: '40px' }} />
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Bottom Input Area - drops down AFTER Stage 3 */}
                <motion.div
                    layout
                    style={{
                        padding: showChatUI ? '120px 10% 60px' : '0', // Increased top padding to accommodate suggestions
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'center',
                        alignItems: 'center',
                        width: '100%',
                        position: showChatUI ? 'absolute' : 'relative',
                        bottom: showChatUI ? 0 : 'auto',
                        left: 0,
                        right: 0,
                        background: showChatUI ? 'linear-gradient(to top, #FFFFFF 60%, rgba(255,255,255,0) 100%)' : 'transparent',
                    }}
                    transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                >
                    <AnimatePresence>
                        {isWaitingForUser && (suggestions.length > 0 || visibleMessages[visibleMessages.length - 1].content.toLowerCase().includes('voice') ||
                            visibleMessages[visibleMessages.length - 1].content.toLowerCase().includes('language')) && (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: 10 }}
                                    style={{
                                        display: 'flex',
                                        gap: '8px',
                                        flexWrap: 'wrap',
                                        marginBottom: '16px',
                                        justifyContent: 'center',
                                        width: '100%',
                                        maxWidth: '800px'
                                    }}
                                >
                                    {(suggestions.length > 0 ? suggestions.map(s => ({ label: s, value: s })) : POPULAR_VOICE_SUGGESTIONS).map((suggestion) => (
                                        <button
                                            key={suggestion.label}
                                            onClick={() => setPromptValue(suggestion.value)}
                                            style={{
                                                padding: '8px 16px',
                                                background: '#FFFFFF',
                                                border: '1px solid #E5E7EB',
                                                borderRadius: '12px',
                                                fontSize: '13px',
                                                fontWeight: '600',
                                                color: '#111827',
                                                cursor: 'pointer',
                                                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                                                boxShadow: '0 2px 8px rgba(0,0,0,0.05)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '6px'
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.transform = 'translateY(-2px)';
                                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
                                                e.currentTarget.style.borderColor = '#FF4D00';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.transform = 'translateY(0)';
                                                e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.05)';
                                                e.currentTarget.style.borderColor = '#E5E7EB';
                                            }}
                                        >
                                            <span style={{ color: '#FF4D00', fontSize: '14px' }}>✨</span>
                                            {suggestion.label}
                                        </button>
                                    ))}
                                </motion.div>
                            )}
                    </AnimatePresence>

                    <div style={{ width: '100%', maxWidth: '800px' }}>
                        <PromptInputBox
                            value={promptValue}
                            onChange={setPromptValue}
                            onSend={handleSend}
                            isLoading={isWaitingForUser}
                            placeholder={isWaitingForUser ? "" : "Send message to Prometheus..."}
                        />
                    </div>
                </motion.div>

                {/* Quick Templates Area */}
                <AnimatePresence>
                    {!hideTemplates && (
                        <motion.div
                            initial={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 20, scale: 0.95 }}
                            transition={{ duration: 0.4 }}
                            style={{
                                display: 'flex',
                                gap: '10px',
                                justifyContent: 'center',
                                flexWrap: 'wrap',
                                marginTop: '72px'
                            }}
                        >
                            {quickTemplates.map((template, i) => (
                                <button
                                    key={i}
                                    onClick={() => setPromptValue(template.prompt)}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '8px 16px',
                                        background: '#FFFFFF',
                                        border: '1px solid #E0E0E0',
                                        borderRadius: '20px',
                                        color: '#555',
                                        fontSize: '13.5px',
                                        fontWeight: '500',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease',
                                    }}
                                >
                                    <span className="material-icons-round" style={{ fontSize: '18px', opacity: 0.7 }}>
                                        {template.icon}
                                    </span>
                                    {template.label}
                                </button>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
