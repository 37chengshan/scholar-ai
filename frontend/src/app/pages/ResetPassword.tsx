import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import { motion } from 'motion/react';
import { ArrowLeft, Lock, CheckCircle } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { useLanguage } from '../contexts/LanguageContext';
import * as authApi from '@/services/authApi';
import { toast } from 'sonner';

export function ResetPassword() {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  
  const token = searchParams.get('token');
  
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  
  const t = {
    backToLogin: isZh ? "返回登录" : "Back to Login",
    title: isZh ? "重置密码" : "Reset Password",
    description: isZh ? "输入新密码" : "Enter your new password",
    newPassword: isZh ? "新密码" : "New Password",
    passwordPlaceholder: isZh ? "至少8个字符" : "At least 8 characters",
    confirmPassword: isZh ? "确认密码" : "Confirm Password",
    confirmPasswordPlaceholder: isZh ? "再次输入密码" : "Enter password again",
    resetButton: isZh ? "重置密码" : "Reset Password",
    resetting: isZh ? "重置中..." : "Resetting...",
    successTitle: isZh ? "密码重置成功" : "Password Reset Successful",
    successDesc: isZh ? "您现在可以使用新密码登录" : "You can now log in with your new password",
    goToLogin: isZh ? "前往登录" : "Go to Login",
    invalidToken: isZh ? "无效的重置链接" : "Invalid reset link",
    passwordMismatch: isZh ? "两次密码输入不一致" : "Passwords do not match",
    passwordTooShort: isZh ? "密码至少需要8个字符" : "Password must be at least 8 characters",
  };
  
  useEffect(() => {
    if (!token) {
      toast.error(t.invalidToken);
      navigate('/login');
    }
  }, [token, navigate, t.invalidToken]);
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password.length < 8) {
      toast.error(t.passwordTooShort);
      return;
    }
    
    if (password !== confirmPassword) {
      toast.error(t.passwordMismatch);
      return;
    }
    
    try {
      setLoading(true);
      await authApi.resetPassword(token!, password);
      setSuccess(true);
      toast.success(isZh ? "密码重置成功" : "Password reset successful");
    } catch (error: any) {
      toast.error(error.response?.data?.error?.detail || (isZh ? "重置失败" : "Failed to reset password"));
    } finally {
      setLoading(false);
    }
  };
  
  if (success) {
    return (
      <div className="min-h-screen bg-[#fdfaf6] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="w-full max-w-md bg-white border border-[#f4ece1]">
            <CardHeader className="text-center">
              <CheckCircle className="w-16 h-16 text-[#d35400] mx-auto mb-4" />
              <CardTitle className="text-xl font-semibold text-[#d35400]">
                {t.successTitle}
              </CardTitle>
              <CardDescription className="text-base">
                {t.successDesc}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                onClick={() => navigate('/login')}
                className="w-full bg-[#d35400] hover:bg-[#e67e22] text-white"
              >
                {t.goToLogin}
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen bg-[#fdfaf6] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        <Button
          onClick={() => navigate('/login')}
          variant="ghost"
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t.backToLogin}
        </Button>
        
        <Card className="bg-white border border-[#f4ece1]">
          <CardHeader>
            <CardTitle className="text-2xl font-semibold">
              {t.title}
            </CardTitle>
            <CardDescription className="text-base">
              {t.description}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-semibold">
                  {t.newPassword}
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder={t.passwordPlaceholder}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10"
                    disabled={loading}
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="confirmPassword" className="text-sm font-semibold">
                  {t.confirmPassword}
                </Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="confirmPassword"
                    type="password"
                    placeholder={t.confirmPasswordPlaceholder}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="pl-10"
                    disabled={loading}
                  />
                </div>
              </div>
              
              <Button
                type="submit"
                className="w-full bg-[#d35400] hover:bg-[#e67e22] text-white"
                disabled={loading}
              >
                {loading ? t.resetting : t.resetButton}
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}