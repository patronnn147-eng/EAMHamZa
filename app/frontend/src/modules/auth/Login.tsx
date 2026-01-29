import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/hooks/use-toast';
import { Wrench, AlertCircle } from 'lucide-react';

interface LoginFormData {
  email: string;
  mot_de_passe: string;
}

interface RegisterFormData {
  email: string;
  nom: string;
  mot_de_passe: string;
  confirm_password: string;
  role: string;
}

export default function Login() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [loginData, setLoginData] = useState<LoginFormData>({
    email: '',
    mot_de_passe: '',
  });
  const [registerData, setRegisterData] = useState<RegisterFormData>({
    email: '',
    nom: '',
    mot_de_passe: '',
    confirm_password: '',
    role: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validatePassword = (password: string): string | null => {
    if (password.length < 8) {
      return 'Le mot de passe doit contenir au moins 8 caractères';
    }
    if (!/[A-Z]/.test(password)) {
      return 'Le mot de passe doit contenir au moins une lettre majuscule';
    }
    if (!/[a-z]/.test(password)) {
      return 'Le mot de passe doit contenir au moins une lettre minuscule';
    }
    if (!/[0-9]/.test(password)) {
      return 'Le mot de passe doit contenir au moins un chiffre';
    }
    return null;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    // Validation
    if (!loginData.email) {
      newErrors.email = 'Email requis';
    } else if (!validateEmail(loginData.email)) {
      newErrors.email = 'Format email invalide';
    }

    if (!loginData.mot_de_passe) {
      newErrors.mot_de_passe = 'Mot de passe requis';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    setLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(loginData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Échec de la connexion');
      }

      // Store token in localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      toast({
        title: 'Connexion réussie',
        description: `Bienvenue ${data.user.nom}!`,
      });

      // Redirect based on role
      if (data.user.role === 'TECHNICIEN') {
        navigate('/technician/dashboard');
      } else {
        navigate('/admin/dashboard');
      }
    } catch (error: unknown) {
      const message = (error as Error).message || 'Erreur de connexion';
      toast({
        title: 'Erreur',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    // Validation
    if (!registerData.email) {
      newErrors.email = 'Email requis';
    } else if (!validateEmail(registerData.email)) {
      newErrors.email = 'Format email invalide';
    }

    if (!registerData.nom || registerData.nom.length < 2) {
      newErrors.nom = 'Nom requis (minimum 2 caractères)';
    }

    const passwordError = validatePassword(registerData.mot_de_passe);
    if (passwordError) {
      newErrors.mot_de_passe = passwordError;
    }

    if (registerData.mot_de_passe !== registerData.confirm_password) {
      newErrors.confirm_password = 'Les mots de passe ne correspondent pas';
    }

    if (!registerData.role) {
      newErrors.role = 'Rôle requis';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    setLoading(true);

    try {
      const { confirm_password, ...submitData } = registerData;
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(submitData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Échec de l\'inscription');
      }

      // Store token in localStorage
      localStorage.setItem('access_token', data.access_token);
      localStorage.setItem('user', JSON.stringify(data.user));

      toast({
        title: 'Inscription réussie',
        description: `Bienvenue ${data.user.nom}!`,
      });

      // Redirect based on role
      if (data.user.role === 'TECHNICIEN') {
        navigate('/technician/dashboard');
      } else {
        navigate('/admin/dashboard');
      }
    } catch (error: unknown) {
      const message = (error as Error).message || 'Erreur d\'inscription';
      toast({
        title: 'Erreur',
        description: message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
            <div className="p-3 bg-blue-600 rounded-full">
              <Wrench className="h-8 w-8 text-white" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold">Gestion des Actifs</CardTitle>
          <CardDescription>Système de maintenance industrielle</CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="login" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="login">Connexion</TabsTrigger>
              <TabsTrigger value="register">Inscription</TabsTrigger>
            </TabsList>

            <TabsContent value="login">
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="login-email">Email</Label>
                  <Input
                    id="login-email"
                    type="email"
                    placeholder="votre.email@exemple.com"
                    value={loginData.email}
                    onChange={(e) => setLoginData({ ...loginData, email: e.target.value })}
                    className={errors.email ? 'border-red-500' : ''}
                  />
                  {errors.email && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.email}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="login-password">Mot de passe</Label>
                  <Input
                    id="login-password"
                    type="password"
                    placeholder="••••••••"
                    value={loginData.mot_de_passe}
                    onChange={(e) => setLoginData({ ...loginData, mot_de_passe: e.target.value })}
                    className={errors.mot_de_passe ? 'border-red-500' : ''}
                  />
                  {errors.mot_de_passe && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.mot_de_passe}
                    </p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Connexion...' : 'Se connecter'}
                </Button>
              </form>
            </TabsContent>

            <TabsContent value="register">
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="register-email">Email</Label>
                  <Input
                    id="register-email"
                    type="email"
                    placeholder="votre.email@exemple.com"
                    value={registerData.email}
                    onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })}
                    className={errors.email ? 'border-red-500' : ''}
                  />
                  {errors.email && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.email}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-name">Nom complet</Label>
                  <Input
                    id="register-name"
                    type="text"
                    placeholder="Jean Dupont"
                    value={registerData.nom}
                    onChange={(e) => setRegisterData({ ...registerData, nom: e.target.value })}
                    className={errors.nom ? 'border-red-500' : ''}
                  />
                  {errors.nom && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.nom}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-role">Rôle</Label>
                  <Select value={registerData.role} onValueChange={(value) => setRegisterData({ ...registerData, role: value })}>
                    <SelectTrigger className={errors.role ? 'border-red-500' : ''}>
                      <SelectValue placeholder="Sélectionner un rôle" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="TECHNICIEN">Technicien</SelectItem>
                      <SelectItem value="CHETOP">Chef des Opérations</SelectItem>
                      <SelectItem value="CHEFTECH">Chef Technique</SelectItem>
                      <SelectItem value="ADMIN">Administrateur</SelectItem>
                    </SelectContent>
                  </Select>
                  {errors.role && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.role}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-password">Mot de passe</Label>
                  <Input
                    id="register-password"
                    type="password"
                    placeholder="••••••••"
                    value={registerData.mot_de_passe}
                    onChange={(e) => setRegisterData({ ...registerData, mot_de_passe: e.target.value })}
                    className={errors.mot_de_passe ? 'border-red-500' : ''}
                  />
                  {errors.mot_de_passe && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.mot_de_passe}
                    </p>
                  )}
                  <p className="text-xs text-gray-500">
                    Min. 8 caractères, 1 majuscule, 1 minuscule, 1 chiffre
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="register-confirm">Confirmer le mot de passe</Label>
                  <Input
                    id="register-confirm"
                    type="password"
                    placeholder="••••••••"
                    value={registerData.confirm_password}
                    onChange={(e) => setRegisterData({ ...registerData, confirm_password: e.target.value })}
                    className={errors.confirm_password ? 'border-red-500' : ''}
                  />
                  {errors.confirm_password && (
                    <p className="text-sm text-red-500 flex items-center gap-1">
                      <AlertCircle className="h-4 w-4" />
                      {errors.confirm_password}
                    </p>
                  )}
                </div>

                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Inscription...' : 'S\'inscrire'}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}