"use client";

import { useMutation } from "@tanstack/react-query";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, Phone, User, KeyRound, Sparkles, Mail, Image as ImageIcon, Camera, Loader2, XCircle } from "lucide-react";
import { useState, useEffect, useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { loginUser, registerUser, verifyOtp, sendOtp, checkUsername } from "@/services/auth";
import { useSessionStore } from "@/store/use-session-store";

type RegisterData = { phone: string; email: string; display_name: string; username: string; password: string; confirm_password: string; avatar_url: string };
type RegisterStep = "phone" | "otp" | "profile";
const STEPS: RegisterStep[] = ["phone", "otp", "profile"];

const BUILT_IN_AVATARS = [
  "bg-red-500", "bg-orange-500", "bg-amber-500", "bg-green-500", 
  "bg-emerald-500", "bg-teal-500", "bg-cyan-500", "bg-blue-500", 
  "bg-indigo-500", "bg-violet-500", "bg-purple-500", "bg-fuchsia-500"
];

export function AuthScreen() {
  const [mode, setMode] = useState<"welcome" | "login" | "register">("welcome");
  const [registerStep, setRegisterStep] = useState<RegisterStep>("phone");
  const [registerData, setRegisterData] = useState<RegisterData>({ phone: "", email: "", display_name: "", username: "", password: "", confirm_password: "", avatar_url: BUILT_IN_AVATARS[0] });
  const [loginId, setLoginId] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [registrationToken, setRegistrationToken] = useState("");
  const [resendCountdown, setResendCountdown] = useState(0);
  const [usernameStatus, setUsernameStatus] = useState<"idle" | "checking" | "available" | "taken">("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const setSession = useSessionStore((state) => state.setSession);

  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (resendCountdown > 0) {
      timer = setTimeout(() => setResendCountdown(resendCountdown - 1), 1000);
    }
    return () => clearTimeout(timer);
  }, [resendCountdown]);

  useEffect(() => {
    if (!registerData.username) {
      setUsernameStatus("idle");
      return;
    }
    setUsernameStatus("checking");
    const timeoutId = setTimeout(() => {
      checkUsername(registerData.username)
        .then(res => setUsernameStatus(res.available ? "available" : "taken"))
        .catch(() => setUsernameStatus("idle"));
    }, 500);
    return () => clearTimeout(timeoutId);
  }, [registerData.username]);

  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (payload) => setSession(payload),
  });

  const sendOtpMutation = useMutation({
    mutationFn: sendOtp,
    onSuccess: () => {
      setRegisterStep("otp");
    },
  });

  const verifyOtpMutation = useMutation({
    mutationFn: verifyOtp,
    onSuccess: (payload) => {
      setRegistrationToken(payload.registration_token);
      setOtpError("");
      setRegisterStep("profile");
    },
    onError: (error: any) => {
      setOtpError(error.message || "Invalid or expired OTP");
    }
  });

  const registerMutation = useMutation({
    mutationFn: registerUser,
    onSuccess: (payload) => {
      setSession(payload);
    },
  });

  const handleRegisterNext = () => {
    if (registerStep === "phone" && registerData.phone && registerData.email) {
      setResendCountdown(30);
      sendOtpMutation.mutate({ phone: registerData.phone, email: registerData.email });
    } else if (registerStep === "otp" && otp.length === 6) {
      verifyOtpMutation.mutate({ phone: registerData.phone, email: registerData.email, otp });
    } else if (registerStep === "profile" && registerData.display_name && usernameStatus === "available" && registerData.password && registerData.password === registerData.confirm_password) {
      registerMutation.mutate({ 
        phone: registerData.phone,
        email: registerData.email,
        display_name: registerData.display_name,
        username: registerData.username,
        password: registerData.password,
        avatar_url: registerData.avatar_url,
        registration_token: registrationToken 
      });
    }
  };

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setRegisterData({ ...registerData, avatar_url: reader.result as string });
      };
      reader.readAsDataURL(file);
    }
  };

  const slideVariants = {
    enter: (direction: number) => ({ x: direction > 0 ? 100 : -100, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (direction: number) => ({ x: direction < 0 ? 100 : -100, opacity: 0 }),
  };

  const renderRegisterStep = () => {
    if (registerStep === "phone") {
      return (
        <motion.div key="phone" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Enter your phone and email to receive a code.</p>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg focus-visible:ring-blue-500" placeholder="+1234567890" value={registerData.phone} onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && registerData.email && handleRegisterNext()} />
          </div>
          <div className="relative mt-2">
            <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg focus-visible:ring-blue-500" type="email" placeholder="you@example.com" value={registerData.email} onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })} onKeyDown={(e) => e.key === "Enter" && registerData.phone && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={handleRegisterNext} disabled={!registerData.phone || !registerData.email || sendOtpMutation.isPending}>
            {sendOtpMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {sendOtpMutation.isPending ? "Sending code..." : "Next"} {!sendOtpMutation.isPending && <ArrowRight className="ml-2 h-4 w-4" />}
          </Button>
          {sendOtpMutation.error ? <p className="text-sm text-red-400 text-center">{sendOtpMutation.error.message}</p> : null}
        </motion.div>
      );
    }
    if (registerStep === "otp") {
      return (
        <motion.div key="otp" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Enter the 6-digit code sent to {registerData.email}</p>
          <Input className="bg-neutral-900 border-neutral-800 h-14 text-center tracking-[0.5em] text-2xl font-medium focus-visible:ring-blue-500" placeholder="------" maxLength={6} value={otp} onChange={(e) => { setOtp(e.target.value); setOtpError(""); }} autoFocus onKeyDown={(e) => e.key === "Enter" && otp.length === 6 && handleRegisterNext()} />
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={handleRegisterNext} disabled={otp.length !== 6 || verifyOtpMutation.isPending}>
            {verifyOtpMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {verifyOtpMutation.isPending ? "Verifying..." : "Verify Code"}
          </Button>
          <Button variant="ghost" className="w-full text-neutral-400 hover:text-white mt-2 transition-colors" onClick={() => { setResendCountdown(30); sendOtpMutation.mutate({ phone: registerData.phone, email: registerData.email }); }} disabled={resendCountdown > 0 || sendOtpMutation.isPending}>
            {resendCountdown > 0 ? `Resend Code in ${resendCountdown}s` : "Resend Code"}
          </Button>
          {otpError && <p className="text-sm text-red-400 text-center">{otpError}</p>}
        </motion.div>
      );
    }
    if (registerStep === "profile") {
      const isUsernameOk = usernameStatus === "available";
      const isValid = registerData.display_name && isUsernameOk && registerData.password && registerData.password === registerData.confirm_password;
      
      const isBase64Avatar = registerData.avatar_url.startsWith('data:image');
      const isColorAvatar = registerData.avatar_url.startsWith('bg-');

      return (
        <motion.div key="profile" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4 max-h-[75vh] overflow-y-auto px-1 scrollbar-hide pb-4">
          <p className="text-sm text-neutral-400">Complete your profile to finish registration.</p>
          
          <div className="flex flex-col items-center mb-6 space-y-4">
            <input type="file" accept="image/*" className="hidden" ref={fileInputRef} onChange={handlePhotoUpload} />
            <div 
              className={`relative h-24 w-24 rounded-full flex items-center justify-center border-4 border-neutral-800 shadow-xl overflow-hidden cursor-pointer group transition-all hover:border-neutral-700 ${isColorAvatar ? registerData.avatar_url : 'bg-neutral-800'}`}
              onClick={() => fileInputRef.current?.click()}
            >
              {isBase64Avatar ? (
                <img src={registerData.avatar_url} alt="Avatar" className="h-full w-full object-cover" />
              ) : (
                <User className="h-10 w-10 text-white/50 group-hover:opacity-0 transition-opacity" />
              )}
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <Camera className="h-6 w-6 text-white" />
              </div>
            </div>
            
            <div className="grid grid-cols-6 gap-2 w-full max-w-[280px]">
              {BUILT_IN_AVATARS.map((color) => (
                <button
                  key={color}
                  onClick={() => setRegisterData({ ...registerData, avatar_url: color })}
                  className={`h-8 w-8 rounded-full ${color} transition-all ${registerData.avatar_url === color ? 'ring-2 ring-white ring-offset-2 ring-offset-neutral-900 scale-110' : 'opacity-60 hover:opacity-100 hover:scale-105'}`}
                  type="button"
                />
              ))}
            </div>
            <p className="text-xs text-neutral-500">Upload a photo or choose an avatar</p>
          </div>

          <div className="space-y-3">
            <div className="relative">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
              <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-base focus-visible:ring-blue-500" placeholder="Display Name" value={registerData.display_name} onChange={(e) => setRegisterData({ ...registerData, display_name: e.target.value })} autoFocus />
            </div>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 font-medium">@</span>
              <Input className="bg-neutral-900 border-neutral-800 h-12 pl-8 pr-10 text-base focus-visible:ring-blue-500" placeholder="Username" value={registerData.username} onChange={(e) => setRegisterData({ ...registerData, username: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })} />
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                {usernameStatus === "checking" && <Loader2 className="h-4 w-4 animate-spin text-neutral-500" />}
                {usernameStatus === "available" && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                {usernameStatus === "taken" && <XCircle className="h-5 w-5 text-red-500" />}
              </div>
            </div>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
              <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-base focus-visible:ring-blue-500" type="password" placeholder="Password" value={registerData.password} onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })} />
            </div>
            <div className="relative">
              <KeyRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
              <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-base focus-visible:ring-blue-500" type="password" placeholder="Confirm Password" value={registerData.confirm_password} onChange={(e) => setRegisterData({ ...registerData, confirm_password: e.target.value })} onKeyDown={(e) => e.key === "Enter" && isValid && handleRegisterNext()} />
            </div>
          </div>
          
          {registerData.password && registerData.confirm_password && registerData.password !== registerData.confirm_password && (
            <p className="text-xs text-red-400 text-center">Passwords do not match</p>
          )}

          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={handleRegisterNext} disabled={!isValid || registerMutation.isPending}>
            {registerMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {registerMutation.isPending ? "Creating account..." : "Complete Registration"}
          </Button>
          {registerMutation.error ? <p className="text-sm text-red-400 text-center">{registerMutation.error.message}</p> : null}
        </motion.div>
      );
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 text-neutral-100 overflow-hidden relative">
      <div className="absolute inset-0 flex items-center justify-center opacity-[0.03] pointer-events-none">
        <Sparkles className="w-96 h-96" />
      </div>
      <div className="w-full max-w-md rounded-3xl border border-neutral-800 bg-neutral-900/50 p-8 shadow-2xl backdrop-blur-xl relative z-10">
        
        {mode !== "welcome" && (
          <button className="absolute left-6 top-8 text-neutral-400 hover:text-white transition-colors" onClick={() => {
            if (mode === "register" && registerStep !== "phone") {
              setRegisterStep(STEPS[STEPS.indexOf(registerStep) - 1]);
            } else {
              setMode("welcome");
              setRegisterStep("phone");
              setRegisterData({ phone: "", email: "", display_name: "", username: "", password: "", confirm_password: "", avatar_url: BUILT_IN_AVATARS[0] });
              setOtp("");
              setOtpError("");
              setResendCountdown(0);
              setUsernameStatus("idle");
            }
          }}>
            <ArrowLeft className="h-6 w-6" />
          </button>
        )}

        <div className="mb-10 mt-2 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-600/10">
            <Lock className="h-7 w-7 text-blue-500" />
          </div>
          <h2 className="text-2xl font-semibold text-white tracking-tight">
            {mode === "welcome" ? "Signal Desktop" : mode === "login" ? "Welcome Back" : "Create Account"}
          </h2>
        </div>

        <AnimatePresence mode="wait" custom={1}>
          {mode === "welcome" && (
            <motion.div key="welcome" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
              <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base rounded-xl transition-all" onClick={() => setMode("register")}>
                Create an account
              </Button>
              <Button className="w-full h-12 bg-neutral-800 hover:bg-neutral-700 text-white font-medium text-base rounded-xl transition-all" onClick={() => setMode("login")}>
                Sign in
              </Button>
            </motion.div>
          )}

          {mode === "login" && (
            <motion.div key="login" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
              <Input className="bg-neutral-900 border-neutral-800 h-12 focus-visible:ring-blue-500" placeholder="Phone or username" value={loginId} onChange={(e) => setLoginId(e.target.value)} autoFocus />
              <Input className="bg-neutral-900 border-neutral-800 h-12 focus-visible:ring-blue-500" type="password" placeholder="Password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && loginMutation.mutate({ login_id: loginId, password: loginPassword })} />
              <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-2 transition-all" onClick={() => loginMutation.mutate({ login_id: loginId, password: loginPassword })} disabled={!loginId || !loginPassword || loginMutation.isPending}>
                {loginMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                {loginMutation.isPending ? "Signing in..." : "Sign in"}
              </Button>
              {loginMutation.error ? <p className="text-sm text-red-400 text-center mt-2">{loginMutation.error.message}</p> : null}
            </motion.div>
          )}

          {mode === "register" && renderRegisterStep()}
        </AnimatePresence>
      </div>
    </div>
  );
}
