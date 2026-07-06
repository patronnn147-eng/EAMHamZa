import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { CheckCircle2, Activity, AlertTriangle, Boxes, ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import { useInterventionPartsByWO } from '@/hooks/useInventory';
import { PartsConsumedSelector, ConsumedRow, buildInitialConsumedRows, serializeConsumedRows } from '@/components/inventory/PartsConsumedSelector';
import { DirectConsumeSelector, DirectConsumeRow, PendingDraftRow, directHasErrors, serializeDirect, serializePendingDirect } from '@/components/inventory/DirectConsumeSelector';

interface WorkOrderCompleteDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (data: WorkOrderCompletePayload) => void;
    workOrderId: number;
    workOrderTitle: string;
    machineName?: string;
    machineId?: number | null;
    suggestedCause?: string;
    interventionId?: number | null;
}

export interface WorkOrderCompletePayload {
    rapport: string;
    intervention_type?: string;
    root_cause_category?: string;
    root_cause_description?: string;
    symptoms?: string;
    actions_performed?: string;
    parts_replaced?: string;
    tools_used?: string;
    machine_status_after?: string;
    air_temperature?: number;
    process_temperature?: number;
    rotational_speed?: number;
    torque?: number;
    tool_wear?: number;
    telemetry_notes?: string;
    parts_consumed?: ReturnType<typeof serializeConsumedRows>;
    parts_consumed_direct?: ReturnType<typeof serializeDirect>;
    pending_pieces_direct?: ReturnType<typeof serializePendingDirect>;
}

const INTERVENTION_TYPES = [
    { value: 'PREVENTIVE', label: 'Maintenance préventive' },
    { value: 'CORRECTIVE', label: 'Maintenance corrective' },
    { value: 'PREDICTIVE', label: 'Maintenance prédictive' },
    { value: 'EMERGENCY', label: 'Urgence / Dépannage' },
    { value: 'INSPECTION', label: 'Inspection / Audit' },
    { value: 'OTHER', label: 'Autre' },
];

const ROOT_CAUSE_CATEGORIES = [
    { value: 'MECHANICAL', label: 'Défaillance mécanique' },
    { value: 'ELECTRICAL', label: 'Défaillance électrique' },
    { value: 'HYDRAULIC', label: 'Problème hydraulique' },
    { value: 'SOFTWARE', label: 'Problème logiciel / firmware' },
    { value: 'WEAR', label: 'Usure normale' },
    { value: 'OVERLOAD', label: 'Surcharge / Stress excessif' },
    { value: 'ENVIRONMENTAL', label: 'Conditions environnementales' },
    { value: 'MATERIAL', label: 'Problème de matière première' },
    { value: 'UNKNOWN', label: 'Cause indéterminée' },
];

const MACHINE_STATUS_OPTIONS = [
    { value: 'OPERATIONAL', label: 'Opérationnel' },
    { value: 'DEGRADED', label: 'Dégradé (fonctionne partiellement)' },
    { value: 'STOPPED', label: 'Arrêté (en attente)' },
    { value: 'SCRAP', label: 'Mettre au rebut' },
];

const STEPS = [
    { id: 1, label: 'Rapport' },
    { id: 2, label: 'Diagnostic' },
    { id: 3, label: 'Pièces & Outils' },
    { id: 4, label: 'Télémétrie' },
];

