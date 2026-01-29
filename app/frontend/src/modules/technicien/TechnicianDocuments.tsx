import { useEffect, useState } from 'react';
import { client } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Search, FileText, Download, Eye } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface Archive {
  id: number;
  identifiant_archive: string;
  nom: string;
  date_archivage: string;
  type: string;
  object_key: string;
  ordre_travail_id: number | null;
  created_at: string;
}

export default function TechnicianDocuments() {
  const [documents, setDocuments] = useState<Archive[]>([]);
  const [filteredDocuments, setFilteredDocuments] = useState<Archive[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (searchTerm) {
      const filtered = documents.filter(
        (d) =>
          d.nom.toLowerCase().includes(searchTerm.toLowerCase()) ||
          d.type.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredDocuments(filtered);
    } else {
      setFilteredDocuments(documents);
    }
  }, [searchTerm, documents]);

  const fetchData = async () => {
    try {
      const response = await client.entities.archives.queryAll({
        query: {},
        sort: '-date_archivage',
        limit: 100,
      });

      const documentsList = response.data.items || [];
      setDocuments(documentsList);
      setFilteredDocuments(documentsList);
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (doc: Archive) => {
    try {
      if (!doc.object_key) {
        toast({
          title: 'Erreur',
          description: 'Aucun fichier disponible pour ce document',
          variant: 'destructive',
        });
        return;
      }

      const response = await client.apiCall.invoke({
        url: '/api/v1/storage/download-url',
        method: 'POST',
        data: {
          bucket_name: 'archives',
          object_key: doc.object_key,
        },
      });

      if (response.data.download_url) {
        window.open(response.data.download_url, '_blank');
      }
    } catch (error: unknown) {
      const detail =
        (error as { data?: { detail?: string }; response?: { data?: { detail?: string } }; message?: string })?.data
          ?.detail ||
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        (error as { message?: string }).message;
      toast({
        title: 'Erreur',
        description: detail || 'Échec du téléchargement',
        variant: 'destructive',
      });
    }
  };

  const getTypeColor = (type: string) => {
    switch (type.toLowerCase()) {
      case 'manuel':
        return 'bg-blue-100 text-blue-800';
      case 'schema':
        return 'bg-purple-100 text-purple-800';
      case 'procedure':
        return 'bg-green-100 text-green-800';
      case 'certification':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
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
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Documents Techniques</h2>
        <p className="mt-1 text-sm text-gray-500">Accédez aux manuels, schémas et procédures</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Rechercher par nom ou type de document..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="pl-10"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredDocuments.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="text-center py-12">
              <p className="text-gray-500">Aucun document trouvé</p>
            </CardContent>
          </Card>
        ) : (
          filteredDocuments.map((doc) => (
            <Card key={doc.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg flex items-center gap-2">
                      <FileText className="h-5 w-5 text-blue-600" />
                      {doc.nom}
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">{doc.identifiant_archive}</p>
                  </div>
                  <Badge className={getTypeColor(doc.type)}>{doc.type}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="text-sm text-gray-600">
                    <p>Date: {new Date(doc.date_archivage).toLocaleDateString()}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      className="flex-1"
                      onClick={() => handleDownload(doc)}
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      Prévisualiser
                    </Button>
                    <Button
                      size="sm"
                      className="flex-1"
                      onClick={() => handleDownload(doc)}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      Télécharger
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}