import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { config } from '../config';

interface Agent {
    session_id: string;
    agent_id: string;
    name: string;
    config_path: string;
    created_at: number;
}

interface MyAgentsViewProps {
    onStartConversation: (agentId: string, agentName: string) => void;
}

export default function MyAgentsView({ onStartConversation }: MyAgentsViewProps) {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        fetchAgents();
    }, []);

    const fetchAgents = async () => {
        try {
            setLoading(true);
            const response = await fetch(`${config.apiUrl}/api/agents`);
            if (!response.ok) throw new Error('Failed to fetch agents');

            const data = await response.json();
            setAgents(data.agents || []);
            setError(null);
        } catch (err) {
            setError('Failed to load agents');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const formatDate = (timestamp: number) => {
        return new Date(timestamp * 1000).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div style={{
            flex: 1,
            padding: '40px',
            overflowY: 'auto',
            background: '#FAFAFA'
        }}>
            {/* Header */}
            <div style={{
                marginBottom: '32px'
            }}>
                <h1 style={{
                    fontSize: '28px',
                    fontWeight: '800',
                    color: '#0A0A0A',
                    letterSpacing: '-0.02em',
                    marginBottom: '8px'
                }}>
                    My Agents
                </h1>
                <p style={{
                    fontSize: '14px',
                    color: '#666'
                }}>
                    All your deployed voice agents. Click to start a conversation.
                </p>
            </div>

            {/* Loading State */}
            {loading && (
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '60px',
                    color: '#999'
                }}>
                    <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                        style={{
                            width: '24px',
                            height: '24px',
                            border: '3px solid #E5E5E5',
                            borderTopColor: '#FF4D00',
                            borderRadius: '50%'
                        }}
                    />
                </div>
            )}

            {/* Error State */}
            {error && (
                <div style={{
                    padding: '40px',
                    textAlign: 'center',
                    color: '#DC2626'
                }}>
                    <span className="material-icons-round" style={{ fontSize: '48px', marginBottom: '16px', display: 'block' }}>error</span>
                    <p>{error}</p>
                    <button
                        onClick={fetchAgents}
                        style={{
                            marginTop: '16px',
                            padding: '8px 16px',
                            background: '#FF4D00',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: '600'
                        }}
                    >
                        Retry
                    </button>
                </div>
            )}

            {/* Empty State */}
            {!loading && !error && agents.length === 0 && (
                <div style={{
                    padding: '60px',
                    textAlign: 'center',
                    color: '#999'
                }}>
                    <span className="material-icons-round" style={{ fontSize: '64px', marginBottom: '16px', display: 'block', color: '#E5E5E5' }}>smart_toy</span>
                    <h3 style={{ fontSize: '18px', fontWeight: '600', color: '#666', marginBottom: '8px' }}>No agents yet</h3>
                    <p style={{ fontSize: '14px' }}>Create your first voice agent to get started.</p>
                </div>
            )}

            {/* Agents Grid */}
            {!loading && !error && agents.length > 0 && (
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
                    gap: '20px'
                }}>
                    <AnimatePresence>
                        {agents.map((agent, index) => (
                            <motion.div
                                key={agent.agent_id}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.05 }}
                                style={{
                                    background: '#FFFFFF',
                                    borderRadius: '12px',
                                    border: '1px solid #E5E5E5',
                                    padding: '24px',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease'
                                }}
                                whileHover={{
                                    y: -4,
                                    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.08)'
                                }}
                                onClick={() => onStartConversation(agent.agent_id, agent.name)}
                            >
                                {/* Agent Icon & Name */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '14px',
                                    marginBottom: '16px'
                                }}>
                                    <div style={{
                                        width: '48px',
                                        height: '48px',
                                        background: 'linear-gradient(135deg, #FF4D00, #FF6B2C)',
                                        borderRadius: '12px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        boxShadow: '0 4px 12px rgba(255, 77, 0, 0.2)'
                                    }}>
                                        <span className="material-icons-round" style={{ color: 'white', fontSize: '24px' }}>
                                            smart_toy
                                        </span>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <h3 style={{
                                            fontSize: '16px',
                                            fontWeight: '700',
                                            color: '#0A0A0A',
                                            marginBottom: '4px'
                                        }}>
                                            {agent.name}
                                        </h3>
                                        <div style={{
                                            fontSize: '11px',
                                            color: '#999',
                                            fontFamily: 'JetBrains Mono, monospace'
                                        }}>
                                            {agent.agent_id.substring(0, 20)}...
                                        </div>
                                    </div>
                                </div>

                                {/* Status & Action */}
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between'
                                }}>
                                    <div style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '6px',
                                        padding: '4px 10px',
                                        background: '#DEF7EC',
                                        borderRadius: '20px'
                                    }}>
                                        <div style={{
                                            width: '6px',
                                            height: '6px',
                                            borderRadius: '50%',
                                            background: '#22C55E'
                                        }} />
                                        <span style={{
                                            fontSize: '11px',
                                            fontWeight: '600',
                                            color: '#15803D'
                                        }}>
                                            Live
                                        </span>
                                    </div>

                                    <button
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '6px',
                                            padding: '8px 16px',
                                            background: '#0A0A0A',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '8px',
                                            fontSize: '12px',
                                            fontWeight: '600',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        <span className="material-icons-round" style={{ fontSize: '16px' }}>play_arrow</span>
                                        Talk
                                    </button>
                                </div>

                                {/* Created Date */}
                                <div style={{
                                    marginTop: '16px',
                                    paddingTop: '16px',
                                    borderTop: '1px solid #F3F4F6',
                                    fontSize: '11px',
                                    color: '#999'
                                }}>
                                    Created {formatDate(agent.created_at)}
                                </div>
                            </motion.div>
                        ))}
                    </AnimatePresence>
                </div>
            )}
        </div>
    );
}
