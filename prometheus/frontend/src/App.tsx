import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import Sidebar from './components/Sidebar';
import HeroPrompt from './components/HeroPrompt';
import BuilderSheet from './components/BuilderSheet';
import DeploySheet from './components/DeploySheet';
import TestFlightPanel from './components/TestFlightPanel';
import AnimatedBackground from './components/AnimatedBackground';
import MyAgentsView from './components/MyAgentsView';
import { useBuildSession } from './hooks/useBuildSession';
import { useBuildStore } from './store/buildStore';
import { config } from './config';

interface Agent {
    session_id: string;
    agent_id: string;
    name: string;
    created_at: number;
}

function App() {
    const {
        isBuilding,
        isReadyToTest,
        hasError,
        missionName,
        builderWidth,
        showDeploySheet,
        setShowDeploySheet,
        setDeployedAgentId,
        setMissionName
    } = useBuildStore();
    const { startBuild, selectVoice } = useBuildSession();

    const [currentView, setCurrentView] = useState<'builder' | 'agents' | 'settings'>('builder');
    const [recentAgents, setRecentAgents] = useState<Agent[]>([]);

    // Fetch agents list for sidebar
    useEffect(() => {
        const fetchAgents = async () => {
            try {
                const res = await fetch(`${config.apiUrl}/api/agents`);
                if (res.ok) {
                    const data = await res.json();
                    setRecentAgents(data.agents || []);
                }
            } catch (err) {
                console.error('Failed to fetch agents:', err);
            }
        };
        fetchAgents();
    }, [isReadyToTest]); // Refetch when a new agent is ready

    const handleSubmit = async (prompt: string) => {
        await startBuild(prompt);
    };

    const handleStartConversation = (agentId: string, agentName: string) => {
        console.log('[APP] Starting conversation with agent:', agentId, agentName);
        setDeployedAgentId(agentId);
        setMissionName(agentName);
        setShowDeploySheet(true);
        setCurrentView('builder'); // Switch to builder view to show DeploySheet
    };

    const handleNavigation = (view: string) => {
        setCurrentView(view as 'builder' | 'agents' | 'settings');
        // Close deploy sheet when switching views
        if (view !== 'builder') {
            setShowDeploySheet(false);
        }
    };

    const isBuilderOpen = (isBuilding || isReadyToTest || hasError) && !showDeploySheet;
    const isAnyPanelOpen = isBuilderOpen || showDeploySheet;

    return (
        <div style={{
            display: 'flex',
            height: '100vh',
            overflow: 'hidden',
            background: '#FFFFFF'
        }}>
            <AnimatedBackground />

            <Sidebar
                onNavigate={handleNavigation}
                agents={recentAgents}
                onAgentClick={handleStartConversation}
            />

            {/* Main Content Area */}
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                position: 'relative'
            }}>
                {/* Top Bar */}
                <div style={{
                    height: '52px',
                    padding: '0 20px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: '1px solid #E5E5E5',
                    background: '#FFFFFF',
                    zIndex: 40
                }}>
                    {/* Left: Project Info */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        {isAnyPanelOpen && (
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '10px'
                            }}>
                                <div style={{
                                    width: '8px',
                                    height: '8px',
                                    borderRadius: '50%',
                                    background: isReadyToTest ? '#22C55E' : '#FF4D00',
                                    animation: isBuilding ? 'pulse 1.5s infinite' : 'none'
                                }} />
                                <span style={{
                                    fontSize: '14px',
                                    fontWeight: '600',
                                    color: '#0A0A0A'
                                }}>
                                    {missionName || 'New Agent'}
                                </span>
                            </div>
                        )}
                    </div>

                    {/* Right: Actions */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <TopBarButton
                            icon="rocket_launch"
                            label="Test Flight"
                            active={showDeploySheet}
                            onClick={() => setShowDeploySheet(!showDeploySheet)}
                        />
                        <div style={{ width: '1px', height: '20px', background: '#E5E5E5', margin: '0 8px' }} />
                        <TopBarButton icon="history" />
                        <TopBarButton icon="code" />

                        <button
                            disabled={!isReadyToTest}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '6px',
                                background: isReadyToTest ? '#FF4D00' : '#F0F0F0',
                                border: 'none',
                                cursor: isReadyToTest ? 'pointer' : 'not-allowed',
                                fontSize: '13px',
                                fontWeight: '600',
                                color: isReadyToTest ? 'white' : '#999',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '6px'
                            }}
                        >
                            <span className="material-icons-round" style={{ fontSize: '16px' }}>publish</span>
                            Publish
                        </button>
                    </div>
                </div>

                {/* Main Stage - View Switching */}
                <div style={{
                    flex: 1,
                    position: 'relative',
                    overflow: 'hidden',
                    display: 'flex'
                }}>
                    {/* Builder View (New Agent) */}
                    {currentView === 'builder' && (
                        <>
                            {/* Hero Prompt */}
                            <motion.div
                                animate={{
                                    marginRight: isAnyPanelOpen ? builderWidth : 0
                                }}
                                transition={{
                                    type: 'spring',
                                    damping: 30,
                                    stiffness: 300
                                }}
                                style={{
                                    flex: 1,
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    height: '100%'
                                }}
                            >
                                <HeroPrompt onSubmit={handleSubmit} />
                            </motion.div>

                            {/* Builder Panel */}
                            <BuilderSheet
                                isOpen={isBuilderOpen}
                                onSelectVoice={selectVoice}
                            />

                            {/* Deploy Panel */}
                            <DeploySheet />
                        </>
                    )}

                    {/* My Agents View */}
                    {currentView === 'agents' && (
                        <MyAgentsView onStartConversation={handleStartConversation} />
                    )}

                    {/* Settings View */}
                    {currentView === 'settings' && (
                        <div style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: '#999'
                        }}>
                            <div style={{ textAlign: 'center' }}>
                                <span className="material-icons-round" style={{ fontSize: '64px', color: '#E5E5E5', marginBottom: '16px', display: 'block' }}>settings</span>
                                <h2 style={{ fontSize: '20px', fontWeight: '600', color: '#666' }}>Settings</h2>
                                <p>Coming soon...</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            <TestFlightPanel />
        </div>
    );
}

function TopBarButton({ icon, label, active, onClick }: { icon: string, label?: string, active?: boolean, onClick?: () => void }) {
    return (
        <button
            onClick={onClick}
            style={{
                padding: label ? '6px 12px' : '8px',
                background: active ? 'rgba(255, 77, 0, 0.08)' : 'transparent',
                border: active ? '1px solid rgba(255, 77, 0, 0.2)' : '1px solid transparent',
                cursor: 'pointer',
                color: active ? '#FF4D00' : '#666',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'all 0.2s ease'
            }}
        >
            <span className="material-icons-round" style={{ fontSize: '20px' }}>{icon}</span>
            {label && <span style={{ fontSize: '13px', fontWeight: '600' }}>{label}</span>}
        </button>
    );
}

export default App;
