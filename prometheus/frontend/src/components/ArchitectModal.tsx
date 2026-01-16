import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useBuildStore } from '../store/buildStore';
import { config } from '../config';

export default function ArchitectModal() {
    const { showModal, architectQuestion, setShowModal, sessionId } = useBuildStore();
    const [response, setResponse] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async () => {
        if (!response.trim() || isSubmitting) return;
        setIsSubmitting(true);

        try {
            const res = await fetch(`${config.apiUrl}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: response,
                    session_id: sessionId
                })
            });

            if (res.ok) {
                setShowModal(false);
                setResponse('');
            }
        } catch (error) {
            console.error('Error submitting clarification:', error);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <AnimatePresence>
            {showModal && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    style={{
                        position: 'fixed',
                        inset: 0,
                        background: 'rgba(0, 0, 0, 0.5)',
                        backdropFilter: 'blur(8px)',
                        zIndex: 3000,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        padding: '24px'
                    }}
                    onClick={() => setShowModal(false)}
                >
                    <motion.div
                        initial={{ scale: 0.9, opacity: 0, rotateX: 10 }}
                        animate={{ scale: 1, opacity: 1, rotateX: 0 }}
                        exit={{ scale: 0.95, opacity: 0, rotateX: -5 }}
                        transition={{
                            type: 'spring',
                            stiffness: 300,
                            damping: 25
                        }}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                            width: '100%',
                            maxWidth: '520px',
                            background: 'linear-gradient(135deg, #FFFFFF 0%, #FAFAFA 100%)',
                            borderRadius: '20px',
                            boxShadow: '0 32px 64px rgba(0, 0, 0, 0.2), 0 0 0 1px rgba(0, 0, 0, 0.05)',
                            overflow: 'hidden',
                            border: '1px solid rgba(255, 255, 255, 0.8)'
                        }}
                    >
                        {/* Flash Card Header */}
                        <div style={{
                            padding: '24px',
                            background: 'linear-gradient(135deg, #FF4D00 0%, #FF6B2C 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '14px'
                        }}>
                            <motion.div
                                initial={{ rotate: -10, scale: 0.8 }}
                                animate={{ rotate: 0, scale: 1 }}
                                transition={{ delay: 0.1, type: 'spring' }}
                                style={{
                                    width: '48px',
                                    height: '48px',
                                    borderRadius: '12px',
                                    background: 'rgba(255, 255, 255, 0.2)',
                                    backdropFilter: 'blur(10px)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    border: '2px solid rgba(255, 255, 255, 0.3)'
                                }}
                            >
                                <span className="material-icons-round" style={{ fontSize: '26px', color: 'white' }}>
                                    psychology
                                </span>
                            </motion.div>
                            <div>
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: 0.15 }}
                                    style={{ fontWeight: '700', fontSize: '18px', color: 'white' }}
                                >
                                    🤖 Architect Needs Clarification
                                </motion.div>
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: 0.2 }}
                                    style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.9)' }}
                                >
                                    Help me understand your requirements better
                                </motion.div>
                            </div>
                        </div>

                        {/* Content */}
                        <div style={{ padding: '28px' }}>
                            {/* Question Card */}
                            <motion.div
                                initial={{ y: 10, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.25 }}
                                style={{
                                    padding: '20px',
                                    background: '#F8F9FA',
                                    border: '2px solid #E9ECEF',
                                    borderRadius: '12px',
                                    marginBottom: '20px',
                                    position: 'relative'
                                }}
                            >
                                {/* Quote mark decoration */}
                                <div style={{
                                    position: 'absolute',
                                    top: '12px',
                                    left: '12px',
                                    fontSize: '48px',
                                    color: '#FF4D00',
                                    opacity: 0.1,
                                    fontFamily: 'Georgia, serif',
                                    lineHeight: 1
                                }}>
                                    "
                                </div>
                                <div style={{
                                    fontSize: '15px',
                                    color: '#1A1A1A',
                                    lineHeight: '1.7',
                                    position: 'relative',
                                    zIndex: 1
                                }}>
                                    {architectQuestion}
                                </div>
                            </motion.div>

                            {/* Response Input */}
                            <motion.div
                                initial={{ y: 10, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.3 }}
                            >
                                <label style={{
                                    display: 'block',
                                    fontSize: '13px',
                                    fontWeight: '600',
                                    color: '#666',
                                    marginBottom: '10px',
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.5px'
                                }}>
                                    Your Response
                                </label>
                                <textarea
                                    value={response}
                                    onChange={(e) => setResponse(e.target.value)}
                                    placeholder="Type your clarification here..."
                                    autoFocus
                                    style={{
                                        width: '100%',
                                        height: '120px',
                                        padding: '16px',
                                        background: '#FFFFFF',
                                        border: '2px solid #E0E0E0',
                                        borderRadius: '12px',
                                        color: '#0A0A0A',
                                        fontSize: '15px',
                                        lineHeight: '1.6',
                                        resize: 'none',
                                        outline: 'none',
                                        fontFamily: 'Inter, sans-serif',
                                        transition: 'all 0.2s ease',
                                        boxShadow: 'inset 0 1px 3px rgba(0, 0, 0, 0.05)'
                                    }}
                                    onFocus={(e) => {
                                        e.target.style.borderColor = '#FF4D00';
                                        e.target.style.boxShadow = '0 0 0 3px rgba(255, 77, 0, 0.1)';
                                    }}
                                    onBlur={(e) => {
                                        e.target.style.borderColor = '#E0E0E0';
                                        e.target.style.boxShadow = 'inset 0 1px 3px rgba(0, 0, 0, 0.05)';
                                    }}
                                />
                            </motion.div>

                            {/* Actions */}
                            <motion.div
                                initial={{ y: 10, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: 0.35 }}
                                style={{
                                    display: 'flex',
                                    gap: '12px',
                                    marginTop: '20px'
                                }}
                            >
                                <button
                                    onClick={() => setShowModal(false)}
                                    style={{
                                        flex: 1,
                                        padding: '14px',
                                        background: '#F5F5F5',
                                        border: '2px solid #E5E5E5',
                                        borderRadius: '10px',
                                        color: '#666',
                                        fontSize: '15px',
                                        fontWeight: '600',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s ease'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.background = '#ECECEC';
                                        e.currentTarget.style.borderColor = '#D0D0D0';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.background = '#F5F5F5';
                                        e.currentTarget.style.borderColor = '#E5E5E5';
                                    }}
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleSubmit}
                                    disabled={isSubmitting || !response.trim()}
                                    style={{
                                        flex: 2,
                                        padding: '14px',
                                        background: response.trim()
                                            ? 'linear-gradient(135deg, #FF4D00 0%, #FF6B2C 100%)'
                                            : '#E5E5E5',
                                        border: 'none',
                                        borderRadius: '10px',
                                        color: response.trim() ? 'white' : '#999',
                                        fontSize: '15px',
                                        fontWeight: '700',
                                        cursor: response.trim() ? 'pointer' : 'not-allowed',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        gap: '8px',
                                        transition: 'all 0.2s ease',
                                        boxShadow: response.trim()
                                            ? '0 4px 12px rgba(255, 77, 0, 0.3)'
                                            : 'none'
                                    }}
                                    onMouseEnter={(e) => {
                                        if (response.trim()) {
                                            e.currentTarget.style.transform = 'translateY(-1px)';
                                            e.currentTarget.style.boxShadow = '0 6px 16px rgba(255, 77, 0, 0.4)';
                                        }
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.transform = 'translateY(0)';
                                        e.currentTarget.style.boxShadow = response.trim()
                                            ? '0 4px 12px rgba(255, 77, 0, 0.3)'
                                            : 'none';
                                    }}
                                >
                                    {isSubmitting ? (
                                        <>
                                            <motion.span
                                                animate={{ rotate: 360 }}
                                                transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                                                className="material-icons-round"
                                                style={{ fontSize: '18px' }}
                                            >
                                                sync
                                            </motion.span>
                                            Sending...
                                        </>
                                    ) : (
                                        <>
                                            <span className="material-icons-round" style={{ fontSize: '18px' }}>
                                                send
                                            </span>
                                            Submit Response
                                        </>
                                    )}
                                </button>
                            </motion.div>
                        </div>
                    </motion.div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
