import { useEffect, useState, useCallback } from 'react';
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
    Search,
    Edit,
    Trash2,
    AlertTriangle,
    ArrowUpCircle,
    ArrowDownCircle,
    BoxIcon,
} from 'lucide-react';

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
    'Électrique',
    'Mécanique',
    'Hydraulique',
    'Pneumatique',
    'Électronique',
    'Consommable',
    'Autre',
];

function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' };
}

export default function InventoryPage() {
    const { user } = useAuth();
    const { toast } = useToast();
    const [activeTab, setActiveTab] = useState('catalog');
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

    // Form data
    const [pieceForm, setPieceForm] = useState({
        reference: '',
        name: '',
        description: '',
        unit_price: '',
        category: '',
        min_stock: '5',
    });
    const [stockForm, setStockForm] = useState({
        piece_id: '',
        quantity: '',
        reference: '',
    });

    const canManage = user?.role === 'ADMIN' || user?.role === 'CHEFTECH';
    const canConsume = canManage || user?.role === 'CHETOP';

    // ---------- Data Fetching ----------
    const fetchPieces = useCallback(async () => {
        try {
            const resp = await fetch(`${apiBase}/api/v1/inventory/pieces?limit=500`, { headers: getAuthHeaders() });
            if (!resp.ok) throw new Error('Failed to fetch pieces');
            const data = await resp.json();
            setPieces(data.items || []);
        } catch (e) {
            console.error('Error fetching pieces:', e);
        }
    }, []);

    const fetchStockLevels = useCallback(async () => {
        try {
            const resp = await fetch(`${apiBase}/api/v1/inventory/stock`, { headers: getAuthHeaders() });
            if (!resp.ok) throw new Error('Failed to fetch stock');
            const data = await resp.json();
            setStockLevels(data || []);
        } catch (e) {
            console.error('Error fetching stock:', e);
        }
    }, []);

    const fetchAlerts = useCallback(async () => {
        try {
            const resp = await fetch(`${apiBase}/api/v1/inventory/stock/alertes`, { headers: getAuthHeaders() });
            if (!resp.ok) throw new Error('Failed to fetch alerts');
            const data = await resp.json();
            setAlerts(data || []);
        } catch (e) {
            console.error('Error fetching alerts:', e);
        }
    }, []);

    const fetchMovements = useCallback(async () => {
        try {
            const resp = await fetch(`${apiBase}/api/v1/inventory/stock/movements?limit=100`, { headers: getAuthHeaders() });
            if (!resp.ok) throw new Error('Failed to fetch movements');
            const data = await resp.json();
            setMovements(data || []);
        } catch (e) {
            console.error('Error fetching movements:', e);
        }
    }, []);

    const fetchAll = useCallback(async () => {
        setLoading(true);
        await Promise.all([fetchPieces(), fetchStockLevels(), fetchAlerts(), fetchMovements()]);
        setLoading(false);
    }, [fetchPieces, fetchStockLevels, fetchAlerts, fetchMovements]);

    useEffect(() => {
        fetchAll();
    }, [fetchAll]);

    // ---------- Piece CRUD ----------
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
            const body: Record<string, unknown> = {
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

            const resp = await fetch(url, {
                method: editingPiece ? 'PUT' : 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(body),
            });

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error((err as { detail?: string }).detail || 'Failed');
            }

            toast({
                title: 'Succès',
                description: editingPiece ? 'Pièce mise à jour' : 'Pièce créée',
            });
            setPieceDialogOpen(false);
            fetchAll();
        } catch (e) {
            toast({
                title: 'Erreur',
                description: e instanceof Error ? e.message : 'Erreur lors de la sauvegarde',
                variant: 'destructive',
            });
        }
    };

    const handleDeletePiece = async () => {
        if (!deletingPiece) return;
        try {
            const resp = await fetch(`${apiBase}/api/v1/inventory/pieces/${deletingPiece.id}`, {
                method: 'DELETE',
                headers: getAuthHeaders(),
            });
            if (!resp.ok) throw new Error('Failed to delete piece');
            toast({ title: 'Succès', description: 'Pièce supprimée' });
            setDeleteDialogOpen(false);
            setDeletingPiece(null);
            fetchAll();
        } catch (e) {
            toast({
                title: 'Erreur',
                description: e instanceof Error ? e.message : 'Erreur lors de la suppression',
                variant: 'destructive',
            });
        }
    };

    // ---------- Stock Operations ----------
    const openStockDialog = (action: 'add' | 'consume') => {
        setStockAction(action);
        setStockForm({ piece_id: '', quantity: '', reference: '' });
        setStockDialogOpen(true);
    };

    const handleStockSubmit = async () => {
        try {
            const url = stockAction === 'add'
                ? `${apiBase}/api/v1/inventory/stock`
                : `${apiBase}/api/v1/inventory/stock/consume`;

            const body = {
                piece_id: parseInt(stockForm.piece_id),
                quantity: parseInt(stockForm.quantity),
                reference: stockForm.reference || null,
            };

            const resp = await fetch(url, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(body),
            });

            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                throw new Error((err as { detail?: string }).detail || 'Failed');
            }

            toast({
                title: 'Succès',
                description: stockAction === 'add' ? 'Stock ajouté' : 'Stock consommé',
            });
            setStockDialogOpen(false);
            fetchAll();
        } catch (e) {
            toast({
                title: 'Erreur',
                description: e instanceof Error ? e.message : 'Erreur lors de l\'opération',
                variant: 'destructive',
            });
        }
    };

    // ---------- Filtering ----------
    const filteredPieces = pieces.filter(
        (p) =>
            p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
            p.reference.toLowerCase().includes(searchTerm.toLowerCase()) ||
            (p.category || '').toLowerCase().includes(searchTerm.toLowerCase())
    );

    // ---------- Render ----------
    if (loading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <Package className="h-7 w-7" />
                        Gestion des Stocks
                    </h1>
                    <p className="text-gray-500 mt-1">
                        Catalogue de pièces, niveaux de stock et alertes de réapprovisionnement
                    </p>
                </div>
                <div className="flex gap-2">
                    {canConsume && (
                        <Button variant="outline" onClick={() => openStockDialog('consume')}>
                            <ArrowDownCircle className="mr-2 h-4 w-4" />
                            Consommer
                        </Button>
                    )}
                    {canManage && (
                        <>
                            <Button variant="outline" onClick={() => openStockDialog('add')}>
                                <ArrowUpCircle className="mr-2 h-4 w-4" />
                                Ajouter Stock
                            </Button>
                            <Button onClick={openCreatePiece}>
                                <Plus className="mr-2 h-4 w-4" />
                                Nouvelle Pièce
                            </Button>
                        </>
                    )}
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Pièces au catalogue</CardDescription>
                        <CardTitle className="text-3xl">{pieces.length}</CardTitle>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Articles en stock</CardDescription>
                        <CardTitle className="text-3xl">{stockLevels.length}</CardTitle>
                    </CardHeader>
                </Card>
                <Card className={alerts.length > 0 ? 'border-orange-300 bg-orange-50' : ''}>
                    <CardHeader className="pb-2">
                        <CardDescription className="flex items-center gap-1">
                            {alerts.length > 0 && <AlertTriangle className="h-4 w-4 text-orange-500" />}
                            Alertes stock bas
                        </CardDescription>
                        <CardTitle className={`text-3xl ${alerts.length > 0 ? 'text-orange-600' : ''}`}>
                            {alerts.length}
                        </CardTitle>
                    </CardHeader>
                </Card>
                <Card>
                    <CardHeader className="pb-2">
                        <CardDescription>Mouvements récents</CardDescription>
                        <CardTitle className="text-3xl">{movements.length}</CardTitle>
                    </CardHeader>
                </Card>
            </div>

            {/* Tabs */}
            <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                    <TabsTrigger value="catalog">
                        <BoxIcon className="mr-2 h-4 w-4" />
                        Catalogue
                    </TabsTrigger>
                    <TabsTrigger value="stock">
                        <Package className="mr-2 h-4 w-4" />
                        Niveaux de Stock
                    </TabsTrigger>
                    <TabsTrigger value="alerts" className="relative">
                        <AlertTriangle className="mr-2 h-4 w-4" />
                        Alertes
                        {alerts.length > 0 && (
                            <Badge variant="destructive" className="ml-2 text-xs px-1.5 py-0.5">
                                {alerts.length}
                            </Badge>
                        )}
                    </TabsTrigger>
                    <TabsTrigger value="history">
                        Historique
                    </TabsTrigger>
                </TabsList>

                {/* Catalog Tab */}
                <TabsContent value="catalog" className="space-y-4">
                    <div className="flex items-center gap-4">
                        <div className="relative flex-1 max-w-sm">
                            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                            <Input
                                placeholder="Rechercher une pièce..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                className="pl-10"
                            />
                        </div>
                    </div>

                    <div className="border rounded-lg">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Référence</TableHead>
                                    <TableHead>Nom</TableHead>
                                    <TableHead>Catégorie</TableHead>
                                    <TableHead>Prix unitaire</TableHead>
                                    <TableHead>Stock min.</TableHead>
                                    {canManage && <TableHead className="text-right">Actions</TableHead>}
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {filteredPieces.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={canManage ? 6 : 5} className="text-center text-gray-500 py-8">
                                            Aucune pièce trouvée
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    filteredPieces.map((piece) => (
                                        <TableRow key={piece.id}>
                                            <TableCell className="font-mono text-sm">{piece.reference}</TableCell>
                                            <TableCell className="font-medium">{piece.name}</TableCell>
                                            <TableCell>
                                                {piece.category && (
                                                    <Badge variant="secondary">{piece.category}</Badge>
                                                )}
                                            </TableCell>
                                            <TableCell>
                                                {piece.unit_price ? `${piece.unit_price.toFixed(2)} €` : '—'}
                                            </TableCell>
                                            <TableCell>{piece.min_stock ?? 5}</TableCell>
                                            {canManage && (
                                                <TableCell className="text-right">
                                                    <div className="flex gap-1 justify-end">
                                                        <Button size="sm" variant="ghost" onClick={() => openEditPiece(piece)}>
                                                            <Edit className="h-4 w-4" />
                                                        </Button>
                                                        <Button
                                                            size="sm"
                                                            variant="ghost"
                                                            className="text-red-600 hover:text-red-700"
                                                            onClick={() => {
                                                                setDeletingPiece(piece);
                                                                setDeleteDialogOpen(true);
                                                            }}
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                </TableCell>
                                            )}
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </TabsContent>

                {/* Stock Levels Tab */}
                <TabsContent value="stock" className="space-y-4">
                    <div className="border rounded-lg">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Référence</TableHead>
                                    <TableHead>Pièce</TableHead>
                                    <TableHead>Quantité</TableHead>
                                    <TableHead>Seuil min.</TableHead>
                                    <TableHead>Statut</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {stockLevels.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                                            Aucun stock enregistré
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    stockLevels.map((s) => {
                                        const isLow = s.min_stock != null && s.quantity < s.min_stock;
                                        return (
                                            <TableRow key={s.id} className={isLow ? 'bg-orange-50' : ''}>
                                                <TableCell className="font-mono text-sm">{s.piece_reference}</TableCell>
                                                <TableCell className="font-medium">{s.piece_name}</TableCell>
                                                <TableCell>
                                                    <span className={`font-semibold ${isLow ? 'text-orange-600' : 'text-green-600'}`}>
                                                        {s.quantity}
                                                    </span>
                                                </TableCell>
                                                <TableCell>{s.min_stock ?? '—'}</TableCell>
                                                <TableCell>
                                                    {isLow ? (
                                                        <Badge variant="destructive" className="flex items-center gap-1 w-fit">
                                                            <AlertTriangle className="h-3 w-3" />
                                                            Stock bas
                                                        </Badge>
                                                    ) : (
                                                        <Badge variant="secondary" className="bg-green-100 text-green-800 w-fit">
                                                            OK
                                                        </Badge>
                                                    )}
                                                </TableCell>
                                            </TableRow>
                                        );
                                    })
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </TabsContent>

                {/* Alerts Tab */}
                <TabsContent value="alerts" className="space-y-4">
                    {alerts.length === 0 ? (
                        <Card>
                            <CardContent className="flex flex-col items-center justify-center py-12 text-gray-500">
                                <Package className="h-12 w-12 mb-4 text-green-500" />
                                <p className="text-lg font-medium">Tous les stocks sont suffisants</p>
                                <p className="text-sm">Aucune alerte de réapprovisionnement</p>
                            </CardContent>
                        </Card>
                    ) : (
                        <div className="space-y-3">
                            {alerts.map((alert) => (
                                <Card key={alert.piece_id} className="border-orange-300 bg-orange-50">
                                    <CardContent className="flex items-center justify-between py-4">
                                        <div className="flex items-center gap-4">
                                            <div className="bg-orange-100 p-2 rounded-full">
                                                <AlertTriangle className="h-5 w-5 text-orange-600" />
                                            </div>
                                            <div>
                                                <p className="font-semibold">{alert.piece_name}</p>
                                                <p className="text-sm text-gray-600">Réf: {alert.piece_reference}</p>
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            <p className="text-sm text-gray-500">
                                                Stock actuel: <span className="font-bold text-orange-600">{alert.current_quantity}</span> / Minimum: {alert.min_stock}
                                            </p>
                                            <p className="text-sm font-semibold text-red-600">
                                                Manque: {alert.deficit} unité(s)
                                            </p>
                                        </div>
                                        {canManage && (
                                            <Button
                                                size="sm"
                                                variant="outline"
                                                onClick={() => {
                                                    setStockAction('add');
                                                    setStockForm({ piece_id: alert.piece_id.toString(), quantity: alert.deficit.toString(), reference: '' });
                                                    setStockDialogOpen(true);
                                                }}
                                            >
                                                <ArrowUpCircle className="mr-1 h-4 w-4" />
                                                Réapprovisionner
                                            </Button>
                                        )}
                                    </CardContent>
                                </Card>
                            ))}
                        </div>
                    )}
                </TabsContent>

                {/* History Tab */}
                <TabsContent value="history" className="space-y-4">
                    <div className="border rounded-lg">
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Date</TableHead>
                                    <TableHead>Pièce</TableHead>
                                    <TableHead>Type</TableHead>
                                    <TableHead>Quantité</TableHead>
                                    <TableHead>Référence</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {movements.length === 0 ? (
                                    <TableRow>
                                        <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                                            Aucun mouvement enregistré
                                        </TableCell>
                                    </TableRow>
                                ) : (
                                    movements.map((m) => (
                                        <TableRow key={m.id}>
                                            <TableCell className="text-sm text-gray-500">
                                                {m.created_at ? new Date(m.created_at).toLocaleString('fr-FR') : '—'}
                                            </TableCell>
                                            <TableCell className="font-medium">{m.piece_name}</TableCell>
                                            <TableCell>
                                                {m.movement_type === 'in' ? (
                                                    <Badge className="bg-green-100 text-green-800 flex items-center gap-1 w-fit">
                                                        <ArrowUpCircle className="h-3 w-3" />
                                                        Entrée
                                                    </Badge>
                                                ) : (
                                                    <Badge className="bg-red-100 text-red-800 flex items-center gap-1 w-fit">
                                                        <ArrowDownCircle className="h-3 w-3" />
                                                        Sortie
                                                    </Badge>
                                                )}
                                            </TableCell>
                                            <TableCell className="font-semibold">{m.quantity}</TableCell>
                                            <TableCell className="text-sm text-gray-500">{m.reference || '—'}</TableCell>
                                        </TableRow>
                                    ))
                                )}
                            </TableBody>
                        </Table>
                    </div>
                </TabsContent>
            </Tabs>

            {/* ---------- Piece Create/Edit Dialog ---------- */}
            <Dialog open={pieceDialogOpen} onOpenChange={setPieceDialogOpen}>
                <DialogContent className="max-w-lg">
                    <DialogHeader>
                        <DialogTitle>{editingPiece ? 'Modifier la pièce' : 'Nouvelle pièce'}</DialogTitle>
                        <DialogDescription>
                            {editingPiece
                                ? 'Modifiez les informations de la pièce de rechange.'
                                : 'Ajoutez une nouvelle pièce de rechange au catalogue.'}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="reference">Référence *</Label>
                                <Input
                                    id="reference"
                                    value={pieceForm.reference}
                                    onChange={(e) => setPieceForm({ ...pieceForm, reference: e.target.value })}
                                    placeholder="REF-001"
                                    disabled={!!editingPiece}
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="name">Nom *</Label>
                                <Input
                                    id="name"
                                    value={pieceForm.name}
                                    onChange={(e) => setPieceForm({ ...pieceForm, name: e.target.value })}
                                    placeholder="Nom de la pièce"
                                />
                            </div>
                        </div>
                        <div className="space-y-2">
                            <Label htmlFor="description">Description</Label>
                            <Input
                                id="description"
                                value={pieceForm.description}
                                onChange={(e) => setPieceForm({ ...pieceForm, description: e.target.value })}
                                placeholder="Description optionnelle"
                            />
                        </div>
                        <div className="grid grid-cols-3 gap-4">
                            <div className="space-y-2">
                                <Label htmlFor="unit_price">Prix unitaire (€)</Label>
                                <Input
                                    id="unit_price"
                                    type="number"
                                    step="0.01"
                                    value={pieceForm.unit_price}
                                    onChange={(e) => setPieceForm({ ...pieceForm, unit_price: e.target.value })}
                                    placeholder="0.00"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="category">Catégorie</Label>
                                <Select
                                    value={pieceForm.category}
                                    onValueChange={(val) => setPieceForm({ ...pieceForm, category: val })}
                                >
                                    <SelectTrigger>
                                        <SelectValue placeholder="Choisir..." />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {CATEGORIES.map((c) => (
                                            <SelectItem key={c} value={c}>
                                                {c}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="min_stock">Stock minimum</Label>
                                <Input
                                    id="min_stock"
                                    type="number"
                                    value={pieceForm.min_stock}
                                    onChange={(e) => setPieceForm({ ...pieceForm, min_stock: e.target.value })}
                                    placeholder="5"
                                />
                            </div>
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setPieceDialogOpen(false)}>
                            Annuler
                        </Button>
                        <Button
                            onClick={handlePieceSubmit}
                            disabled={!pieceForm.reference || !pieceForm.name}
                        >
                            {editingPiece ? 'Mettre à jour' : 'Créer'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ---------- Delete Confirmation Dialog ---------- */}
            <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Confirmer la suppression</DialogTitle>
                        <DialogDescription>
                            Êtes-vous sûr de vouloir supprimer la pièce "{deletingPiece?.name}" (Réf: {deletingPiece?.reference}) ?
                            Cette action est irréversible.
                        </DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
                            Annuler
                        </Button>
                        <Button variant="destructive" onClick={handleDeletePiece}>
                            Supprimer
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            {/* ---------- Stock Add/Consume Dialog ---------- */}
            <Dialog open={stockDialogOpen} onOpenChange={setStockDialogOpen}>
                <DialogContent className="max-w-md">
                    <DialogHeader>
                        <DialogTitle>
                            {stockAction === 'add' ? 'Ajouter du stock' : 'Consommer du stock'}
                        </DialogTitle>
                        <DialogDescription>
                            {stockAction === 'add'
                                ? 'Enregistrez une entrée de stock (livraison, retour, etc.)'
                                : 'Enregistrez une sortie de stock (utilisation en intervention, etc.)'}
                        </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4">
                        <div className="space-y-2">
                            <Label>Pièce *</Label>
                            <Select
                                value={stockForm.piece_id}
                                onValueChange={(val) => setStockForm({ ...stockForm, piece_id: val })}
                            >
                                <SelectTrigger>
                                    <SelectValue placeholder="Sélectionner une pièce..." />
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
                        <div className="space-y-2">
                            <Label>Quantité *</Label>
                            <Input
                                type="number"
                                min="1"
                                value={stockForm.quantity}
                                onChange={(e) => setStockForm({ ...stockForm, quantity: e.target.value })}
                                placeholder="Quantité"
                            />
                        </div>
                        <div className="space-y-2">
                            <Label>Référence (optionnel)</Label>
                            <Input
                                value={stockForm.reference}
                                onChange={(e) => setStockForm({ ...stockForm, reference: e.target.value })}
                                placeholder="N° bon de commande, intervention..."
                            />
                        </div>
                    </div>
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setStockDialogOpen(false)}>
                            Annuler
                        </Button>
                        <Button
                            onClick={handleStockSubmit}
                            disabled={!stockForm.piece_id || !stockForm.quantity}
                            className={stockAction === 'consume' ? 'bg-orange-600 hover:bg-orange-700' : ''}
                        >
                            {stockAction === 'add' ? 'Ajouter' : 'Consommer'}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}
