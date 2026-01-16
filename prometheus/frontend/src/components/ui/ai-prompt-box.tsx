import { useState, useRef, useEffect } from 'react';
import { ArrowUp, Paperclip, Mic, Globe, Settings, Image as ImageIcon } from 'lucide-react';
import { motion } from 'framer-motion';

interface PromptInputBoxProps {
    onSend?: (message: string, files?: File[]) => void;
    isLoading?: boolean;
    placeholder?: string;
    className?: string;
    value?: string;
    onChange?: (value: string) => void;
}

export const PromptInputBox = ({
    onSend = () => { },
    placeholder = "e.g., Build a luxury car sales agent for Ferrari dealerships...",
    value: propValue,
    onChange,
    isLoading = false
}: PromptInputBoxProps) => {
    const [internalValue, setInternalValue] = useState("");
    const input = propValue !== undefined ? propValue : internalValue;

    const setInput = (val: string) => {
        if (onChange) {
            onChange(val);
        } else {
            setInternalValue(val);
        }
    };

    const [isRecording, setIsRecording] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + 'px';
        }
    }, [input]);

    const handleSubmit = () => {
        if (input.trim()) {
            onSend(input.trim());
            setInput("");
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    const hasContent = input.trim() !== "";

    return (
        <div style={{
            width: '100%',
            background: '#2D2E32',
            borderRadius: '28px',
            padding: '14px 20px',
            boxShadow: '0 8px 24px rgba(0, 0, 0, 0.25)',
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            gap: '16px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            transition: 'all 0.2s ease',
            position: 'relative'
        }}>
            {/* Left Icons Group */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                flexShrink: 0
            }}>
                <IconButton icon={<Paperclip size={18} />} />
                <IconButton icon={<Globe size={18} />} />
                <IconButton icon={<Settings size={18} />} />
                <IconButton icon={<ImageIcon size={18} />} />
            </div>

            {/* Textarea - Takes up remaining space */}
            <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center' }}>
                <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={isLoading ? "" : placeholder}
                    rows={1}
                    style={{
                        width: '100%',
                        background: 'transparent',
                        border: 'none',
                        outline: 'none',
                        color: '#FFFFFF',
                        fontSize: '14px',
                        fontFamily: 'Inter, system-ui, sans-serif',
                        resize: 'none',
                        minHeight: '24px',
                        maxHeight: '120px',
                        lineHeight: '1.5',
                        padding: '4px 0',
                        zIndex: 2
                    }}
                />

                {/* Blinking Cursor Indicator when waiting for user and no input */}
                {isLoading && !hasContent && (
                    <motion.div
                        animate={{ opacity: [0, 1, 0] }}
                        transition={{ repeat: Infinity, duration: 1 }}
                        style={{
                            position: 'absolute',
                            left: 0,
                            pointerEvents: 'none',
                            color: '#FFFFFF',
                            fontSize: '18px',
                            fontWeight: '300',
                            marginTop: '-1px'
                        }}
                    >
                        |
                    </motion.div>
                )}
            </div>

            {/* Right Mic/Send Button */}
            <button
                onClick={hasContent ? handleSubmit : () => setIsRecording(!isRecording)}
                style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    background: hasContent ? '#FFFFFF' : 'transparent',
                    border: 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    flexShrink: 0,
                    color: hasContent ? '#2D2E32' : '#9CA3AF'
                }}
                onMouseEnter={(e) => {
                    if (hasContent) {
                        e.currentTarget.style.background = '#F0F0F0';
                    } else {
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                    }
                }}
                onMouseLeave={(e) => {
                    e.currentTarget.style.background = hasContent ? '#FFFFFF' : 'transparent';
                }}
            >
                {hasContent ? (
                    <ArrowUp size={18} strokeWidth={2.5} />
                ) : (
                    <Mic size={18} />
                )}
            </button>
        </div>
    );
};

function IconButton({ icon }: { icon: React.ReactNode }) {
    return (
        <button
            style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'transparent',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: '#9CA3AF',
                transition: 'all 0.15s ease'
            }}
            onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                e.currentTarget.style.color = '#D1D5DB';
            }}
            onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
                e.currentTarget.style.color = '#9CA3AF';
            }}
        >
            {icon}
        </button>
    );
}
