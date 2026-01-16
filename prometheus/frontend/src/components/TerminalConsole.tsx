import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { useBuildStore } from '../store/buildStore';

export function TerminalConsole() {
    const { terminalLogs } = useBuildStore();
    const scrollRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [terminalLogs]);

    const getPhaseColor = (phase: string) => {
        if (phase === 'DEPLOYED' || phase === 'COMPLETE') return '#22C55E';
        if (phase === 'ERROR') return '#EF4444';
        if (phase === 'VOICE') return '#A855F7';
        if (phase === 'INIT') return '#3B82F6';
        if (phase === 'BUILD' || phase === 'BUILDING') return '#3B82F6';
        if (phase === 'GENERATING') return '#10B981';
        if (phase === 'PLANNING') return '#F59E0B';
        return '#3B82F6';
    };

    const formatMessage = (message: string) => {
        // Parse message to detect tree structures, emojis, and special formatting
        const parts: Array<{ text: string; color?: string; bold?: boolean }> = [];

        // Check for tree characters at the start (with any amount of leading spaces)
        const treeMatch = message.match(/^(\s*)(├─|└─|│)\s*/);
        if (treeMatch) {
            const indent = treeMatch[1];
            const treeChar = treeMatch[2];
            const rest = message.substring(treeMatch[0].length);

            // Indent spaces + tree character in dim color
            parts.push({ text: indent + treeChar + ' ', color: '#555' });

            // Check for checkmark in the rest
            if (rest.includes('✓')) {
                const checkIndex = rest.indexOf('✓');
                const before = rest.substring(0, checkIndex);
                const after = rest.substring(checkIndex + 1);

                if (before) parts.push({ text: before, color: '#AAA' });
                parts.push({ text: '✓ ', color: '#22C55E', bold: true });
                if (after) parts.push({ text: after, color: '#AAA' });
            } else {
                parts.push({ text: rest, color: '#AAA' });
            }
        } else {
            // Regular message - highlight emojis and special characters
            let remaining = message;

            // Emoji and special character regex
            const emojiRegex = /(🚀|🏗️|📦|🧠|🎤|🤖|🌐|🔍|🔊|✓|✅|❌|🎙️|💬|🔧|━|★)/g;
            const matches = Array.from(remaining.matchAll(emojiRegex));
            let lastIndex = 0;

            for (const match of matches) {
                // Text before emoji
                if (match.index! > lastIndex) {
                    parts.push({ text: remaining.substring(lastIndex, match.index), color: '#AAA' });
                }

                // Emoji with bright color
                const emoji = match[0];
                if (emoji === '✓' || emoji === '✅') {
                    parts.push({ text: emoji, color: '#22C55E', bold: true });
                } else if (emoji === '❌') {
                    parts.push({ text: emoji, color: '#EF4444', bold: true });
                } else {
                    parts.push({ text: emoji, bold: true });
                }

                lastIndex = match.index! + match[0].length;
            }

            // Remaining text
            if (lastIndex < remaining.length) {
                parts.push({ text: remaining.substring(lastIndex), color: '#AAA' });
            }
        }

        return parts;
    };

    return (
        <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            background: '#0A0A0A'
        }}>
            {/* Terminal Header */}
            <div style={{
                padding: '10px 16px',
                borderBottom: '1px solid #222',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
            }}>
                <div style={{ display: 'flex', gap: '6px' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#FF5F57' }} />
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#FFBD2E' }} />
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#28C840' }} />
                </div>
                <span style={{
                    fontSize: '11px',
                    color: '#666',
                    fontFamily: 'JetBrains Mono, monospace',
                    textTransform: 'uppercase',
                    letterSpacing: '0.1em'
                }}>
                    prometheus-build-system
                </span>
            </div>

            {/* Terminal Content */}
            <div
                ref={scrollRef}
                style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '12px 16px',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '11px',
                    lineHeight: '1.8'
                }}
            >
                {terminalLogs.length === 0 ? (
                    <div style={{ color: '#666' }}>
                        <span style={{ color: '#FF4D00' }}>$</span> Waiting for build to start...
                        <motion.span
                            animate={{ opacity: [1, 0] }}
                            transition={{ repeat: Infinity, duration: 0.8 }}
                            style={{ marginLeft: '4px' }}
                        >
                            █
                        </motion.span>
                    </div>
                ) : (
                    terminalLogs.map((log, i) => {
                        const messageParts = formatMessage(log.message);
                        const phaseColor = getPhaseColor(log.phase);

                        return (
                            <motion.div
                                key={`${log.timestamp}-${i}`}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ duration: 0.1 }}
                                style={{
                                    display: 'flex',
                                    gap: '8px',
                                    color: '#AAA'
                                }}
                            >
                                {/* Timestamp - no brackets, cyan color */}
                                <span style={{
                                    color: '#06B6D4',
                                    flexShrink: 0,
                                    minWidth: '60px'
                                }}>
                                    {log.timestamp}
                                </span>

                                {/* Phase tag - with brackets, bold blue */}
                                <span style={{
                                    color: phaseColor,
                                    fontWeight: '700',
                                    flexShrink: 0,
                                    minWidth: '90px'
                                }}>
                                    [{log.phase}]
                                </span>

                                {/* Message with formatted parts */}
                                <span style={{
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                    flex: 1
                                }}>
                                    {messageParts.map((part, idx) => (
                                        <span
                                            key={idx}
                                            style={{
                                                color: part.color || '#AAA',
                                                fontWeight: part.bold ? '700' : 'normal'
                                            }}
                                        >
                                            {part.text}
                                        </span>
                                    ))}
                                </span>
                            </motion.div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
