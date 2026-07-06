import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
    Package,
    Plus,
    Minus,
    Search,
    Edit,
    Trash2,
    AlertTriangle,
    ArrowUpCircle,
    ArrowDownCircle,
    BoxIcon,
    Zap,
    Link2,
    CheckCircle2,
} from 'lucide-react';
import { PieceMachinesLinker } from '@/components/inventory/PieceMachinesLinker';

const apiBase = import.meta.env.VITE_API_BASE_URL || '';

interface Piece {
    id: number;
    reference: string;
    name: string;
    description?: string;
    unit_price?: number;
    category?: string;
    min_stock?: number;
}

interface StockLevel {
    id: number;
    piece_id: number;
    quantity: number;
    piece_name?: string;
    piece_reference?: string;
    min_stock?: number;
}

interface StockAlert {
    piece_id: number;
    piece_name: string;
    piece_reference: string;
    current_quantity: number;
    min_stock: number;
    deficit: number;
}

interface Movement {
    id: number;
    piece_id: number;
    quantity: number;
    movement_type: string;
    reference?: string;
    created_at?: string;
    piece_name?: string;
}

const CATEGORIES = [
    'Électrique', 'Mécanique', 'Hydraulique',
    'Pneumatique', 'Électronique', 'Consommable', 'Autre',
];

function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return token
        ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
        : { 'Content-Type': 'application/json' };
}

// ─── Quick Actions Panel ───────────────────────────────────────────────────────
interface QuickActionsPanelProps {
    alerts: StockAlert[];
    canManage: boolean;
    canConsume: boolean;
    onNewPiece: () => void;
    onAddStock: (pieceId?: number, qty?: number) => void;
    onConsume: (pieceId?: number) => void;
    onGoToAlerts: () => void;
}

function QuickActionsPanel({
    alerts,
    canManage,
    canConsume,
    onNewPiece,
    onAddStock,
    onConsume,
}: Readonly<QuickActionsPanelProps>) {
    return (
        <Card className="border-blue-500/30 bg-gradient-to-br from-slate-900 to-blue-950/40">
            <CardContent className="py-4 px-5">
                {/* Row 1 – Always-available primary actions */}
                <div className="flex items-center gap-3 flex-wrap">
                    <div className="flex items-center gap-1.5 text-blue-300 mr-1">
                        <Zap className="h-4 w-4 text-yellow-400" />
                        <span className="text-sm font-semibold">Actions rapides</span>
                    </div>

                    {canManage && (
                        <Button
                            size="sm"
                            className="bg-blue-600 hover:bg-blue-500 text-white h-8 gap-1.5"
                            onClick={onNewPiece}
                            title="N"
                        >
                            <Plus className="h-3.5 w-3.5" />
                            Nouvelle pièce
                            <kbd className="ml-1 text-[10px] opacity-50 font-mono bg-white/20 px-1 rounded">N</kbd>
                        </Button>
                    )}

                    {canManage && (
                        <Button
                            size="sm"
                            className="bg-green-700 hover:bg-green-600 text-white h-8 gap-1.5"
                            onClick={() => onAddStock()}
                            title="A"
                        >
                            <ArrowUpCircle className="h-3.5 w-3.5" />
                            Entrée stock
                            <kbd className="ml-1 text-[10px] opacity-50 font-mono bg-white/20 px-1 rounded">A</kbd>
                        </Button>
                    )}

                    {canConsume && (
                        <Button
                            size="sm"
                            className="bg-orange-700 hover:bg-orange-600 text-white h-8 gap-1.5"
                            onClick={() => onConsume()}
                            title="C"
                        >
                            <ArrowDownCircle className="h-3.5 w-3.5" />
                            Sortie stock
                            <kbd className="ml-1 text-[10px] opacity-50 font-mono bg-white/20 px-1 rounded">C</kbd>
                        </Button>
                    )}

                    {alerts.length === 0 && (
                        <span className="ml-auto flex items-center gap-1.5 text-green-400 text-sm">
                            <CheckCircle2 className="h-4 w-4" />
                            Tous les stocks sont suffisants
                        </span>
                    )}
                </div>

            </CardContent>
        </Card>
    );
}

