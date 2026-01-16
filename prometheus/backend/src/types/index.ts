export interface AgentIdentity {
    name: string;
    greeting?: string;
    systemPrompt?: string;
    voiceStability?: number;
    voiceSimilarity?: number;
}

export interface AgentKnowledge {
    orgName: string;
    knowledgeContent?: string;
    responseStyle?: string;
}

export interface BuilderResponse {
    identity: AgentIdentity;
    knowledge: AgentKnowledge;
    missing_fields: string[];
    next_question: string;
    completeness_score: number;
}

export interface BuildLog {
    ts: string;
    tag: 'planning' | 'executing' | 'verifying';
    msg: string;
}

export interface BuildProgress {
    progress: number; // 0-100
    phase: number; // 1-3
    status: 'idle' | 'running' | 'complete' | 'error';
}
