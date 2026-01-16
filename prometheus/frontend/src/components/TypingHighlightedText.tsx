import React, { useState, useEffect, useMemo } from 'react';

interface TypingHighlightedTextProps {
    text: string;
    speed?: number; // average speed in ms per word
    isTypingEnabled?: boolean;
    className?: string;
}

/**
 * Component that reveals text word-by-word and applies custom highlighting
 * for 'fields', "examples", and {variables}.
 */
const TypingHighlightedText: React.FC<TypingHighlightedTextProps> = ({
    text,
    speed = 40,
    isTypingEnabled = true,
    className = ""
}) => {
    const [displayedText, setDisplayedText] = useState("");
    const [isComplete, setIsComplete] = useState(!isTypingEnabled);

    // Split text into tokens (words and spaces) to preserve formatting
    const tokens = useMemo(() => text.split(/(\s+)/), [text]);

    useEffect(() => {
        if (!isTypingEnabled) {
            setDisplayedText(text);
            setIsComplete(true);
            return;
        }

        let currentTokenIndex = 0;
        setDisplayedText("");
        setIsComplete(false);

        const interval = setInterval(() => {
            if (currentTokenIndex < tokens.length) {
                setDisplayedText(prev => prev + tokens[currentTokenIndex]);
                currentTokenIndex++;
            } else {
                clearInterval(interval);
                setIsComplete(true);
            }
        }, speed);

        return () => clearInterval(interval);
    }, [text, speed, isTypingEnabled, tokens]);

    // Highlighting Logic: Match patterns and wrap in <b> tags
    const renderContent = (content: string) => {
        if (!content) return null;

        // Clean up accidental "undefined" strings that might leak from backend templates
        const cleanContent = content.replace(/undefined$/, '').replace(/^undefined/, '');

        // Regex patterns:
        // 1. \*\*([^*]+)\*\* -> Markdown Bold
        // 2. '([^']+)' -> Single quoted fields
        // 3. "([^"]+)" -> Double quoted examples
        // 4. \{([^}]+)\} -> Curly braced variables
        const parts = cleanContent.split(/(\*\*[^*]+\*\*|\'[^']+\'|\"[^"]+\"|\{[^}]+\})/g);

        return parts.map((part, index) => {
            if (part.startsWith("**") && part.endsWith("**")) {
                const inner = part.slice(2, -2);
                return <b key={index} style={{ fontWeight: '800', color: '#0A0A0A' }}>{inner}</b>;
            }
            if ((part.startsWith("'") && part.endsWith("'")) ||
                (part.startsWith('"') && part.endsWith('"')) ||
                (part.startsWith("{") && part.endsWith("}"))) {
                return <b key={index} style={{ fontWeight: '700', color: '#0A0A0A' }}>{part}</b>;
            }
            return part;
        });
    };

    return (
        <div className={className} style={{ display: 'inline' }}>
            {renderContent(displayedText)}
            {!isComplete && isTypingEnabled && (
                <span style={{
                    display: 'inline-block',
                    width: '2px',
                    height: '1em',
                    background: '#0A0A0A',
                    marginLeft: '2px',
                    verticalAlign: 'middle',
                    animation: 'blink 1s step-end infinite'
                }} />
            )}
            <style dangerouslySetInnerHTML={{
                __html: `
                @keyframes blink {
                    from, to { opacity: 1; }
                    50% { opacity: 0; }
                }
            `}} />
        </div>
    );
};

export default TypingHighlightedText;
