import React, { useState, useEffect } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
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
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { CheckCircle2, Activity, AlertTriangle } from 'lucide-react';

interface WorkOrderCompleteDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onConfirm: (data: WorkOrderCompletePayload) => void;
    workOrderId: number;
    workOrderTitle: string;
    machineName?: string;
    suggestedCause?: string;
}

export interface WorkOrderCompletePayload {
    rapport: string;
    intervention_type?: string;
    root_cause_category?: string;
    root_cause_description?: string;
    actions_performed?: string;
    parts_replaced?: string;
    tools_used?: string;
    machine_status_after?: string;
    plan_hypothesis?: string;
    check_resolved?: boolean;
    check_verification_method?: string;
    act_preventive_actions?: string;
    act_recommendations?: string;
    air_temperature?: number;
    process_temperature?: number;
    rotational_speed?: number;
    torque?: number;
    tool_wear?: number;
    telemetry_notes?: string;
    ml_prediction_matched?: boolean | null;
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

export const WorkOrderCompleteDialog: React.FC<WorkOrderCompleteDialogProps> = ({
    open,
    onOpenChange,
    onConfirm,
    workOrderId,
    workOrderTitle,
    machineName,
    suggestedCause,
}) => {
    const [loading, setLoading] = useState(false);
    const [mlPredictionMatched, setMlPredictionMatched] = useState<boolean | null>(null);

    const [rapport, setRapport] = useState('');
    const [interventionType, setInterventionType] = useState<string>('CORRECTIVE');
    const [rootCauseCategory, setRootCauseCategory] = useState<string>('');
    const [rootCauseDescription, setRootCauseDescription] = useState('');
    const [actionsPerformed, setActionsPerformed] = useState('');
    const [partsReplaced, setPartsReplaced] = useState('');
    const [toolsUsed, setToolsUsed] = useState('');
    const [machineStatusAfter, setMachineStatusAfter] = useState<string>('OPERATIONAL');

    const [planHypothesis, setPlanHypothesis] = useState('');
    const [checkResolved, setCheckResolved] = useState(true);
    const [checkVerificationMethod, setCheckVerificationMethod] = useState('');
    const [actPreventiveActions, setActPreventiveActions] = useState('');
    const [actRecommendations, setActRecommendations] = useState('');

    const [airTemperature, setAirTemperature] = useState('');
    const [processTemperature, setProcessTemperature] = useState('');
    const [rotationalSpeed, setRotationalSpeed] = useState('');
    const [torqueVal, setTorqueVal] = useState('');
    const [toolWear, setToolWear] = useState('');
    const [telemetryNotes, setTelemetryNotes] = useState('');

    const resetForm = () => {
        setRapport('');
        setInterventionType('CORRECTIVE');
        setRootCauseCategory('');
        setRootCauseDescription('');
        setActionsPerformed('');
        setPartsReplaced('');
        setToolsUsed('');
        setMachineStatusAfter('OPERATIONAL');
        setPlanHypothesis('');
        setCheckResolved(true);
        setCheckVerificationMethod('');
        setActPreventiveActions('');
        setActRecommendations('');
        setAirTemperature('');
        setProcessTemperature('');
        setRotationalSpeed('');
        setTorqueVal('');
        setToolWear('');
        setTelemetryNotes('');
        setMlPredictionMatched(null);
    };

    useEffect(() => {
        if (!open) {
            resetForm();
        } else if (suggestedCause && !rootCauseDescription) {
            setRootCauseDescription(suggestedCause);
        }
    }, [open]);

    const handleConfirm = async () => {
        setLoading(true);
        try {
            const payload: WorkOrderCompletePayload = {
                rapport: rapport.trim(),
                intervention_type: interventionType || undefined,
                root_cause_category: rootCauseCategory || undefined,
                root_cause_description: rootCauseDescription.trim() || undefined,
                actions_performed: actionsPerformed.trim() || undefined,
                parts_replaced: partsReplaced.trim() || undefined,
                tools_used: toolsUsed.trim() || undefined,
                machine_status_after: machineStatusAfter || undefined,
                plan_hypothesis: planHypothesis.trim() || undefined,
                check_resolved: checkResolved,
                check_verification_method: checkVerificationMethod.trim() || undefined,
                act_preventive_actions: actPreventiveActions.trim() || undefined,
                act_recommendations: actRecommendations.trim() || undefined,
                air_temperature: airTemperature ? parseFloat(airTemperature) : undefined,
                process_temperature: processTemperature ? parseFloat(processTemperature) : undefined,
                rotational_speed: rotationalSpeed ? parseInt(rotationalSpeed) : undefined,
                torque: torqueVal ? parseFloat(torqueVal) : undefined,
                tool_wear: toolWear ? parseInt(toolWear) : undefined,
                telemetry_notes: telemetryNotes.trim() || undefined,
                ml_prediction_matched: mlPredictionMatched,
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

                <div className="grid gap-6 py-4">
                    {/* RAPPORT FINAL */}
                    <div className="grid gap-2">
                        <Label className="text-sm font-semibold text-red-400 flex items-center gap-1">
                            <AlertTriangle className="h-4 w-4" />
                            Rapport final *
                        </Label>
                        <Textarea
                            placeholder="Décrivez le travail effectué sur la machine..."
                            value={rapport}
                            onChange={(e) => setRapport(e.target.value)}
                            className="min-h-[100px]"
                        />
                    </div>

                    {/* TYPE INTERVENTION + ETAT MACHINE */}
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

                    {/* CAUSE RACINE */}
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
                        />
                    </div>

                    {/* ACTIONS */}
                    <div className="grid gap-2">
                        <Label className="text-sm font-semibold">Actions effectuées</Label>
                        <Textarea
                            placeholder="- Action 1&#10;- Action 2&#10;- Action 3"
                            value={actionsPerformed}
                            onChange={(e) => setActionsPerformed(e.target.value)}
                            rows={3}
                        />
                    </div>

                    {/* PIECES + OUTILS */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                            <Label className="text-sm font-semibold">Pièces remplacées</Label>
                            <Input
                                placeholder="Ex: Roulement 6204, Courroie..."
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

                    {/* TELEMETRIE */}
                    <div className="border-t border-blue-800 pt-4">
                        <h4 className="text-sm font-semibold text-amber-400 mb-3 flex items-center gap-2">
                            <Activity className="h-4 w-4" />
                            Telémétrie (IoT Dashboard)
                        </h4>
                        <p className="text-xs text-blue-400 mb-3">
                            Enregistrez les données telemetry de la machine après intervention.
                        </p>
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
                        <div className="mt-3">
                            <Label className="text-xs">Notes</Label>
                            <Input
                                placeholder="Notes supplémentaires..."
                                value={telemetryNotes}
                                onChange={(e) => setTelemetryNotes(e.target.value)}
                            />
                        </div>
                    </div>

                    {/* PDCA */}
                    <div className="border-t border-blue-800 pt-4">
                        <h4 className="text-sm font-semibold text-purple-400 mb-3">
                            Méthode PDCA - Amélioration continue
                        </h4>
                        
                        <div className="grid gap-2 mb-3">
                            <Label className="text-xs">PLAN - Hypothèse / Cause identifiée</Label>
                            <Textarea
                                placeholder="Quelle est votre hypothèse sur la cause..."
                                value={planHypothesis}
                                onChange={(e) => setPlanHypothesis(e.target.value)}
                                rows={2}
                            />
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-blue-800/50 mb-3">
                            <div className="space-y-0.5">
                                <Label className="text-sm font-semibold">CHECK - Problème résolu ?</Label>
                                <p className="text-[10px] text-blue-300">Le problème a-t-il été résolu ?</p>
                            </div>
                            <Switch
                                checked={checkResolved}
                                onCheckedChange={setCheckResolved}
                            />
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-lg bg-slate-800/50 border border-purple-800/50 mb-3">
                            <div className="space-y-0.5">
                                <Label className="text-sm font-semibold">CHECK - L'analyse IA était-elle correcte ?</Label>
                                <p className="text-[10px] text-purple-300">Feedback sur le diagnostic IA</p>
                            </div>
                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    onClick={() => setMlPredictionMatched(true)}
                                    className={`px-3 py-1 rounded text-sm font-medium border transition-colors ${mlPredictionMatched === true ? 'bg-green-600 border-green-500 text-white' : 'bg-transparent border-slate-600 text-slate-400 hover:border-green-600 hover:text-green-400'}`}
                                >
                                    Oui ✓
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setMlPredictionMatched(false)}
                                    className={`px-3 py-1 rounded text-sm font-medium border transition-colors ${mlPredictionMatched === false ? 'bg-red-600 border-red-500 text-white' : 'bg-transparent border-slate-600 text-slate-400 hover:border-red-600 hover:text-red-400'}`}
                                >
                                    Non ✗
                                </button>
                            </div>
                        </div>

                        <div className="grid gap-2 mb-3">
                            <Label className="text-xs">CHECK - Méthode de vérification</Label>
                            <Input
                                placeholder="Comment avez-vous vérifié ?"
                                value={checkVerificationMethod}
                                onChange={(e) => setCheckVerificationMethod(e.target.value)}
                            />
                        </div>

                        <div className="grid gap-2 mb-3">
                            <Label className="text-xs">ACT - Actions préventives</Label>
                            <Textarea
                                placeholder="Quelles actions préventives mettre en place ?"
                                value={actPreventiveActions}
                                onChange={(e) => setActPreventiveActions(e.target.value)}
                                rows={2}
                            />
                        </div>

                        <div className="grid gap-2">
                            <Label className="text-xs">ACT - Recommandations</Label>
                            <Textarea
                                placeholder="Autres recommandations pour éviter la récurrence..."
                                value={actRecommendations}
                                onChange={(e) => setActRecommendations(e.target.value)}
                                rows={2}
                            />
                        </div>
                    </div>
                </div>

                <DialogFooter>
                    <Button variant="outline" onClick={() => onOpenChange(false)}>
                        Annuler
                    </Button>
                    <Button 
                        onClick={handleConfirm} 
                        disabled={!rapport.trim() || loading}
                        className="bg-green-600 hover:bg-green-700"
                    >
                        {loading ? 'Enregistrement...' : 'Terminer'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};