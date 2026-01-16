import { useRef, useCallback, useEffect } from 'react';
import { useBuildStore } from '../store/buildStore';
import { config } from '../config';

const BACKEND_URL = config.apiUrl;
const WS_URL = config.wsUrl;

// Phase detection based on backend log messages
const PHASE_TRIGGERS: Record<string, number> = {
    'Provisioning isolated namespace': 0,
    'Deploying Redis Cluster': 1,
    'Initializing MMAR Logic Engine': 2,
    'Calibrating TTS Voice': 3,
    'Deploying Multi-Agent Orchestrator': 4,
    'Applying Helm values': 5,
    'Verifying pod health': 6
};

export function useBuildSession() {
    const wsRef = useRef<WebSocket | null>(null);
    const messageHandlerRef = useRef<((message: any) => void) | null>(null);
    const pendingVoiceRef = useRef<string | null>(null); // Queue voice selection if WS not ready

    const {
        setIsBuilding,
        setMissionName,
        setSessionId,
        setArchitectQuestion,
        setShowModal,
        setIsReadyToTest,
        setHasError,
        setDeploymentUrl,
        setVoiceCandidates,
        setShowVoiceSelector,
        setSelectedVoiceId,
        addTerminalLog,
        clearTerminalLogs,
        setCurrentPhase,
        setPhaseStatus,
        advancePhase,
        resetPhases,
        addBuildMessage,
        addChecklistTag,
        setChecklistTagStatus,
        clearChecklistTags,
        setExtractedFields,
        setIsArchitectThinking,
        setContextComplete,
        setIsPipelineStarted,
        setIsVoiceSelected,
        setIsKbReady,
        setShowDeploySheet,
        setDeployedAgentId,
        setAgentState,
        setSuggestions
    } = useBuildStore();

    // Detect which phase we're in based on log message
    const detectPhase = useCallback((message: string) => {
        for (const [trigger, phaseIndex] of Object.entries(PHASE_TRIGGERS)) {
            if (message.includes(trigger)) {
                setCurrentPhase(phaseIndex);
                return;
            }
        }
    }, [setCurrentPhase]);

    // Handle incoming WebSocket messages
    const handleWebSocketMessage = useCallback((message: any) => {
        console.log('[WS] Received message:', message);
        const { type, data } = message;

        switch (type) {
            case 'LOG':
                addTerminalLog(data.phase || 'SYSTEM', data.message || '');

                if (data.message) {
                    detectPhase(data.message);

                    if (data.message.includes("🧠 Activating Deep Logic Engine")) {
                        setContextComplete(true);
                        setChecklistTagStatus('context', 'done');
                        addChecklistTag('kb', 'Generating knowledge base');
                        setChecklistTagStatus('kb', 'active');
                    }

                    // KB or Config ready - set the flag
                    if (data.message.includes("✅ Knowledge base ready") ||
                        data.message.includes("✅ Knowledge base generated") ||
                        data.message.includes("✅ Configuration artifacts ready")) {
                        setChecklistTagStatus('kb', 'done');
                        setChecklistTagStatus('kb-extraction', 'done'); // Also mark extraction done
                        setIsKbReady(true);
                        addTerminalLog('SYSTEM', '✅ Knowledge base generation complete');
                    }

                    if (data.message.includes('✓') && data.message.includes('ready')) {
                        advancePhase();
                    }
                }

                // 🔥 READY TO BUILD - Backend signals all manufacturing is complete
                if (data.ready_to_build === true) {
                    console.log('[WS] 🔥 READY TO BUILD signal received!');
                    setContextComplete(true);
                    setIsKbReady(true);
                    setChecklistTagStatus('kb', 'done');
                    setChecklistTagStatus('voice', 'done');
                    addTerminalLog('READY', '🔥 All artifacts manufactured. Ready to deploy!');
                }


                // Voice candidates received - only show if not already selected
                if (data.voice_candidates && data.voice_candidates.length > 0) {
                    const state = useBuildStore.getState();

                    // Skip if voice already selected
                    if (state.isVoiceSelected || state.selectedVoiceId) {
                        console.log('[WS] Voice candidates received but voice already selected - skipping popup');
                        return;
                    }

                    console.log('[WS] 🎙️ Voice candidates RECEIVED:', data.voice_candidates.length);
                    setVoiceCandidates(data.voice_candidates);
                    setShowVoiceSelector(true);
                    setChecklistTagStatus('voice-search', 'done');
                    addChecklistTag('voice', 'Select your voice');
                    setChecklistTagStatus('voice', 'active');
                    addTerminalLog('VOICE', `${data.voice_candidates.length} voices available`);
                }

                if (data.extracted_fields) {
                    setExtractedFields(data.extracted_fields);
                }
                break;

            case 'BUILD_COMPLETE':
                setIsBuilding(false);
                setIsReadyToTest(true);
                setDeploymentUrl(data.deployment_url);
                setCurrentPhase(6);
                setPhaseStatus(6, 'completed');
                addTerminalLog('DEPLOYED', `✅ Agent deployed at: ${data.deployment_url}`);
                break;

            case 'DEPLOYMENT_COMPLETE':
                setIsBuilding(false);
                setIsReadyToTest(true);
                setDeploymentUrl(data.deployment_url);
                setDeployedAgentId(data.agent_id);
                setCurrentPhase(6);
                setPhaseStatus(6, 'completed');
                addTerminalLog('DEPLOYED', `🚀 Agent successfully deployed to ElevenLabs: ${data.agent_id}`);

                // Transition to DeploySheet
                setShowDeploySheet(true);
                break;

            case 'PHASE_BUILDING':
                addTerminalLog('SYSTEM', data.message);
                break;

            case 'STATUS_UPDATE':
                addTerminalLog('SYSTEM', data.message);
                if (data.extracted_fields) {
                    setExtractedFields(data.extracted_fields);

                    // Sync mission name if it just arrived
                    const fields = data.extracted_fields;
                    if (fields.agent_name) {
                        setMissionName(fields.agent_name);
                    } else if (fields.org_name && !useBuildStore.getState().missionName) {
                        setMissionName(fields.org_name);
                    }
                }
                break;

            case 'ERROR':
                setHasError(true);
                setIsBuilding(false);
                addTerminalLog('ERROR', data.message);
                break;
        }
    }, [addTerminalLog, detectPhase, advancePhase, setVoiceCandidates, setShowVoiceSelector, setIsBuilding, setIsReadyToTest, setDeploymentUrl, setCurrentPhase, setPhaseStatus, setHasError, setChecklistTagStatus, addChecklistTag, setExtractedFields, setIsKbReady, setShowDeploySheet, setDeployedAgentId, setAgentState]);

    useEffect(() => {
        messageHandlerRef.current = handleWebSocketMessage;
    }, [handleWebSocketMessage]);

    const reconnectTimeoutRef = useRef<number | null>(null);

    // Connect WebSocket for real-time events
    const connectWebSocket = useCallback((sid: string) => {
        if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
            return;
        }

        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
        }

        const tenantQuery = config.tenantId ? `?x_tenant_id=${config.tenantId}` : '';
        const ws = new WebSocket(`${WS_URL}/ws/${sid}${tenantQuery}`);
        wsRef.current = ws;

        ws.onopen = () => {
            console.log('[WS] Connected to', sid);
            addTerminalLog('SYSTEM', 'Connected to build server');

            // Send any pending voice selection
            if (pendingVoiceRef.current) {
                ws.send(JSON.stringify({ type: 'VOICE_SELECTED', voice_id: pendingVoiceRef.current }));
                addTerminalLog('SYSTEM', '🚀 Voice selection sent');
                pendingVoiceRef.current = null;
            }
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);
                if (messageHandlerRef.current) {
                    messageHandlerRef.current(message);
                }
            } catch (e) {
                console.error('WS parse error:', e);
            }
        };

        ws.onclose = () => {
            console.log('WS closed - attempting to reconnect...');
            reconnectTimeoutRef.current = setTimeout(() => {
                connectWebSocket(sid);
            }, 2000);
        };
    }, [addTerminalLog]);

    // Start a new build session
    const startBuild = useCallback(async (prompt: string) => {
        resetPhases();
        clearTerminalLogs();
        setHasError(false);
        setIsReadyToTest(false);
        setShowVoiceSelector(false);
        setSelectedVoiceId(null);
        setContextComplete(false);
        setIsPipelineStarted(false);
        setIsVoiceSelected(false);
        setIsKbReady(false);
        setIsBuilding(true);
        clearChecklistTags();

        addBuildMessage('user', prompt);
        addTerminalLog('INIT', `🚀 Initializing build system...`);

        await new Promise(resolve => setTimeout(resolve, 300));
        addChecklistTag('context', 'Extracting context');
        setChecklistTagStatus('context', 'active');

        try {
            addTerminalLog('SYSTEM', `📡 Connecting to backend...`);
            setIsArchitectThinking(true);

            const response = await fetch(`${BACKEND_URL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': config.tenantId
                },
                body: JSON.stringify({ message: prompt })
            });

            const data = await response.json();
            setIsArchitectThinking(false);

            if (!response.ok) {
                throw new Error(data.message || 'Server error during extraction');
            }

            const newSessionId = data.session_id;
            if (!newSessionId) {
                throw new Error('No session ID returned from backend');
            }

            setSessionId(newSessionId);

            // Connect WS immediately for real-time updates
            connectWebSocket(newSessionId);

            if (data.extracted_fields) {
                setExtractedFields(data.extracted_fields);
                if (data.extracted_fields.voice_parameters) {
                    addChecklistTag('voice-search', 'Searching voices');
                    setChecklistTagStatus('voice-search', 'active');
                }
            }

            if (data.voice_candidates && data.voice_candidates.length > 0) {
                setVoiceCandidates(data.voice_candidates);
                setShowVoiceSelector(true);
                setChecklistTagStatus('voice-search', 'done');
                addChecklistTag('voice', 'Select your voice');
                setChecklistTagStatus('voice', 'active');
            }

            if (data.selected_voice_id) {
                console.log('[SYNC] Voice already selected:', data.selected_voice_id);
                setSelectedVoiceId(data.selected_voice_id);
                setIsVoiceSelected(true);
                setShowVoiceSelector(false);
            }

            // Mission Name logic: Agent Name > Org Name > fallback
            const fields = data.extracted_fields || {};
            if (fields.agent_name) {
                setMissionName(fields.agent_name);
                addTerminalLog('SYSTEM', `✅ Agent: ${fields.agent_name}`);
            } else if (fields.org_name) {
                setMissionName(fields.org_name);
                addTerminalLog('SYSTEM', `🏢 Organization: ${fields.org_name}`);
            } else {
                setMissionName('New Agent');
            }

            addTerminalLog('SYSTEM', `🆔 Session: ${newSessionId.slice(0, 8)}...`);

            if (data.clarification) {
                setArchitectQuestion(data.clarification);
                setShowModal(true);
                addTerminalLog('SYSTEM', '💬 Architect needs clarification...');
                addBuildMessage('assistant', data.clarification);
                return;
            }

            // If complete already (unlikely on first call), mark context done
            if (data.is_complete) {
                setContextComplete(true);
                setChecklistTagStatus('context', 'done');
            }

        } catch (error) {
            console.error('Build error:', error);
            addTerminalLog('ERROR', `❌ Build failed: ${error}`);
            setHasError(true);
            setIsBuilding(false);
        }
    }, [resetPhases, clearTerminalLogs, setHasError, setIsReadyToTest, setShowVoiceSelector, setIsBuilding, addTerminalLog, setSessionId, setMissionName, setArchitectQuestion, setShowModal, connectWebSocket, addBuildMessage, setIsVoiceSelected, setIsKbReady, setSelectedVoiceId]);

    // Send clarification response
    const sendClarification = useCallback(async (message: string) => {
        const sid = useBuildStore.getState().sessionId;
        if (!sid) return;

        addBuildMessage('user', message);
        setShowModal(false);

        try {
            setIsArchitectThinking(true);
            const res = await fetch(`${BACKEND_URL}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': config.tenantId
                },
                body: JSON.stringify({ message: message, session_id: sid })
            });

            const data = await res.json();
            setIsArchitectThinking(false);

            if (data.extracted_fields) {
                setExtractedFields(data.extracted_fields);

                // Update mission name if agent_name or org_name found
                const fields = data.extracted_fields;
                if (fields.agent_name) {
                    setMissionName(fields.agent_name);
                } else if (fields.org_name && !useBuildStore.getState().missionName) {
                    setMissionName(fields.org_name);
                }

                // Detect URL in user message and show KB extraction tag immediately
                const urlPattern = /https?:\/\/[^\s]+/;
                if (urlPattern.test(message)) {
                    addChecklistTag('kb-extraction', 'Extracting KB from URL');
                    setChecklistTagStatus('kb-extraction', 'active');
                    addTerminalLog('SYSTEM', '🌐 Fetching content from URL...');
                }

                if (data.extracted_fields.voice_parameters && !data.clarification) {
                    addChecklistTag('voice-search', 'Searching voices');
                    setChecklistTagStatus('voice-search', 'active');
                }
            }

            if (data.voice_candidates && data.voice_candidates.length > 0) {
                setVoiceCandidates(data.voice_candidates);
                setShowVoiceSelector(true);

                // Reset selection
                useBuildStore.getState().setIsVoiceSelected(false);
                useBuildStore.getState().setSelectedVoiceId(null);
                setChecklistTagStatus('voice-search', 'done');
                addChecklistTag('voice', 'Select your voice');
                setChecklistTagStatus('voice', 'active');
            }

            if (data.clarification) {
                setArchitectQuestion(data.clarification);
                setSuggestions(data.suggestions || []);
                setShowModal(true);
                addBuildMessage('assistant', data.clarification);
            } else {
                // No more clarifications - context is complete, wait for voice + KB
                setSuggestions([]);
                setChecklistTagStatus('context', 'done');
                setContextComplete(true);
                addChecklistTag('kb', 'Generating knowledge base');
                setChecklistTagStatus('kb', 'active');
                addTerminalLog('SYSTEM', '✨ Context complete. Generating knowledge base...');
                addBuildMessage('assistant', "Everything looks perfect! We are good to go. I am now generating the knowledge base and finding the best voices for you. Select your favorite voice to finalize the build.");

                // Connect WS for real-time updates, but DON'T auto-build
                connectWebSocket(sid);
            }
        } catch (error) {
            console.error('Error submitting clarification:', error);
            addTerminalLog('ERROR', 'Error submitting clarification');
        }
    }, [addBuildMessage, setShowModal, setArchitectQuestion, addTerminalLog, connectWebSocket, setChecklistTagStatus, addChecklistTag, setContextComplete, setSuggestions]);

    // Select a voice - queue if WS not ready
    const selectVoice = useCallback((voiceId: string) => {
        console.log('[VOICE] Selecting voice:', voiceId);
        setSelectedVoiceId(voiceId);
        setShowVoiceSelector(false);
        setIsVoiceSelected(true);
        setChecklistTagStatus('voice', 'done');

        addTerminalLog('VOICE', `🎙️ Voice selected: ${voiceId}`);

        // Try to send via WS, queue if not ready
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'VOICE_SELECTED', voice_id: voiceId }));
        } else {
            // Queue for when WS connects
            pendingVoiceRef.current = voiceId;
            addTerminalLog('SYSTEM', '⏳ Queued voice selection (connecting...)');

            // Ensure WS is connecting
            const sid = useBuildStore.getState().sessionId;
            if (sid) connectWebSocket(sid);
        }
    }, [setSelectedVoiceId, setShowVoiceSelector, addTerminalLog, setChecklistTagStatus, setIsVoiceSelected, connectWebSocket]);

    // Launch the actual infrastructure pipeline
    const launchPipeline = useCallback(async () => {
        const sid = useBuildStore.getState().sessionId;
        if (!sid) return;

        setIsPipelineStarted(true);
        addTerminalLog('SYSTEM', '🚀 Initializing core infrastructure...');
        setCurrentPhase(0);
        setPhaseStatus(0, 'active');

        addChecklistTag('deploy', 'Deploying infrastructure');
        setChecklistTagStatus('deploy', 'active');

        // Try to trigger via WS first for immediate feedback
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'START_BUILD' }));
        } else {
            // Fallback to REST if WS is disconnected
            try {
                await fetch(`${BACKEND_URL}/api/build/${sid}`, {
                    method: 'POST',
                    headers: { 'X-Tenant-ID': config.tenantId }
                });
            } catch (error) {
                console.error('Launch error:', error);
                addTerminalLog('ERROR', 'Failed to launch build pipeline');
            }
        }
    }, [addTerminalLog, setIsPipelineStarted, addChecklistTag, setChecklistTagStatus, setCurrentPhase, setPhaseStatus]);

    // Test the deployed agent
    const testAgent = useCallback(async (message: string): Promise<string> => {
        const sid = useBuildStore.getState().sessionId;
        if (!sid) return 'No active session';

        try {
            const response = await fetch(`${BACKEND_URL}/api/test/${sid}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Tenant-ID': config.tenantId
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            return data.message || 'No response';
        } catch (error) {
            console.error('Test error:', error);
            return 'Error testing agent';
        }
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
        };
    }, []);

    return {
        startBuild,
        sendClarification,
        selectVoice,
        testAgent,
        launchPipeline
    };
}
