import { useState } from 'react';

interface SidebarProps {
    onNavigate?: (view: string) => void;
    agents?: Array<{ name: string; agent_id: string }>;
    onAgentClick?: (agentId: string, name: string) => void;
}

export default function Sidebar({ onNavigate, agents = [], onAgentClick }: SidebarProps) {
    const [activeItem, setActiveItem] = useState('builder');

    const handleNavigation = (item: string) => {
        setActiveItem(item);
        onNavigate?.(item);
    };

    return (
        <div style={{
            width: '260px',
            background: '#FAFAFA',
            borderRight: '1px solid #E5E5E5',
            padding: '0',
            display: 'flex',
            flexDirection: 'column',
            fontFamily: 'Inter, sans-serif',
            height: '100vh',
            position: 'relative',
            zIndex: 50
        }}>
            {/* Brand Header */}
            <div style={{
                padding: '24px 20px',
                borderBottom: '1px solid #E5E5E5'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                }}>
                    <div style={{
                        width: '36px',
                        height: '36px',
                        background: '#FF4D00',
                        borderRadius: '8px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <span className="material-icons-round" style={{ fontSize: '20px', color: 'white' }}>bolt</span>
                    </div>
                    <div>
                        <div style={{
                            fontFamily: 'Outfit, sans-serif',
                            fontWeight: '700',
                            fontSize: '16px',
                            letterSpacing: '-0.02em',
                            color: '#0A0A0A'
                        }}>
                            PROMETHEUS
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Navigation */}
            <div style={{ padding: '16px 12px', flex: 1, overflowY: 'auto' }}>
                {/* Primary Actions */}
                <div style={{ marginBottom: '24px' }}>
                    <NavItem
                        icon="add_circle"
                        label="New Agent"
                        active={activeItem === 'builder'}
                        onClick={() => handleNavigation('builder')}
                    />
                    <NavItem
                        icon="folder"
                        label="My Agents"
                        active={activeItem === 'agents'}
                        onClick={() => handleNavigation('agents')}
                    />
                    <NavItem
                        icon="settings"
                        label="Settings"
                        active={activeItem === 'settings'}
                        onClick={() => handleNavigation('settings')}
                    />
                </div>

                {/* Recent Agents */}
                {agents.length > 0 && (
                    <div>
                        <SectionHeader>Recent</SectionHeader>
                        {agents.slice(0, 5).map(agent => (
                            <AgentItem
                                key={agent.agent_id}
                                name={agent.name}
                                onClick={() => onAgentClick?.(agent.agent_id, agent.name)}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Bottom Section */}
            <div style={{
                padding: '16px 20px',
                borderTop: '1px solid #E5E5E5'
            }}>
                <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px'
                }}>
                    <div style={{
                        width: '32px',
                        height: '32px',
                        borderRadius: '50%',
                        background: '#E5E5E5',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center'
                    }}>
                        <span className="material-icons-round" style={{ fontSize: '18px', color: '#666' }}>person</span>
                    </div>
                    <div style={{ flex: 1 }}>
                        <div style={{ fontSize: '13px', fontWeight: '600', color: '#0A0A0A' }}>Amar</div>
                        <div style={{ fontSize: '11px', color: '#999' }}>Pro Plan</div>
                    </div>
                </div>
            </div>
        </div>
    );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
    return (
        <div style={{
            padding: '0 8px 8px',
            fontSize: '11px',
            fontWeight: '600',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            color: '#999'
        }}>
            {children}
        </div>
    );
}

function NavItem({
    icon,
    label,
    active = false,
    onClick
}: {
    icon: string;
    label: string;
    active?: boolean;
    onClick?: () => void;
}) {
    return (
        <div
            onClick={onClick}
            style={{
                padding: '10px 12px',
                borderRadius: '8px',
                fontSize: '14px',
                fontWeight: '500',
                color: active ? '#0A0A0A' : '#666',
                background: active ? '#FFFFFF' : 'transparent',
                border: active ? '1px solid #E5E5E5' : '1px solid transparent',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                marginBottom: '4px',
                transition: 'all 0.15s ease'
            }}
        >
            <span
                className="material-icons-round"
                style={{
                    fontSize: '20px',
                    color: active ? '#FF4D00' : '#999'
                }}
            >
                {icon}
            </span>
            <span>{label}</span>
        </div>
    );
}

function AgentItem({ name, onClick }: { name: string; onClick?: () => void }) {
    return (
        <div
            onClick={onClick}
            style={{
                padding: '8px 12px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                marginBottom: '2px',
                color: '#666',
                fontSize: '13px',
                transition: 'background 0.15s ease'
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#F3F4F6')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
            <span className="material-icons-round" style={{ fontSize: '16px', color: '#CCC' }}>smart_toy</span>
            <span style={{ flex: 1 }}>{name}</span>
            <span className="material-icons-round" style={{ fontSize: '16px', color: '#DDD' }}>play_circle</span>
        </div>
    );
}
