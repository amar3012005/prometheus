import { create } from 'zustand';

// 7 Build Phases matching backend k8s.py
export const BUILD_PHASES = [
    { id: 'infrastructure', name: 'Infrastructure Bootstrap', icon: '🏗️', description: 'Namespace, quotas, network policies' },
    { id: 'redis', name: 'Redis Cluster', icon: '📦', description: 'Session & cache layer with TLS' },
    { id: 'mmar', name: 'MMAR Engine', icon: '🧠', description: 'RAG + Qdrant vector store' },
    { id: 'voice', name: 'Voice Pipeline', icon: '🎤', description: 'STT (Deepgram) + TTS (ElevenLabs)' },
    { id: 'orchestrator', name: 'Multi-Agent Orchestrator', icon: '🤖', description: 'LangGraph agent nodes' },
    { id: 'ingress', name: 'Ingress Gateway', icon: '🌐', description: 'TLS, routing, CORS, health checks' },
    { id: 'health', name: 'Health Verification', icon: '🔍', description: 'Pod readiness checks' }
] as const;

export type PhaseStatus = 'pending' | 'active' | 'completed' | 'error';

export interface TerminalLog {
    timestamp: string;
    phase: string;
    message: string;
}

export interface VoiceCandidate {
    voice_id: string;
    name: string;
    preview_url: string | null;
    labels?: { accent?: string; age?: string; gender?: string };
    category?: string;
}

interface TestMessage {
    role: 'user' | 'assistant';
    content: string;
}

export interface ChecklistTag {
    id: string;
    label: string;
    status: 'pending' | 'active' | 'done';
}

interface BuildState {
    // Session
    sessionId: string | null;
    setSessionId: (id: string) => void;

    // Build Status
    isBuilding: boolean;
    setIsBuilding: (val: boolean) => void;
    isReadyToTest: boolean;
    setIsReadyToTest: (val: boolean) => void;
    hasError: boolean;
    setHasError: (val: boolean) => void;

    // Agent Info
    missionName: string;
    setMissionName: (name: string) => void;
    deploymentUrl: string | null;
    setDeploymentUrl: (url: string | null) => void;
    extractedFields: Record<string, any>;
    setExtractedFields: (fields: Record<string, any>) => void;
    contextComplete: boolean;
    setContextComplete: (val: boolean) => void;
    isPipelineStarted: boolean;
    setIsPipelineStarted: (val: boolean) => void;
    isVoiceSelected: boolean;
    setIsVoiceSelected: (val: boolean) => void;
    isKbReady: boolean;
    setIsKbReady: (val: boolean) => void;

    // 7-Phase Progress
    currentPhaseIndex: number;
    phaseStatuses: PhaseStatus[];
    setCurrentPhase: (index: number) => void;
    setPhaseStatus: (index: number, status: PhaseStatus) => void;
    advancePhase: () => void;
    resetPhases: () => void;

    // Terminal Logs
    terminalLogs: TerminalLog[];
    addTerminalLog: (phase: string, message: string) => void;
    clearTerminalLogs: () => void;

    // Voice Selection
    showVoiceSelector: boolean;
    setShowVoiceSelector: (val: boolean) => void;
    voiceCandidates: VoiceCandidate[];
    setVoiceCandidates: (candidates: VoiceCandidate[]) => void;
    selectedVoiceId: string | null;
    setSelectedVoiceId: (id: string | null) => void;

    // Architect Modal
    showModal: boolean;
    setShowModal: (val: boolean) => void;
    architectQuestion: string;
    setArchitectQuestion: (q: string) => void;
    isArchitectThinking: boolean;
    setIsArchitectThinking: (val: boolean) => void;
    suggestions: string[];
    setSuggestions: (s: string[]) => void;

    // Voice Toast (legacy)
    showVoiceToast: boolean;
    setShowVoiceToast: (val: boolean) => void;
    voicePreviewUrl: string | null;
    setVoicePreviewUrl: (url: string | null) => void;

    // Test Panel
    testHistory: TestMessage[];
    addTestMessage: (role: 'user' | 'assistant', content: string) => void;

    // DeploySheet State
    showDeploySheet: boolean;
    setShowDeploySheet: (val: boolean) => void;
    deployedAgentId: string | null;
    setDeployedAgentId: (id: string | null) => void;
    agentState: 'idle' | 'listening' | 'talking' | null;
    setAgentState: (state: 'idle' | 'listening' | 'talking' | null) => void;

    // Build Chat History
    buildHistory: TestMessage[];
    addBuildMessage: (role: 'user' | 'assistant', content: string) => void;

    // UI State
    builderWidth: number;
    setBuilderWidth: (width: number) => void;

    // Legacy compat
    logs: any[];
    addLog: (tag: string, msg: string) => void;
    phase1Progress: number;
    phase2Progress: number;
    phase3Progress: number;
    updatePhaseProgress: (phase: number, progress: number) => void;

    // Checklist Tags for BuilderSheet
    checklistTags: ChecklistTag[];
    addChecklistTag: (id: string, label: string) => void;
    setChecklistTagStatus: (id: string, status: 'pending' | 'active' | 'done') => void;
    clearChecklistTags: () => void;
}

const getTimestamp = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour12: false });
};

