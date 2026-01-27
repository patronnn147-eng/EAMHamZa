import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Search, Plus, FileText, Download, Edit, Trash2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';
import type { Rapport } from '@/lib/types';

export default function Reports() {
  const [reports, setReports] = useState<Rapport[]>([]);
  const [filteredReports, setFilteredReports] = useState<Rapport[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [editingReport, setEditingReport] = useState<Rapport | null>(null);
  const [deletingReport, setDeletingReport] = useState<Rapport | null>(null);
  const [currentUser, setCurrentUser] = useState<{ id: string } | null>(null);
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    identifiant_rapport: '',
    titre: '',
    contenu: '',
  });

  useEffect(() => {
    fetchCurrentUser();
    fetchReports();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = reports.filter(
        (r) =>
          r.titre.toLowerCase().includes(searchTerm.toLowerCase()) ||
          r.identifiant_rapport.toLowerCase().includes(searchTerm.toLowerCase()) ||
          r.contenu.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredReports(filtered);
    } else {
      setFilteredReports(reports);
    }
  }, [searchTerm, reports]);

  const fetchCurrentUser = async () => {
    try {
      const userData = await client.auth.me();
      if (userData.data) {
        setCurrentUser({ id: userData.data.id });
      }
    } catch (error) {
      console.error('Error fetching current user:', error);
    }
  };

  const fetchReports = async () => {
    try {
      const response = await client.entities.rapports.query({
        query: {},
        sort: '-created_at',
        limit: 100
      });
      const reportsList = response.data.items || [];
      setReports(reportsList);
      setFilteredReports(reportsList);
    } catch (error) {
      console.error('Error fetching reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenDialog = (report?: Rapport) => {
    if (report) {
      setEditingReport(report);
      setFormData({
        identifiant_rapport: report.identifiant_rapport,
        titre: report.titre,
        contenu: report.contenu,
      });
    } else {
      setEditingReport(null);
      setFormData({
        identifiant_rapport: `RPT-${Date.now()}`,
        titre: '',
        contenu: '',
      });
    }
    setDialogOpen(true);
  };

  const handleSubmit = async () => {
    try {
      if (!formData.identifiant_rapport.trim() || !formData.titre.trim() || !formData.contenu.trim()) {
        toast({
          title: 'Validation Error',
          description: 'Please fill in all required fields',
          variant: 'destructive',
        });
        return;
      }

      if (!currentUser) {
        toast({
          title: 'Error',
          description: 'User not authenticated',
          variant: 'destructive',
        });
        return;
      }

      const submitData = {
        identifiant_rapport: formData.identifiant_rapport,
        titre: formData.titre,
        contenu: formData.contenu,
        utilisateur_id: currentUser.id,
      };

      if (editingReport) {
        await client.entities.rapports.update({
          id: editingReport.id.toString(),
          data: submitData,
        });
        toast({
          title: 'Success',
          description: 'Report updated successfully',
        });
      } else {
        await client.entities.rapports.create({
          data: submitData,
        });
        toast({
          title: 'Success',
          description: 'Report generated successfully',
        });
      }
      setDialogOpen(false);
      fetchReports();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to save report',
        variant: 'destructive',
      });
    }
  };

  const handleDelete = async () => {
    if (!deletingReport) return;
    
    try {
      await client.entities.rapports.delete({ id: deletingReport.id.toString() });
      toast({
        title: 'Success',
        description: 'Report deleted successfully',
      });
      setDeleteDialogOpen(false);
      setDeletingReport(null);
      fetchReports();
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data?.detail
                  || (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail
                  || (error as { message?: string }).message;
      toast({
        title: 'Error',
        description: detail || 'Failed to delete report',
        variant: 'destructive',
      });
    }
  };

  const handleExport = (report: Rapport) => {
    const content = `${report.titre}\n\nReport ID: ${report.identifiant_rapport}\nDate: ${new Date(report.created_at).toLocaleString()}\n\n${report.contenu}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.identifiant_rapport}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    toast({
      title: 'Success',
      description: 'Report exported successfully',
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Reports</h2>
          <p className="mt-1 text-sm text-gray-500">
            Generate and manage maintenance reports
          </p>
        </div>
        <Button onClick={() => handleOpenDialog()}>
          <Plus className="mr-2 h-4 w-4" />
          Generate Report
        </Button>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search reports by title, ID, or content..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 gap-4">
        {filteredReports.length === 0 ? (
          <Card>
            <CardContent className="text-center py-12">
              <p className="text-gray-500">No reports found</p>
            </CardContent>
          </Card>
        ) : (
          filteredReports.map((report) => (
            <Card key={report.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      {report.titre}
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      {report.identifiant_rapport}
                    </p>
                  </div>
                  <div className="text-sm text-gray-500">
                    {new Date(report.created_at).toLocaleDateString()}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4">
                  <p className="text-sm text-gray-600 line-clamp-3 bg-gray-50 p-3 rounded-md">
                    {report.contenu}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleExport(report)}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Export
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleOpenDialog(report)}
                  >
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-red-600 hover:text-red-700"
                    onClick={() => {
                      setDeletingReport(report);
                      setDeleteDialogOpen(true);
                    }}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingReport ? 'Edit Report' : 'Generate Report'}</DialogTitle>
            <DialogDescription>
              {editingReport ? 'Update report information' : 'Create a new maintenance report'}
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="identifiant_rapport">Report ID *</Label>
              <Input
                id="identifiant_rapport"
                value={formData.identifiant_rapport}
                onChange={(e) => setFormData({ ...formData, identifiant_rapport: e.target.value })}
                placeholder="e.g., RPT-2026-001"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="titre">Title *</Label>
              <Input
                id="titre"
                value={formData.titre}
                onChange={(e) => setFormData({ ...formData, titre: e.target.value })}
                placeholder="Report title"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="contenu">Content *</Label>
              <Textarea
                id="contenu"
                value={formData.contenu}
                onChange={(e) => setFormData({ ...formData, contenu: e.target.value })}
                placeholder="Enter the detailed report content including findings, recommendations, and conclusions..."
                rows={12}
                className="resize-none"
              />
              <p className="text-xs text-gray-500">
                {formData.contenu.length} characters
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit}>
              {editingReport ? 'Update' : 'Generate'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Deletion</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deletingReport?.titre}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}