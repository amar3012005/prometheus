import { useState, useRef, useEffect } from 'react';
import { useBuildStore } from '../store/buildStore';
import { useBuildSession } from '../hooks/useBuildSession';

export default function TestFlightPanel() {
    const { isReadyToTest, testHistory, addTestMessage, missionName } = useBuildStore();
    const { testAgent } = useBuildSession();
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [showPanel, setShowPanel] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [testHistory]);

    if (!isReadyToTest) return null;

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage = input.trim();
        setInput('');
        addTestMessage('user', userMessage);
        setLoading(true);

        try {
            const response = await testAgent(userMessage);
            addTestMessage('assistant', response);
        } catch (error) {
            addTestMessage('assistant', 'Error: Could not reach agent.');
        } finally {
            setLoading(false);
        }
    };

    if (!showPanel) {
        return (
            <button
                onClick={() => setShowPanel(true)}
                style={{
                    position: 'fixed',
                    bottom: '24px',
                    right: '24px',
                    padding: '14px 20px',
                    borderRadius: '10px',
                    background: '#FF4D00',
                    border: 'none',
                    color: 'white',
                    fontSize: '14px',
                    fontWeight: '600',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    boxShadow: '0 4px 12px rgba(255, 77, 0, 0.3)',
                    zIndex: 1000
                }}
            >
                <span className="material-icons-round" style={{ fontSize: '20px' }}>chat</span>
                Test Agent
            </button>
        );
    }

    return (
        <div style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.4)',
            zIndex: 2000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '40px'
        }}>
            <div style={{
                width: '100%',
                maxWidth: '500px',
                height: '70vh',
                maxHeight: '600px',
                background: '#FFFFFF',
                borderRadius: '16px',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                boxShadow: '0 24px 48px rgba(0, 0, 0, 0.15)'
            }}>
                {/* Header */}
                <div style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid #E5E5E5',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{
                            width: '36px',
                            height: '36px',
                            borderRadius: '8px',
                            background: '#FF4D00',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}>
                            <span className="material-icons-round" style={{ color: 'white', fontSize: '20px' }}>smart_toy</span>
                        </div>
                        <div>
                            <div style={{ fontWeight: '600', fontSize: '14px', color: '#0A0A0A' }}>
                                {missionName || 'Your Agent'}
                            </div>
                            <div style={{ fontSize: '11px', color: '#666' }}>Test Sandbox</div>
                        </div>
                    </div>
                    <button
                        onClick={() => setShowPanel(false)}
                        style={{
                            width: '32px',
                            height: '32px',
                            background: '#F5F5F5',
                            border: 'none',
                            borderRadius: '8px',
                            color: '#666',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <span className="material-icons-round" style={{ fontSize: '20px' }}>close</span>
                    </button>
                </div>

                {/* Chat Area */}
                <div style={{
                    flex: 1,
                    overflowY: 'auto',
                    padding: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '12px'
                }}>
                    {testHistory.length === 0 && (
                        <div style={{
                            textAlign: 'center',
                            color: '#999',
                            marginTop: '60px'
                        }}>
                            <span className="material-icons-round" style={{ fontSize: '48px', color: '#E5E5E5', marginBottom: '12px' }}>chat_bubble_outline</span>
                            <div style={{ fontSize: '14px', fontWeight: '500' }}>Start chatting</div>
                            <div style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>Test your agent's responses</div>
                        </div>
                    )}

                    {testHistory.map((msg, i) => (
                        <div
                            key={i}
                            style={{
                                alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                maxWidth: '80%'
                            }}
                        >
                            <div style={{
                                padding: '12px 16px',
                                borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                                background: msg.role === 'user' ? '#FF4D00' : '#F5F5F5',
                                color: msg.role === 'user' ? 'white' : '#0A0A0A',
                                fontSize: '14px',
                                lineHeight: '1.5'
                            }}>
                                {msg.content}
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div style={{
                            alignSelf: 'flex-start',
                            padding: '12px 16px',
                            borderRadius: '16px 16px 16px 4px',
                            background: '#F5F5F5',
                            color: '#999',
                            fontSize: '14px'
                        }}>
                            Thinking...
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input Area */}
                <div style={{
                    padding: '16px 20px',
                    borderTop: '1px solid #E5E5E5',
                    display: 'flex',
                    gap: '10px'
                }}>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                        placeholder="Type a message..."
                        style={{
                            flex: 1,
                            padding: '12px 16px',
                            background: '#F5F5F5',
                            border: 'none',
                            borderRadius: '10px',
                            color: '#0A0A0A',
                            fontSize: '14px',
                            outline: 'none'
                        }}
                        disabled={loading}
                    />
                    <button
                        onClick={handleSend}
                        disabled={loading || !input.trim()}
                        style={{
                            width: '44px',
                            height: '44px',
                            borderRadius: '10px',
                            background: loading || !input.trim() ? '#E5E5E5' : '#FF4D00',
                            border: 'none',
                            color: loading || !input.trim() ? '#999' : 'white',
                            cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <span className="material-icons-round" style={{ fontSize: '20px' }}>send</span>
                    </button>
                </div>
            </div>
        </div>
    );
}
