import { useState } from 'react';
import { useNavigate } from 'react-router';
import { motion } from 'motion/react';
import { ArrowLeft, Mail } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { useLanguage } from '../contexts/LanguageContext';
import * as authApi from '@/services/authApi';
import { toast } from 'sonner';

export function ForgotPassword() {
  const { language } = useLanguage();
  const isZh = language === "zh";
  const navigate = useNavigate();
  
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  
  const t = {
    backToLogin: isZh ? "返回登录" : "Back to Login",
    title: isZh ? "忘记密码" : "Forgot Password",
    description: isZh ? "输入您的邮箱地址，我们将发送重置链接" : "Enter your email and we'll send you a reset link",
    email: isZh ? "邮箱地址" : "Email Address",
    emailPlaceholder: isZh ? "name@example.com" : "name@example.com",
    sendLink: isZh ? "发送重置链接" : "Send Reset Link",
    sending: isZh ? "发送中..." : "Sending...",
    successTitle: isZh ? "重置链接已发送" : "Reset Link Sent",
    successDesc: isZh ? "请检查您的邮箱，点击链接重置密码" : "Check your email and click the link to reset your password",
  };
  
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!email.trim()) {
      toast.error(isZh ? "请输入邮箱地址" : "Please enter your email");
      return;
    }
    
    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      toast.error(isZh ? "邮箱格式不正确" : "Invalid email format");
      return;
    }
    
    try {
      setLoading(true);
      await authApi.forgotPassword(email);
      setSubmitted(true);
      toast.success(isZh ? "重置链接已发送" : "Reset link sent");
    } catch (error: any) {
      toast.error(error.response?.data?.error?.detail || (isZh ? "发送失败" : "Failed to send reset link"));
    } finally {
      setLoading(false);
    }
  };
  
  if (submitted) {
    return (
      <div className="min-h-screen bg-[#fdfaf6] flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <Card className="w-full max-w-md bg-white border border-[#f4ece1]">
            <CardHeader>
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
                variant="ghost"
                className="w-full"
              >
                {t.backToLogin}
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
                <Label htmlFor="email" className="text-sm font-semibold">
                  {t.email}
                </Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder={t.emailPlaceholder}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
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
                {loading ? t.sending : t.sendLink}
              </Button>
            </form>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}