function StepIndicator({ current }: { current: number }) {
    return (
        <div className="flex items-center w-full mb-2">
            {STEPS.map((s, i) => {
                let circleClass: string;
                if (current > s.id) {
                    circleClass = 'bg-green-600 border-green-600 text-white';
                } else if (current === s.id) {
                    circleClass = 'bg-blue-600 border-blue-600 text-white';
                } else {
                    circleClass = 'bg-transparent border-slate-600 text-slate-400';
                }

                let connectorClass = 'bg-slate-700';
                if (current > s.id + 1) {
                    connectorClass = 'bg-green-600';
                } else if (current > s.id) {
                    connectorClass = 'bg-blue-600';
                }

                return (
                    <React.Fragment key={s.id}>
                        <div className="flex flex-col items-center gap-1 shrink-0">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold border-2 transition-colors ${circleClass}`}>
                                {current > s.id ? <Check className="h-3.5 w-3.5" /> : s.id}
                            </div>
                            <span className={`text-[10px] whitespace-nowrap ${current === s.id ? 'text-blue-400 font-medium' : 'text-slate-500'}`}>
                                {s.label}
                            </span>
                        </div>
                        {i < STEPS.length - 1 && (
                            <div className={`flex-1 h-0.5 mx-1 mb-4 transition-colors ${connectorClass}`} />
                        )}
                    </React.Fragment>
                );
            })}
        </div>
    );
}

export const WorkOrderCompleteDialog: React.FC<WorkOrderCompleteDialogProps> = ({
    open,
    onOpenChange,
    onConfirm,
    workOrderId,
    workOrderTitle,
    machineName,
    machineId,
    suggestedCause,
}) => {
    const { data: partsDetail } = useInterventionPartsByWO(open ? workOrderId : null);
    const [consumedRows, setConsumedRows] = useState<ConsumedRow[]>([]);
    const [directRows, setDirectRows] = useState<DirectConsumeRow[]>([]);
    const [pendingRows, setPendingRows] = useState<PendingDraftRow[]>([]);

    useEffect(() => {
        if (partsDetail?.required) {
            setConsumedRows(buildInitialConsumedRows(partsDetail.required));
        } else {
            setConsumedRows([]);
        }
    }, [partsDetail]);

    const [step, setStep] = useState(1);
    const [loading, setLoading] = useState(false);

    const [rapport, setRapport] = useState('');
    const [interventionType, setInterventionType] = useState<string>('CORRECTIVE');
    const [rootCauseCategory, setRootCauseCategory] = useState<string>('');
    const [rootCauseDescription, setRootCauseDescription] = useState('');
    const [symptoms, setSymptoms] = useState<string[]>([]);
    const [actionsPerformed, setActionsPerformed] = useState('');
    const [partsReplaced, setPartsReplaced] = useState('');
    const [toolsUsed, setToolsUsed] = useState('');
    const [machineStatusAfter, setMachineStatusAfter] = useState<string>('OPERATIONAL');

    const [airTemperature, setAirTemperature] = useState('');
    const [processTemperature, setProcessTemperature] = useState('');
    const [rotationalSpeed, setRotationalSpeed] = useState('');
    const [torqueVal, setTorqueVal] = useState('');
    const [toolWear, setToolWear] = useState('');
    const [telemetryNotes, setTelemetryNotes] = useState('');

    const resetForm = () => {
        setStep(1);
        setRapport('');
        setInterventionType('CORRECTIVE');
        setRootCauseCategory('');
        setRootCauseDescription('');
        setSymptoms([]);
        setActionsPerformed('');
        setPartsReplaced('');
        setToolsUsed('');
        setMachineStatusAfter('OPERATIONAL');
        setAirTemperature('');
        setProcessTemperature('');
        setRotationalSpeed('');
        setTorqueVal('');
        setToolWear('');
        setTelemetryNotes('');
        setDirectRows([]);
        setPendingRows([]);
    };

    useEffect(() => {
        if (!open) {
            resetForm();
        } else if (suggestedCause && !rootCauseDescription) {
            setRootCauseDescription(suggestedCause);
        }
    }, [open]);

    const canProceed = () => {
        if (step === 1) return rapport.trim().length > 0;
        return true;
    };

    const handleConfirm = async () => {
        setLoading(true);
        try {
            const payload: WorkOrderCompletePayload = {
                parts_consumed: consumedRows.length > 0 ? serializeConsumedRows(consumedRows) : undefined,
                parts_consumed_direct: directRows.length > 0 ? serializeDirect(directRows) : undefined,
                pending_pieces_direct: pendingRows.length > 0 ? serializePendingDirect(pendingRows) : undefined,
                rapport: rapport.trim(),
                intervention_type: interventionType || undefined,
                root_cause_category: rootCauseCategory || undefined,
                root_cause_description: rootCauseDescription.trim() || undefined,
                symptoms: symptoms.length > 0 ? symptoms.join(', ') : undefined,
                actions_performed: actionsPerformed.trim() || undefined,
                parts_replaced: partsReplaced.trim() || undefined,
                tools_used: toolsUsed.trim() || undefined,
                machine_status_after: machineStatusAfter || undefined,
                air_temperature: airTemperature ? parseFloat(airTemperature) : undefined,
                process_temperature: processTemperature ? parseFloat(processTemperature) : undefined,
                rotational_speed: rotationalSpeed ? parseInt(rotationalSpeed) : undefined,
                torque: torqueVal ? parseFloat(torqueVal) : undefined,
                tool_wear: toolWear ? parseInt(toolWear) : undefined,
                telemetry_notes: telemetryNotes.trim() || undefined,
            };
            onConfirm(payload);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2 text-green-600">
                        <CheckCircle2 className="h-5 w-5" />
                        Terminer l'OT #{workOrderId}
                    </DialogTitle>
                    <DialogDescription className="text-blue-300">
                        {workOrderTitle}
                        {machineName && <span className="ml-2 font-semibold">• {machineName}</span>}
                    </DialogDescription>
                </DialogHeader>

                <StepIndicator current={step} />

                <div className="min-h-[320px] py-2">
                    {/* Step 1 — Rapport & Contexte */}
                    {step === 1 && (
                        <div className="grid gap-5">
                            <div className="grid gap-2">
                                <Label className="text-sm font-semibold text-red-400 flex items-center gap-1">
                                    <AlertTriangle className="h-4 w-4" />
                                    Rapport final *
                                </Label>
                                <Textarea
                                    placeholder="Décrivez le travail effectué sur la machine..."
                                    value={rapport}
                                    onChange={(e) => setRapport(e.target.value)}
                                    className="min-h-[120px]"
                                    autoFocus
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="grid gap-2">
                                    <Label className="text-sm font-semibold">Type d'intervention</Label>
                                    <Select value={interventionType} onValueChange={setInterventionType}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Sélectionner..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {INTERVENTION_TYPES.map((type) => (
                                                <SelectItem key={type.value} value={type.value}>
                                                    {type.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>

                                <div className="grid gap-2">
                                    <Label className="text-sm font-semibold">État de la machine après</Label>
                                    <Select value={machineStatusAfter} onValueChange={setMachineStatusAfter}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Sélectionner..." />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {MACHINE_STATUS_OPTIONS.map((status) => (
                                                <SelectItem key={status.value} value={status.value}>
                                                    {status.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 2 — Diagnostic */}
                    {step === 2 && (
                        <div className="grid gap-5">
                            <div className="grid gap-2">
                                <Label className="text-sm font-semibold">Catégorie de cause racine</Label>
                                <Select value={rootCauseCategory} onValueChange={setRootCauseCategory}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Sélectionner la cause..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {ROOT_CAUSE_CATEGORIES.map((cat) => (
                                            <SelectItem key={cat.value} value={cat.value}>
                                                {cat.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="grid gap-2">
                                <Label className="text-sm font-semibold">Symptômes observés</Label>
                                <div className="grid grid-cols-2 gap-2 p-3 rounded-lg border border-slate-700 bg-slate-800/50">
                                    {['Bruit anormal', 'Vibrations', 'Surchauffe', 'Fuite', 'Panne électrique', 'Baisse de performance'].map((s) => (
                                        <div key={s} className="flex items-center space-x-2">
                                            <Checkbox
                                                id={`sym-${s}`}
                                                checked={symptoms.includes(s)}
                                                onCheckedChange={(checked) => {
                                                    if (checked) setSymptoms(prev => [...prev, s]);
                                                    else setSymptoms(prev => prev.filter(x => x !== s));
                                                }}
                                            />
                                            <label htmlFor={`sym-${s}`} className="text-xs font-medium cursor-pointer">{s}</label>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            <div className="grid gap-2">
                                <Label className="text-sm font-semibold">Description de la cause</Label>
                                {suggestedCause && (
                                    <p className="text-xs text-purple-400">
                                        💡 Cause suggérée par l'IA: {suggestedCause}
                                    </p>
                                )}
                                <Textarea
                                    placeholder="Décrivez la cause du problème..."
                                    value={rootCauseDescription}
                                    onChange={(e) => setRootCauseDescription(e.target.value)}
                                    className="min-h-[80px]"
                                />
                            </div>

                            <div className="grid gap-2">
                                <Label className="text-sm font-semibold">Actions effectuées</Label>
                                <Textarea
                                    placeholder="- Action 1&#10;- Action 2&#10;- Action 3"
                                    value={actionsPerformed}
                                    onChange={(e) => setActionsPerformed(e.target.value)}
                                    rows={4}
                                />
                            </div>
                        </div>
                    )}

                    {/* Step 3 — Pièces & Outils */}
                    {step === 3 && (
                        <div className="grid gap-5">
                            {partsDetail && partsDetail.required.length > 0 && (
                                <div className="grid gap-2">
                                    <Label className="text-sm font-semibold flex items-center gap-2">
                                        <Boxes className="h-4 w-4 text-emerald-400" />
                                        Consommation des pièces réservées
                                    </Label>
                                    <PartsConsumedSelector
                                        required={partsDetail.required}
                                        rows={consumedRows}
                                        onChange={setConsumedRows}
                                    />
                                </div>
                            )}

                            <div className="grid gap-2">
                                <Label className="text-sm font-semibold flex items-center gap-2">
                                    <Boxes className="h-4 w-4 text-blue-400" />
                                    Pièces remplacées (depuis l'inventaire)
                                </Label>
                                <DirectConsumeSelector
                                    machineId={machineId ?? null}
                                    consumedRows={directRows}
                                    pendingRows={pendingRows}
                                    onConsumedChange={setDirectRows}
                                    onPendingChange={setPendingRows}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="grid gap-2">
                                    <Label className="text-sm font-semibold">Notes libres (optionnel)</Label>
                                    <Input
                                        placeholder="Notes complémentaires hors catalogue"
                                        value={partsReplaced}
                                        onChange={(e) => setPartsReplaced(e.target.value)}
                                    />
                                </div>
                                <div className="grid gap-2">
                                    <Label className="text-sm font-semibold">Outils utilisés</Label>
                                    <Input
                                        placeholder="Ex: Clé à douille, Multimètre..."
                                        value={toolsUsed}
                                        onChange={(e) => setToolsUsed(e.target.value)}
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Step 4 — Télémétrie */}
                    {step === 4 && (
                        <div className="grid gap-4">
                            <div>
                                <h4 className="text-sm font-semibold text-amber-400 mb-1 flex items-center gap-2">
                                    <Activity className="h-4 w-4" />
                                    Télémétrie (IoT Dashboard)
                                </h4>
                                <p className="text-xs text-blue-400 mb-4">
                                    Données de la machine après intervention. Tous les champs sont optionnels.
                                </p>
                            </div>
                            <div className="grid grid-cols-5 gap-3">
                                <div className="grid gap-1">
                                    <Label className="text-xs">Temp. Air (K)</Label>
                                    <Input
                                        type="number"
                                        step="0.1"
                                        min="250"
                                        max="400"
                                        placeholder="298.0"
                                        value={airTemperature}
                                        onChange={(e) => setAirTemperature(e.target.value)}
                                    />
                                </div>
                                <div className="grid gap-1">
                                    <Label className="text-xs">Temp. Process (K)</Label>
                                    <Input
                                        type="number"
                                        step="0.1"
                                        min="250"
                                        max="450"
                                        placeholder="308.0"
                                        value={processTemperature}
                                        onChange={(e) => setProcessTemperature(e.target.value)}
                                    />
                                </div>
                                <div className="grid gap-1">
                                    <Label className="text-xs">Vitesse (RPM)</Label>
                                    <Input
                                        type="number"
                                        min="0"
                                        max="10000"
                                        placeholder="1500"
                                        value={rotationalSpeed}
                                        onChange={(e) => setRotationalSpeed(e.target.value)}
                                    />
                                </div>
                                <div className="grid gap-1">
                                    <Label className="text-xs">Couple (Nm)</Label>
                                    <Input
                                        type="number"
                                        step="0.1"
                                        min="0"
                                        max="1000"
                                        placeholder="40.0"
                                        value={torqueVal}
                                        onChange={(e) => setTorqueVal(e.target.value)}
                                    />
                                </div>
                                <div className="grid gap-1">
                                    <Label className="text-xs">Usure outil (min)</Label>
                                    <Input
                                        type="number"
                                        min="0"
                                        max="500"
                                        placeholder="0"
                                        value={toolWear}
                                        onChange={(e) => setToolWear(e.target.value)}
                                    />
                                </div>
                            </div>
                            <div className="grid gap-1">
                                <Label className="text-xs">Notes</Label>
                                <Input
                                    placeholder="Notes supplémentaires..."
                                    value={telemetryNotes}
                                    onChange={(e) => setTelemetryNotes(e.target.value)}
                                />
                            </div>
                        </div>
                    )}
                </div>

                <DialogFooter className="border-t border-slate-700 pt-4 flex items-center justify-between">
                    <Button
                        variant="outline"
                        onClick={() => step === 1 ? onOpenChange(false) : setStep(s => s - 1)}
                    >
                        {step === 1 ? 'Annuler' : <><ChevronLeft className="h-4 w-4 mr-1" />Précédent</>}
                    </Button>

                    <span className="text-xs text-slate-500">{step} / {STEPS.length}</span>

                    {step < STEPS.length ? (
                        <Button
                            onClick={() => setStep(s => s + 1)}
                            disabled={!canProceed()}
                        >
                            Suivant <ChevronRight className="h-4 w-4 ml-1" />
                        </Button>
                    ) : (
                        <Button
                            onClick={handleConfirm}
                            disabled={!rapport.trim() || loading || directHasErrors(directRows)}
                            className="bg-green-600 hover:bg-green-700"
                        >
                            {loading ? 'Enregistrement...' : 'Terminer'}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};