// ─── Main Page ─────────────────────────────────────────────────────────────────
export default function InventoryPage() {
    const { user } = useAuth();
    const { toast } = useToast();
    const [activeTab, setActiveTab] = useState('stock');   // default: stock overview (most useful)
    const [pieces, setPieces] = useState<Piece[]>([]);
    const [stockLevels, setStockLevels] = useState<StockLevel[]>([]);
    const [alerts, setAlerts] = useState<StockAlert[]>([]);
    const [movements, setMovements] = useState<Movement[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');

    // Dialog states
    const [pieceDialogOpen, setPieceDialogOpen] = useState(false);
    const [editingPiece, setEditingPiece] = useState<Piece | null>(null);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
    const [deletingPiece, setDeletingPiece] = useState<Piece | null>(null);
    const [stockDialogOpen, setStockDialogOpen] = useState(false);
    const [stockAction, setStockAction] = useState<'add' | 'consume'>('add');
    const [linkerPiece, setLinkerPiece] = useState<Piece | null>(null);

    const searchRef = useRef<HTMLInputElement>(null);

    const [pieceForm, setPieceForm] = useState({
        reference: '', name: '', description: '', unit_price: '', category: '', min_stock: '5',
    });
    const [stockForm, setStockForm] = useState({
        piece_id: '', quantity: '', reference: '',
    });

    // Resolve role from auth context, fallback to localStorage (matches Sidebar pattern)
    // — avoids the gap where useAuth() resolves AFTER first render.
    const resolvedRole = (() => {
        if (user?.role) return user.role.toUpperCase();
        try {
            const stored = localStorage.getItem('user');
            if (stored) return (JSON.parse(stored).role || '').toUpperCase();
        } catch { /* ignore */ }
        return '';
    })();
    const canManage = resolvedRole === 'ADMIN' || resolvedRole === 'CHEFTECH';
    const canConsume = canManage || resolvedRole === 'CHETOP';

    // Derived: current stock for selected piece
    const selectedPieceStock = stockForm.piece_id
        ? stockLevels.find((s) => s.piece_id === parseInt(stockForm.piece_id))
        : null;
    const selectedPieceInfo = stockForm.piece_id
        ? pieces.find((p) => p.id === parseInt(stockForm.piece_id))
        : null;

    // ── Data Fetching ──────────────────────────────────────────────────────────
    const fetchPieces = useCallback(async () => {
        try {
            const r = await fetch(`${apiBase}/api/v1/inventory/pieces?limit=500`, { headers: getAuthHeaders() });
            const d = await r.json();
            setPieces(d.items || []);
        } catch { /* silent */ }
    }, []);

    const fetchStockLevels = useCallback(async () => {
        try {
            const r = await fetch(`${apiBase}/api/v1/inventory/stock?size=500`, { headers: getAuthHeaders() });
            const d = await r.json();
            setStockLevels(d.items || []);
        } catch { /* silent */ }
    }, []);

    const fetchAlerts = useCallback(async () => {
        try {
            const r = await fetch(`${apiBase}/api/v1/inventory/stock/alertes?size=500`, { headers: getAuthHeaders() });
            const d = await r.json();
            setAlerts(d.items || []);
        } catch { /* silent */ }
    }, []);

    const fetchMovements = useCallback(async () => {
        try {
            const r = await fetch(`${apiBase}/api/v1/inventory/stock/movements?limit=100`, { headers: getAuthHeaders() });
            const d = await r.json();
            setMovements(d.items || []);
        } catch { /* silent */ }
    }, []);

    const fetchAll = useCallback(async () => {
        setLoading(true);
        await Promise.all([fetchPieces(), fetchStockLevels(), fetchAlerts(), fetchMovements()]);
        setLoading(false);
    }, [fetchPieces, fetchStockLevels, fetchAlerts, fetchMovements]);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    // ── Keyboard shortcuts ─────────────────────────────────────────────────────
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            // Don't fire when typing in an input/select/textarea
            if (['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) return;
            if (e.key === 'n' || e.key === 'N') { e.preventDefault(); if (canManage) openCreatePiece(); }
            if (e.key === 'a' || e.key === 'A') { e.preventDefault(); if (canManage) openStockDialog('add'); }
            if (e.key === 'c' || e.key === 'C') { e.preventDefault(); if (canConsume) openStockDialog('consume'); }
            if (e.key === '/') { e.preventDefault(); searchRef.current?.focus(); }
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [canManage, canConsume]);  

    // ── Piece CRUD ─────────────────────────────────────────────────────────────
    const openCreatePiece = () => {
        setEditingPiece(null);
        setPieceForm({ reference: '', name: '', description: '', unit_price: '', category: '', min_stock: '5' });
        setPieceDialogOpen(true);
    };

    const openEditPiece = (piece: Piece) => {
        setEditingPiece(piece);
        setPieceForm({
            reference: piece.reference,
            name: piece.name,
            description: piece.description || '',
            unit_price: piece.unit_price?.toString() || '',
            category: piece.category || '',
            min_stock: piece.min_stock?.toString() || '5',
        });
        setPieceDialogOpen(true);
    };

    const handlePieceSubmit = async () => {
        try {
            const body = {
                reference: pieceForm.reference,
                name: pieceForm.name,
                description: pieceForm.description || null,
                unit_price: pieceForm.unit_price ? parseFloat(pieceForm.unit_price) : null,
                category: pieceForm.category || null,
                min_stock: parseInt(pieceForm.min_stock) || 5,
            };
            const url = editingPiece
                ? `${apiBase}/api/v1/inventory/pieces/${editingPiece.id}`
                : `${apiBase}/api/v1/inventory/pieces`;
            const r = await fetch(url, { method: editingPiece ? 'PUT' : 'POST', headers: getAuthHeaders(), body: JSON.stringify(body) });
            if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as { detail?: string }).detail || 'Erreur'); }
            toast({ title: 'Succès', description: editingPiece ? 'Pièce mise à jour' : 'Pièce créée' });
            setPieceDialogOpen(false);
            fetchAll();
        } catch (e) {
            toast({ title: 'Erreur', description: e instanceof Error ? e.message : 'Erreur', variant: 'destructive' });
        }
    };

    const handleDeletePiece = async () => {
        if (!deletingPiece) return;
        try {
            await fetch(`${apiBase}/api/v1/inventory/pieces/${deletingPiece.id}`, { method: 'DELETE', headers: getAuthHeaders() });
            toast({ title: 'Succès', description: 'Pièce supprimée' });
            setDeleteDialogOpen(false);
            setDeletingPiece(null);
            fetchAll();
        } catch {
            toast({ title: 'Erreur', description: 'Suppression échouée', variant: 'destructive' });
        }
    };

    // ── Stock Operations ───────────────────────────────────────────────────────
    const openStockDialog = (action: 'add' | 'consume', pieceId?: number, qty?: number) => {
        setStockAction(action);
        setStockForm({
            piece_id: pieceId?.toString() ?? '',
            quantity: qty?.toString() ?? '',
            reference: '',
        });
        setStockDialogOpen(true);
    };

    const handleStockSubmit = async () => {
        const qty = parseInt(stockForm.quantity);
        if (stockAction === 'consume' && selectedPieceStock && qty > selectedPieceStock.quantity) {
            toast({ title: 'Stock insuffisant', description: `Disponible : ${selectedPieceStock.quantity}`, variant: 'destructive' });
            return;
        }
        try {
            const url = stockAction === 'add'
                ? `${apiBase}/api/v1/inventory/stock`
                : `${apiBase}/api/v1/inventory/stock/consume`;
            const r = await fetch(url, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ piece_id: parseInt(stockForm.piece_id), quantity: qty, reference: stockForm.reference || null }),
            });
            if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error((e as { detail?: string }).detail || 'Erreur'); }
            toast({
                title: 'Succès',
                description: stockAction === 'add'
                    ? `+${qty} unité(s) — ${selectedPieceInfo?.name ?? ''}`
                    : `-${qty} unité(s) consommée(s) — ${selectedPieceInfo?.name ?? ''}`,
            });
            setStockDialogOpen(false);
            await fetchAll();
        } catch (e) {
            toast({ title: 'Erreur', description: e instanceof Error ? e.message : 'Erreur', variant: 'destructive' });
        }
    };

    // ── Filtering ──────────────────────────────────────────────────────────────
    const filteredPieces = pieces.filter((p) =>
        p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.reference.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (p.category || '').toLowerCase().includes(searchTerm.toLowerCase())
    );

    // ── Derived alerts: backend alerts + pieces with zero stock entry ──────────
    const stockedPieceIds = new Set(stockLevels.map((s) => s.piece_id));
    const noStockAlerts: StockAlert[] = pieces
        .filter((p) => !stockedPieceIds.has(p.id))
        .map((p) => ({
            piece_id: p.id,
            piece_name: p.name,
            piece_reference: p.reference,
            current_quantity: 0,
            min_stock: p.min_stock ?? 0,
            deficit: p.min_stock ?? 0,
        }));
    const allAlerts = [...alerts, ...noStockAlerts];

    // ── Loading ────────────────────────────────────────────────────────────────
    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
            </div>
        );
    }

    const totalStockValue = stockLevels.reduce((sum, s) => {
        const price = pieces.find((p) => p.id === s.piece_id)?.unit_price ?? 0;
        return sum + s.quantity * price;
    }, 0);

    // ── Render ─────────────────────────────────────────────────────────────────
    return (
        <div className="space-y-5">

            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Package className="h-7 w-7 text-blue-400" />
                        Gestion des Stocks
                    </h1>
                    <p className="text-blue-400 mt-0.5 text-sm">
                        {pieces.length} pièces · {stockLevels.length} références en stock
                        {totalStockValue > 0 && ` · valeur estimée ${totalStockValue.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`}
                    </p>
                </div>
                {/* Keyboard hint */}
                <p className="text-xs text-blue-500 hidden md:block">
                    Raccourcis&nbsp;:&nbsp;
                    <kbd className="font-mono bg-slate-700 px-1 rounded">N</kbd> nouvelle &nbsp;
                    <kbd className="font-mono bg-slate-700 px-1 rounded">A</kbd> entrée &nbsp;
                    <kbd className="font-mono bg-slate-700 px-1 rounded">C</kbd> sortie &nbsp;
                    <kbd className="font-mono bg-slate-700 px-1 rounded">/</kbd> recherche
                </p>
            </div>

            {/* ── Quick Actions Panel (always visible, context-aware) ── */}
            <QuickActionsPanel
                alerts={allAlerts}
                canManage={canManage}
                canConsume={canConsume}
                onNewPiece={openCreatePiece}
                onAddStock={(id, qty) => openStockDialog('add', id, qty)}
                onConsume={(id) => openStockDialog('consume', id)}
                onGoToAlerts={() => setActiveTab('alerts')}
            />

            {/* Summary KPI Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <Card className="cursor-pointer hover:border-blue-400 transition-colors" onClick={openCreatePiece}>
                    <CardHeader className="pb-2 pt-3 px-4">
                        <CardDescription className="text-xs flex items-center gap-1">
                            <BoxIcon className="h-3 w-3" /> Pièces catalogue
                        </CardDescription>
                        <CardTitle className="text-2xl">{pieces.length}</CardTitle>
                    </CardHeader>
                </Card>
                <Card className="cursor-pointer hover:border-green-400 transition-colors" onClick={() => openStockDialog('add')}>
                    <CardHeader className="pb-2 pt-3 px-4">
                        <CardDescription className="text-xs flex items-center gap-1">
                            <ArrowUpCircle className="h-3 w-3" /> Articles en stock
                        </CardDescription>
                        <CardTitle className="text-2xl">{stockLevels.length}</CardTitle>
                    </CardHeader>
                </Card>
                <Card
                    className={`cursor-pointer transition-colors ${allAlerts.length > 0 ? 'border-orange-400 bg-orange-950/20 hover:border-orange-300' : 'hover:border-gray-400'}`}
                    onClick={() => setActiveTab('alerts')}
                >
                    <CardHeader className="pb-2 pt-3 px-4">
                        <CardDescription className={`text-xs flex items-center gap-1 ${allAlerts.length > 0 ? 'text-orange-400' : ''}`}>
                            {allAlerts.length > 0 && <AlertTriangle className="h-3 w-3" />}
                            Alertes stock
                        </CardDescription>
                        <CardTitle className={`text-2xl ${allAlerts.length > 0 ? 'text-orange-400' : ''}`}>
                            {allAlerts.length}
                        </CardTitle>
                    </CardHeader>
                </Card>
                <Card className="cursor-pointer hover:border-purple-400 transition-colors" onClick={() => setActiveTab('history')}>
                    <CardHeader className="pb-2 pt-3 px-4">
                        <CardDescription className="text-xs">Mouvements récents</CardDescription>
                        <CardTitle className="text-2xl">{movements.length}</CardTitle>
                    </CardHeader>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <div className="flex items-center justify-between flex-wrap gap-3">
                    <TabsList>
                        <TabsTrigger value="stock">
                            <Package className="mr-1.5 h-3.5 w-3.5" /> Pièces & Stock
                        </TabsTrigger>
                        <TabsTrigger value="alerts" className="relative">
                            <AlertTriangle className="mr-1.5 h-3.5 w-3.5" />
                            Alertes
                            {allAlerts.length > 0 && (
                                <Badge variant="destructive" className="ml-1.5 text-[10px] px-1.5 py-0 leading-4">
                                    {allAlerts.length}
                                </Badge>
                            )}
                        </TabsTrigger>
                        <TabsTrigger value="history">Historique</TabsTrigger>
                    </TabsList>

                    {/* Inline search — / shortcut */}
                    <div className="relative w-64">
                        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-blue-400" />
                        <Input
                            ref={searchRef}
                            placeholder="Rechercher… (/)"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-8 h-8 text-sm"
                        />
                    </div>
                </div>

                {/* ── Pièces & Stock Tab (unified: all pieces + stock info) ──── */}
                <TabsContent value="stock" className="mt-3">
                    <div className="border rounded-lg overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Référence</TableHead>
                                    <TableHead>Nom</TableHead>
                                    <TableHead>Catégorie</TableHead>
                                    <TableHead>Prix</TableHead>
                                    <TableHead className="text-center">Qté</TableHead>
                                    <TableHead className="text-center">Min.</TableHead>
                                    <TableHead>Statut</TableHead>
                                    <TableHead className="text-right">Actions</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredPieces.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={8} className="text-center text-blue-300 py-10">
                                            Aucune pièce trouvée
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredPieces.map((piece) => {
                                        const stock = stockLevels.find((s) => s.piece_id === piece.id);
                                        const qty = stock?.quantity ?? null;
                                        const minStock = piece.min_stock ?? stock?.min_stock ?? null;
                                        const noStock = qty === null;
                                        const isOut  = qty === 0;
                                        const isLow  = !noStock && !isOut && minStock !== null && qty < minStock;
                                        const deficit = (isOut || isLow) && minStock ? minStock - (qty ?? 0) : 0;

                                        let rowClass = '';
                                        if (isOut) {
                                            rowClass = 'bg-red-950/20';
                                        } else if (isLow) {
                                            rowClass = 'bg-orange-950/15';
                                        }

                                        let qtyClass = 'text-green-400';
                                        if (isOut) {
                                            qtyClass = 'text-red-400';
                                        } else if (isLow) {
                                            qtyClass = 'text-orange-400';
                                        }

                                        let stockBadge: React.ReactNode;
                                        if (noStock) {
                                            stockBadge = <Badge className="bg-slate-800 text-slate-400 border border-slate-600 text-xs">Pas de stock</Badge>;
                                        } else if (isOut) {
                                            stockBadge = <Badge className="bg-red-900/60 text-red-300 border border-red-500/40 text-xs">Rupture</Badge>;
                                        } else if (isLow) {
                                            stockBadge = <Badge className="bg-orange-900/60 text-orange-300 border border-orange-500/40 text-xs">Bas — manque {deficit}</Badge>;
                                        } else {
                                            stockBadge = <Badge className="bg-green-900/60 text-green-300 border border-green-500/40 text-xs">OK</Badge>;
                                        }

                                        return (
                                            <TableRow
                                                key={piece.id}
                                                className={rowClass}
                                            >
                                                <TableCell className="font-mono text-xs text-blue-300">{piece.reference}</TableCell>
                                                <TableCell className="font-medium">{piece.name}</TableCell>
                                                <TableCell>
                                                    {piece.category && <Badge variant="secondary" className="text-xs">{piece.category}</Badge>}
                                                </TableCell>
                                                <TableCell className="text-sm">
                                                    {piece.unit_price ? `${piece.unit_price.toFixed(2)} €` : '—'}
                                                </TableCell>
                                                <TableCell className="text-center">
                                                    {noStock
                                                        ? <span className="text-slate-500 text-sm">—</span>
                                                        : <span className={`font-bold text-base ${qtyClass}`}>{qty}</span>
                                                    }
                                                </TableCell>
                                                <TableCell className="text-center text-blue-300">{minStock ?? '—'}</TableCell>
                                                <TableCell>
                                                    {stockBadge}
                                                </TableCell>
                                                <TableCell>
                                                    <div className="flex gap-1 justify-end">
                                                        {canManage && (
                                                            <button
                                                                onClick={() => openStockDialog('add', piece.id, isLow || isOut ? deficit : undefined)}
                                                                className="flex items-center gap-0.5 rounded border border-green-500/40 bg-green-950/30
                                                                           px-2 py-1 text-xs text-green-400 hover:bg-green-500/20 transition-all"
                                                                title="Entrée stock"
                                                            >
                                                                <Plus className="h-3 w-3" /> Entrée
                                                            </button>
                                                        )}
                                                        {canConsume && stock && stock.quantity > 0 && (
                                                            <button
                                                                onClick={() => openStockDialog('consume', piece.id)}
                                                                className="flex items-center gap-0.5 rounded border border-orange-500/40 bg-orange-950/30
                                                                           px-2 py-1 text-xs text-orange-400 hover:bg-orange-500/20 transition-all"
                                                                title="Sortie stock"
                                                            >
                                                                <Minus className="h-3 w-3" /> Sortie
                                                            </button>
                                                        )}
                                                        {canManage && (
                                                            <>
                                                                <button
                                                                    onClick={() => setLinkerPiece(piece)}
                                                                    className="rounded border border-violet-500/40 bg-violet-950/30 px-2 py-1
                                                                               text-xs text-violet-400 hover:bg-violet-500/20 transition-all"
                                                                    title="Lier aux machines"
                                                                >
                                                                    <Link2 className="h-3 w-3" />
                                                                </button>
                                                                <button
                                                                    onClick={() => openEditPiece(piece)}
                                                                    className="rounded border border-blue-500/30 bg-blue-950/30 px-2 py-1
                                                                               text-xs text-blue-400 hover:bg-blue-500/20 transition-all"
                                                                    title="Modifier"
                                                                >
                                                                    <Edit className="h-3 w-3" />
                                                                </button>
                                                                <button
                                                                    onClick={() => { setDeletingPiece(piece); setDeleteDialogOpen(true); }}
                                                                    className="rounded border border-red-500/30 bg-red-950/30 px-2 py-1
                                                                               text-xs text-red-400 hover:bg-red-500/20 transition-all"
                                                                    title="Supprimer"
                                                                >
                                                                    <Trash2 className="h-3 w-3" />
                                                                </button>
                                                            </>
                                                        )}
                                                    </div>
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </TabsContent>

                {/* ── Alerts Tab ─────────────────────────────────────────────── */}
                <TabsContent value="alerts" className="mt-3 space-y-3">
                    {allAlerts.length === 0 ? (
                        <Card>
                            <CardContent className="flex flex-col items-center justify-center py-16 gap-3 text-green-400">
                                <CheckCircle2 className="h-12 w-12" />
                                <p className="text-lg font-medium">Tous les stocks sont suffisants</p>
                                <p className="text-sm text-blue-300">Aucune alerte de réapprovisionnement active</p>
                            </CardContent>
                        </Card>
                    ) : (
                        allAlerts.map((alert) => (
                            <Card
                                key={alert.piece_id}
                                className={`border-l-4 ${alert.current_quantity === 0 ? 'border-l-red-500 bg-red-950/10' : 'border-l-orange-400 bg-orange-950/10'}`}
                            >
                                <CardContent className="flex items-center justify-between py-4 px-5 gap-4 flex-wrap">
                                    {/* Info */}
                                    <div className="flex items-center gap-4 min-w-0">
                                        <div className={`p-2 rounded-full ${alert.current_quantity === 0 ? 'bg-red-900/50' : 'bg-orange-900/50'}`}>
                                            <AlertTriangle className={`h-5 w-5 ${alert.current_quantity === 0 ? 'text-red-400' : 'text-orange-400'}`} />
                                        </div>
                                        <div className="min-w-0">
                                            <p className="font-semibold text-white truncate">{alert.piece_name}</p>
                                            <p className="text-xs text-blue-400">Réf. {alert.piece_reference}</p>
                                        </div>
                                    </div>

                                    {/* Stock numbers */}
                                    <div className="flex items-center gap-6 text-sm">
                                        <div className="text-center">
                                            <p className={`text-2xl font-bold ${alert.current_quantity === 0 ? 'text-red-400' : 'text-orange-400'}`}>
                                                {alert.current_quantity}
                                            </p>
                                            <p className="text-xs text-blue-400">En stock</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-2xl font-bold text-blue-300">{alert.min_stock}</p>
                                            <p className="text-xs text-blue-400">Minimum</p>
                                        </div>
                                        <div className="text-center">
                                            <p className="text-2xl font-bold text-white">{alert.deficit}</p>
                                            <p className="text-xs text-blue-400">À commander</p>
                                        </div>
                                    </div>

                                    {/* Quick actions on the alert itself */}
                                    <div className="flex gap-2">
                                        {canManage && (
                                            <Button
                                                size="sm"
                                                className="bg-green-700 hover:bg-green-600 text-white"
                                                onClick={() => openStockDialog('add', alert.piece_id, alert.deficit)}
                                            >
                                                <ArrowUpCircle className="mr-1.5 h-4 w-4" />
                                                Réapprovisionner +{alert.deficit}
                                            </Button>
                                        )}
                                        {canConsume && alert.current_quantity > 0 && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10"
                                                onClick={() => openStockDialog('consume', alert.piece_id)}
                                            >
                                                <ArrowDownCircle className="mr-1.5 h-4 w-4" />
                                                Sortie
                                            </Button>
                                        )}
                                    </div>
                                </CardContent>
                            </Card>
                        ))
                    )}
                </TabsContent>

                {/* ── History Tab ────────────────────────────────────────────── */}
                <TabsContent value="history" className="mt-3">
                    <div className="border rounded-lg overflow-hidden">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Pièce</TableHead>
                                    <TableHead>Type</TableHead>
                                    <TableHead className="text-center">Quantité</TableHead>
                                    <TableHead>Référence</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {movements.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center text-blue-300 py-10">
                                            Aucun mouvement enregistré
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    movements.map((m) => (
                                        <TableRow key={m.id}>
                                            <TableCell className="text-xs text-blue-300 whitespace-nowrap">
                                                {m.created_at ? new Date(m.created_at).toLocaleString('fr-FR') : '—'}
                                            </TableCell>
                                            <TableCell className="font-medium">{m.piece_name}</TableCell>
                                            <TableCell>
                                                {m.movement_type === 'in' ? (
                                                    <span className="flex items-center gap-1 text-green-400 text-xs font-medium">
                                                        <ArrowUpCircle className="h-3.5 w-3.5" /> Entrée
                                                    </span>
                                                ) : (
                                                    <span className="flex items-center gap-1 text-orange-400 text-xs font-medium">
                                                        <ArrowDownCircle className="h-3.5 w-3.5" /> Sortie
                                                    </span>
                                                )}
                                            </TableCell>
                                            <TableCell className="text-center font-semibold">{m.quantity}</TableCell>
                                            <TableCell className="text-xs text-blue-300">{m.reference || '—'}</TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </TabsContent>
            </Tabs>

            {/* ── Dialogs ────────────────────────────────────────────────────── */}

            {/* Piece Create/Edit */}
            <Dialog open={pieceDialogOpen} onOpenChange={setPieceDialogOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{editingPiece ? 'Modifier la pièce' : 'Nouvelle pièce'}</DialogTitle>
                        <DialogDescription>
                            {editingPiece ? 'Modifiez les informations de la pièce.' : 'Ajoutez une nouvelle pièce au catalogue.'}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Référence *</Label>
                                <Input value={pieceForm.reference} onChange={(e) => setPieceForm({ ...pieceForm, reference: e.target.value })} placeholder="REF-001" disabled={!!editingPiece} />
                            </div>
                            <div className="space-y-2">
                                <Label>Nom *</Label>
                                <Input value={pieceForm.name} onChange={(e) => setPieceForm({ ...pieceForm, name: e.target.value })} placeholder="Nom de la pièce" />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label>Description</Label>
                            <Input value={pieceForm.description} onChange={(e) => setPieceForm({ ...pieceForm, description: e.target.value })} placeholder="Optionnel" />
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                            <div className="space-y-2">
                                <Label>Prix (€)</Label>
                                <Input type="number" step="0.01" value={pieceForm.unit_price} onChange={(e) => setPieceForm({ ...pieceForm, unit_price: e.target.value })} placeholder="0.00" />
                            </div>
                            <div className="space-y-2">
                                <Label>Catégorie</Label>
                                <Select value={pieceForm.category} onValueChange={(v) => setPieceForm({ ...pieceForm, category: v })}>
                                    <SelectTrigger><SelectValue placeholder="Choisir…" /></SelectTrigger>
                                    <SelectContent>
                                        {CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label>Stock min.</Label>
                                <Input type="number" value={pieceForm.min_stock} onChange={(e) => setPieceForm({ ...pieceForm, min_stock: e.target.value })} placeholder="5" />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPieceDialogOpen(false)}>Annuler</Button>
                        <Button onClick={handlePieceSubmit} disabled={!pieceForm.reference || !pieceForm.name}>
                            {editingPiece ? 'Mettre à jour' : 'Créer'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Delete Confirm */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Confirmer la suppression</DialogTitle>
                        <DialogDescription>
                            Supprimer « {deletingPiece?.name} » (Réf. {deletingPiece?.reference}) ? Action irréversible.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>Annuler</Button>
                        <Button variant="destructive" onClick={handleDeletePiece}>Supprimer</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* Stock Add / Consume */}
            <Dialog open={stockDialogOpen} onOpenChange={setStockDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle className="flex items-center gap-2">
                            {stockAction === 'add'
                                ? <><ArrowUpCircle className="h-5 w-5 text-green-400" /> Entrée de stock</>
                                : <><ArrowDownCircle className="h-5 w-5 text-orange-400" /> Sortie de stock</>}
                        </DialogTitle>
                        <DialogDescription>
                            {stockAction === 'add'
                                ? 'Livraison, retour fournisseur, réapprovisionnement…'
                                : 'Utilisation en intervention, panne, prélèvement…'}
                        </DialogDescription>
                    </DialogHeader>

                    <div className="space-y-4">
                        {/* Piece selector */}
                        <div className="space-y-2">
                            <Label>Pièce *</Label>
                            <Select value={stockForm.piece_id} onValueChange={(v) => setStockForm({ ...stockForm, piece_id: v })}>
                                <SelectTrigger>
                                    <SelectValue placeholder="Sélectionner une pièce…" />
                                </SelectTrigger>
                                <SelectContent>
                                    {pieces.map((p) => (
                                        <SelectItem key={p.id} value={p.id.toString()}>
                                            {p.reference} — {p.name}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* Stock context badge */}
                        {stockForm.piece_id && (() => {
                            let stockBadgeClass: string;
                            if (!selectedPieceStock || selectedPieceStock.quantity === 0) {
                                stockBadgeClass = 'bg-red-950/40 border-red-500/40 text-red-300';
                            } else if (selectedPieceStock.min_stock != null && selectedPieceStock.quantity < selectedPieceStock.min_stock) {
                                stockBadgeClass = 'bg-orange-950/40 border-orange-500/40 text-orange-300';
                            } else {
                                stockBadgeClass = 'bg-green-950/40 border-green-500/40 text-green-300';
                            }
                            return (
                            <div className={`rounded-md px-3 py-2.5 text-sm flex items-center justify-between border ${stockBadgeClass}`}
                            >
                                <span className="font-medium">{selectedPieceInfo?.name}</span>
                                <span className="font-mono text-lg font-bold">
                                    {selectedPieceStock?.quantity ?? 0}
                                    <span className="text-xs font-normal ml-1 opacity-70">
                                        en stock{selectedPieceInfo?.min_stock ? ` (min. ${selectedPieceInfo.min_stock})` : ''}
                                    </span>
                                </span>
                            </div>
                            );
                        })()}

                        {/* Quantity */}
                        <div className="space-y-2">
                            <Label>Quantité *</Label>
                            <Input
                                type="number"
                                min="1"
                                max={stockAction === 'consume' && selectedPieceStock ? selectedPieceStock.quantity : undefined}
                                value={stockForm.quantity}
                                onChange={(e) => setStockForm({ ...stockForm, quantity: e.target.value })}
                                placeholder="Ex. 5"
                                autoFocus
                                className={
                                    stockAction === 'consume' &&
                                    selectedPieceStock &&
                                    parseInt(stockForm.quantity) > selectedPieceStock.quantity
                                        ? 'border-red-500 focus:ring-red-500'
                                        : ''
                                }
                            />
                            {stockAction === 'consume' && selectedPieceStock &&
                                parseInt(stockForm.quantity) > selectedPieceStock.quantity && (
                                <p className="text-xs text-red-400 flex items-center gap-1">
                                    <AlertTriangle className="h-3 w-3" />
                                    Dépasse le stock disponible ({selectedPieceStock.quantity})
                                </p>
                            )}
                        </div>

                        {/* Optional reference */}
                        <div className="space-y-2">
                            <Label>Référence <span className="text-blue-400 text-xs">(optionnel)</span></Label>
                            <Input
                                value={stockForm.reference}
                                onChange={(e) => setStockForm({ ...stockForm, reference: e.target.value })}
                                placeholder={stockAction === 'add' ? 'N° bon de commande, livraison…' : 'N° OT, intervention, demande…'}
                            />
                        </div>
                    </div>

                    <DialogFooter>
                        <Button variant="outline" onClick={() => setStockDialogOpen(false)}>Annuler</Button>
                        <Button
                            onClick={handleStockSubmit}
                            disabled={
                                !stockForm.piece_id ||
                                !stockForm.quantity ||
                                parseInt(stockForm.quantity) < 1 ||
                                (stockAction === 'consume' && !!selectedPieceStock && parseInt(stockForm.quantity) > selectedPieceStock.quantity)
                            }
                            className={stockAction === 'add' ? 'bg-green-700 hover:bg-green-600' : 'bg-orange-700 hover:bg-orange-600'}
                        >
                            {stockAction === 'add'
                                ? <><ArrowUpCircle className="mr-2 h-4 w-4" />Entrée {stockForm.quantity ? `× ${stockForm.quantity}` : ''}</>
                                : <><ArrowDownCircle className="mr-2 h-4 w-4" />Sortie {stockForm.quantity ? `× ${stockForm.quantity}` : ''}</>
                            }
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {linkerPiece && (
                <PieceMachinesLinker
                    open={linkerPiece !== null}
                    onOpenChange={(o) => { if (!o) setLinkerPiece(null); }}
                    pieceId={linkerPiece.id}
                    pieceName={linkerPiece.name}
                    pieceReference={linkerPiece.reference}
                />
            )}
        </div>
    );
}
