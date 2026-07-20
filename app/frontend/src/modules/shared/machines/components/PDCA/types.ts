// PDCA Kanban Types

export interface KanbanItem {
    id: string | number;
    title: string;
    subtitle: string;
    machineId: number;
    machineName: string;
    priority: string;
    riskLevel?: string;
    phase: 'PLAN' | 'DO' | 'CHECK' | 'ACT';
    type: 'PREDICTION' | 'WORK_ORDER' | 'INTERVENTION';
    date: string;
    
    // Real DB status (when type === WORK_ORDER or INTERVENTION)
    statut?: string;

    // Enhanced PLAN fields
    riskScore?: number;
    confidence?: 'LOW' | 'MEDIUM' | 'HIGH';
    machineHealth?: 'OPERATIONAL' | 'WARNING' | 'CRITICAL';
    estimatedImpact?: string;
    
    // Enhanced DO fields
    progress?: number;
    timeElapsed?: string;
    technician?: string;
    isBlocked?: boolean;
    blockingIssue?: string;
    estimatedCompletion?: string;
    
    // Enhanced CHECK fields
    verificationStatus?: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
    qualityMetrics?: {
        vibration?: number;
        temperature?: number;
        noise?: string;
    };
    hasDiagnostic?: boolean;
    hasValidation?: boolean;
    
    // Enhanced ACT fields
    implementationStatus?: 'PENDING' | 'IN_PROGRESS' | 'COMPLETED';
    mlRetraining?: 'PENDING' | 'SCHEDULED' | 'COMPLETED';
    effectiveness?: {
        downtimeReduction?: string;
        costSavings?: string;
        recurrenceRate?: string;
    };
    knowledgeBase?: 'DRAFT' | 'PUBLISHED';
}

export interface KanbanColumn {
    id: 'PLAN' | 'DO' | 'CHECK' | 'ACT';
    label: string;
    description: string;
    color: string;
    border: string;
    badge: string;
    labelClass: string;
}