export const useBuildStore = create<BuildState>((set, get) => ({
    // Session
    sessionId: null,
    setSessionId: (id) => set({ sessionId: id }),

    // Build Status
    isBuilding: false,
    setIsBuilding: (val) => set({ isBuilding: val }),
    isReadyToTest: false,
    setIsReadyToTest: (val) => set({ isReadyToTest: val }),
    hasError: false,
    setHasError: (val) => set({ hasError: val }),

    // Agent Info
    missionName: '',
    setMissionName: (name) => set({ missionName: name }),
    deploymentUrl: null,
    setDeploymentUrl: (url) => set({ deploymentUrl: url }),
    extractedFields: {},
    setExtractedFields: (fields) => set((state) => ({
        extractedFields: { ...state.extractedFields, ...fields }
    })),
    contextComplete: false,
    setContextComplete: (val) => set({ contextComplete: val }),
    isPipelineStarted: false,
    setIsPipelineStarted: (val) => set({ isPipelineStarted: val }),
    isVoiceSelected: false,
    setIsVoiceSelected: (val) => set({ isVoiceSelected: val }),
    isKbReady: false,
    setIsKbReady: (val) => set({ isKbReady: val }),

    // 7-Phase Progress
    currentPhaseIndex: 0,
    phaseStatuses: Array(7).fill('pending'),
    setCurrentPhase: (index) => {
        const { phaseStatuses } = get();
        const newStatuses = [...phaseStatuses];
        // Mark previous phases as completed
        for (let i = 0; i < index; i++) {
            if (newStatuses[i] !== 'completed') newStatuses[i] = 'completed';
        }
        // Mark current as active
        if (index < 7) newStatuses[index] = 'active';
        set({ currentPhaseIndex: index, phaseStatuses: newStatuses });
    },
    setPhaseStatus: (index, status) => {
        const { phaseStatuses } = get();
        const newStatuses = [...phaseStatuses];
        newStatuses[index] = status;
        set({ phaseStatuses: newStatuses });
    },
    advancePhase: () => {
        const { currentPhaseIndex, phaseStatuses } = get();
        if (currentPhaseIndex < 6) {
            const newStatuses = [...phaseStatuses];
            newStatuses[currentPhaseIndex] = 'completed';
            newStatuses[currentPhaseIndex + 1] = 'active';
            set({ currentPhaseIndex: currentPhaseIndex + 1, phaseStatuses: newStatuses });
        } else if (currentPhaseIndex === 6) {
            const newStatuses = [...phaseStatuses];
            newStatuses[6] = 'completed';
            set({ phaseStatuses: newStatuses });
        }
    },
    resetPhases: () => set({
        currentPhaseIndex: 0,
        phaseStatuses: Array(7).fill('pending'),
        buildHistory: []
    }),

    // Terminal Logs
    terminalLogs: [],
    addTerminalLog: (phase, message) => set((state) => ({
        terminalLogs: [...state.terminalLogs, {
            timestamp: getTimestamp(),
            phase,
            message
        }].slice(-100) // Keep last 100 logs
    })),
    clearTerminalLogs: () => set({ terminalLogs: [] }),

    // Voice Selection
    showVoiceSelector: false,
    setShowVoiceSelector: (val) => set({ showVoiceSelector: val }),
    voiceCandidates: [],
    setVoiceCandidates: (candidates) => set({ voiceCandidates: candidates }),
    selectedVoiceId: null,
    setSelectedVoiceId: (id) => set({ selectedVoiceId: id }),

    // Architect Modal
    showModal: false,
    setShowModal: (val) => set({ showModal: val }),
    architectQuestion: '',
    setArchitectQuestion: (q) => set({ architectQuestion: q }),
    isArchitectThinking: false,
    setIsArchitectThinking: (val) => set({ isArchitectThinking: val }),
    suggestions: [],
    setSuggestions: (s) => set({ suggestions: s }),

    // Voice Toast
    showVoiceToast: false,
    setShowVoiceToast: (val) => set({ showVoiceToast: val }),
    voicePreviewUrl: null,
    setVoicePreviewUrl: (url) => set({ voicePreviewUrl: url }),

    // Test Panel
    testHistory: [],
    addTestMessage: (role, content) => set((state) => ({
        testHistory: [...state.testHistory, { role, content }]
    })),

    // DeploySheet State
    showDeploySheet: false,
    setShowDeploySheet: (val) => set({ showDeploySheet: val }),
    deployedAgentId: null,
    setDeployedAgentId: (id) => set({ deployedAgentId: id }),
    agentState: null,
    setAgentState: (state) => set({ agentState: state }),

    // Build Chat History
    buildHistory: [],
    addBuildMessage: (role, content) => set((state) => ({
        buildHistory: [...state.buildHistory, { role, content }]
    })),

    // UI State

    builderWidth: Math.max(440, typeof window !== 'undefined' ? window.innerWidth * 0.35 : 440),
    setBuilderWidth: (width) => set({ builderWidth: width }),

    // Legacy compat
    logs: [],

    addLog: (tag, msg) => set((state) => ({
        logs: [...state.logs, { tag, msg, ts: getTimestamp() }]
    })),
    phase1Progress: 0,
    phase2Progress: 0,
    phase3Progress: 0,
    updatePhaseProgress: (phase, progress) => {
        if (phase === 1) set({ phase1Progress: progress });
        else if (phase === 2) set({ phase2Progress: progress });
        else if (phase === 3) set({ phase3Progress: progress });
    },

    // Checklist Tags for BuilderSheet
    checklistTags: [],
    addChecklistTag: (id, label) => set((state) => {
        // Avoid duplicates
        if (state.checklistTags.some(tag => tag.id === id)) return state;
        return {
            checklistTags: [...state.checklistTags, { id, label, status: 'active' }]
        };
    }),
    setChecklistTagStatus: (id, status) => set((state) => ({
        checklistTags: state.checklistTags.map(tag =>
            tag.id === id ? { ...tag, status } : tag
        )
    })),
    clearChecklistTags: () => set({ checklistTags: [] })
}));
