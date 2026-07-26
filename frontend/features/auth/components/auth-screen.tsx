"use client";

import { useMutation } from "@tanstack/react-query";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, Phone, User, Sparkles, Mail, Camera, Loader2, XCircle } from "lucide-react";
import { useState, useEffect, useRef, KeyboardEvent, ClipboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { sendOtp, verifyOtp, registerUser, sendLoginOtp, verifyLoginOtp, checkUsername } from "@/services/auth";
import { useSessionStore } from "@/store/use-session-store";

type RegisterData = { phone: string; display_name: string; username: string; avatar_url: string };
type RegisterStep = "phone" | "otp" | "profile";
type LoginStep = "identifier" | "otp";
const REGISTER_STEPS: RegisterStep[] = ["phone", "otp", "profile"];
const LOGIN_STEPS: LoginStep[] = ["identifier", "otp"];

const BUILT_IN_AVATARS = [
  "bg-red-500", "bg-orange-500", "bg-amber-500", "bg-green-500", 
  "bg-emerald-500", "bg-teal-500", "bg-cyan-500", "bg-blue-500", 
  "bg-indigo-500", "bg-violet-500", "bg-purple-500", "bg-fuchsia-500"
];

function OTPInputBoxes({ value, onChange, onComplete, error }: { value: string, onChange: (val: string) => void, onComplete: () => void, error?: string }) {
  const inputsRef = useRef<(HTMLInputElement | null)[]>([]);
  
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>, index: number) => {
    if (e.key === "Backspace") {
      if (value[index]) {
        const newValue = value.slice(0, index) + value.slice(index + 1);
        onChange(newValue);
      } else if (index > 0) {
        inputsRef.current[index - 1]?.focus();
      }
    } else if (e.key === "ArrowLeft" && index > 0) {
      inputsRef.current[index - 1]?.focus();
    } else if (e.key === "ArrowRight" && index < 5) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>, index: number) => {
    const val = e.target.value.replace(/[^0-9]/g, "");
    if (!val) return;
    const char = val[val.length - 1];
    
    let newValue = value;
    if (index >= value.length) {
      newValue = value + char;
    } else {
      newValue = value.slice(0, index) + char + value.slice(index + 1);
    }
    
    newValue = newValue.slice(0, 6);
    onChange(newValue);
    
    if (index < 5 && newValue.length > index) {
      inputsRef.current[index + 1]?.focus();
    }
    
    if (newValue.length === 6) {
      setTimeout(onComplete, 50);
    }
  };

  const handlePaste = (e: ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData("text").replace(/[^0-9]/g, "").slice(0, 6);
    if (pastedData) {
      onChange(pastedData);
      if (pastedData.length === 6) {
        inputsRef.current[5]?.focus();
        setTimeout(onComplete, 50);
      } else {
        inputsRef.current[pastedData.length]?.focus();
      }
    }
  };

  return (
    <div className="flex justify-between gap-2">
      {Array.from({ length: 6 }).map((_, i) => (
        <Input
          key={i}
          ref={(el) => { inputsRef.current[i] = el; }}
          type="text"
          inputMode="numeric"
          autoComplete="one-time-code"
          value={value[i] || ""}
          onChange={(e) => handleInput(e, i)}
          onKeyDown={(e) => handleKeyDown(e, i)}
          onPaste={handlePaste}
          onFocus={(e) => e.target.select()}
          className={`h-14 w-12 text-center text-2xl font-medium bg-neutral-900 border-neutral-800 focus-visible:ring-blue-500 ${error ? 'border-red-500/50 focus-visible:ring-red-500' : ''}`}
          maxLength={2}
          autoFocus={i === 0}
        />
      ))}
    </div>
  );
}

export function AuthScreen() {
  const [mode, setMode] = useState<"welcome" | "login" | "register">("welcome");
  
  // Register state
  const [registerStep, setRegisterStep] = useState<RegisterStep>("phone");
  const [registerData, setRegisterData] = useState<RegisterData>({ phone: "", display_name: "", username: "", avatar_url: BUILT_IN_AVATARS[0] });
  const [registrationToken, setRegistrationToken] = useState("");
  
  // Login state
  const [loginStep, setLoginStep] = useState<LoginStep>("identifier");
  const [loginId, setLoginId] = useState("");
  
  // Shared OTP state
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [resendCountdown, setResendCountdown] = useState(0);
  
  // Profile state
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

  // Login Mutations
  const sendLoginOtpMutation = useMutation({
    mutationFn: sendLoginOtp,
    onSuccess: () => {
      setLoginStep("otp");
      setOtpError("");
      setResendCountdown(30);
    },
  });

  const verifyLoginOtpMutation = useMutation({
    mutationFn: verifyLoginOtp,
    onSuccess: (payload) => setSession(payload),
    onError: (error: any) => setOtpError(error.message || "Invalid or expired OTP"),
  });

  // Register Mutations
  const sendOtpMutation = useMutation({
    mutationFn: sendOtp,
    onSuccess: () => {
      setRegisterStep("otp");
      setOtpError("");
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
    if (registerStep === "phone" && registerData.phone) {
      setResendCountdown(30);
      sendOtpMutation.mutate({ phone: registerData.phone });
    } else if (registerStep === "profile" && registerData.display_name && usernameStatus === "available") {
      registerMutation.mutate({ 
        phone: registerData.phone,
        display_name: registerData.display_name,
        username: registerData.username,
        avatar_url: registerData.avatar_url,
        registration_token: registrationToken 
      });
    }
  };

  const handleLoginNext = () => {
    if (loginStep === "identifier" && loginId) {
      sendLoginOtpMutation.mutate({ login_id: loginId });
    }
  };

  const onRegisterOtpComplete = () => {
    if (otp.length === 6) verifyOtpMutation.mutate({ phone: registerData.phone, otp });
  };
  
  const onLoginOtpComplete = () => {
    if (otp.length === 6) verifyLoginOtpMutation.mutate({ login_id: loginId, otp });
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
          <p className="text-sm text-neutral-400">Enter your phone number to receive a verification code.</p>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg focus-visible:ring-blue-500" placeholder="+1234567890" value={registerData.phone} onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && registerData.phone && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={handleRegisterNext} disabled={!registerData.phone || sendOtpMutation.isPending}>
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
          <p className="text-sm text-neutral-400">Enter the 6-digit code sent to {registerData.phone}</p>
          <OTPInputBoxes value={otp} onChange={(val) => { setOtp(val); setOtpError(""); }} onComplete={onRegisterOtpComplete} error={otpError} />
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={onRegisterOtpComplete} disabled={otp.length !== 6 || verifyOtpMutation.isPending}>
            {verifyOtpMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {verifyOtpMutation.isPending ? "Verifying..." : "Verify Code"}
          </Button>
          <Button variant="ghost" className="w-full text-neutral-400 hover:text-white mt-2 transition-colors" onClick={() => { setResendCountdown(30); sendOtpMutation.mutate({ phone: registerData.phone }); }} disabled={resendCountdown > 0 || sendOtpMutation.isPending}>
            {resendCountdown > 0 ? `Resend Code in ${resendCountdown}s` : "Resend Code"}
          </Button>
          {otpError && <p className="text-sm text-red-400 text-center">{otpError}</p>}
        </motion.div>
      );
    }
    if (registerStep === "profile") {
      const isUsernameOk = usernameStatus === "available";
      const isValid = registerData.display_name && isUsernameOk;
      
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
              <Input className="bg-neutral-900 border-neutral-800 h-12 pl-8 pr-10 text-base focus-visible:ring-blue-500" placeholder="Username" value={registerData.username} onChange={(e) => setRegisterData({ ...registerData, username: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })} onKeyDown={(e) => e.key === "Enter" && isValid && handleRegisterNext()}/>
              <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                {usernameStatus === "checking" && <Loader2 className="h-4 w-4 animate-spin text-neutral-500" />}
                {usernameStatus === "available" && <CheckCircle2 className="h-5 w-5 text-green-500" />}
                {usernameStatus === "taken" && <XCircle className="h-5 w-5 text-red-500" />}
              </div>
            </div>
          </div>

          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={handleRegisterNext} disabled={!isValid || registerMutation.isPending}>
            {registerMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {registerMutation.isPending ? "Creating account..." : "Complete Registration"}
          </Button>
          {registerMutation.error ? <p className="text-sm text-red-400 text-center">{registerMutation.error.message}</p> : null}
        </motion.div>
      );
    }
  };

  const renderLoginStep = () => {
    if (loginStep === "identifier") {
      return (
        <motion.div key="identifier" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Enter your phone number to receive a login code.</p>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg focus-visible:ring-blue-500" placeholder="+1234567890" value={loginId} onChange={(e) => setLoginId(e.target.value)} autoFocus onKeyDown={(e) => e.key === "Enter" && loginId && handleLoginNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={handleLoginNext} disabled={!loginId || sendLoginOtpMutation.isPending}>
            {sendLoginOtpMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {sendLoginOtpMutation.isPending ? "Sending code..." : "Next"} {!sendLoginOtpMutation.isPending && <ArrowRight className="ml-2 h-4 w-4" />}
          </Button>
          {sendLoginOtpMutation.error ? <p className="text-sm text-red-400 text-center">{sendLoginOtpMutation.error.message}</p> : null}
        </motion.div>
      );
    }
    if (loginStep === "otp") {
      return (
        <motion.div key="otp" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Enter the 6-digit code sent to you</p>
          <OTPInputBoxes value={otp} onChange={(val) => { setOtp(val); setOtpError(""); }} onComplete={onLoginOtpComplete} error={otpError} />
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={onLoginOtpComplete} disabled={otp.length !== 6 || verifyLoginOtpMutation.isPending}>
            {verifyLoginOtpMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {verifyLoginOtpMutation.isPending ? "Verifying..." : "Sign in"}
          </Button>
          <Button variant="ghost" className="w-full text-neutral-400 hover:text-white mt-2 transition-colors" onClick={() => { setResendCountdown(30); sendLoginOtpMutation.mutate({ login_id: loginId }); }} disabled={resendCountdown > 0 || sendLoginOtpMutation.isPending}>
            {resendCountdown > 0 ? `Resend Code in ${resendCountdown}s` : "Resend Code"}
          </Button>
          {otpError && <p className="text-sm text-red-400 text-center">{otpError}</p>}
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
              setRegisterStep(REGISTER_STEPS[REGISTER_STEPS.indexOf(registerStep) - 1]);
            } else if (mode === "login" && loginStep !== "identifier") {
              setLoginStep(LOGIN_STEPS[LOGIN_STEPS.indexOf(loginStep) - 1]);
            } else {
              setMode("welcome");
              setRegisterStep("phone");
              setLoginStep("identifier");
              setRegisterData({ phone: "", display_name: "", username: "", avatar_url: BUILT_IN_AVATARS[0] });
              setOtp("");
              setOtpError("");
              setResendCountdown(0);
              setUsernameStatus("idle");
              setLoginId("");
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

          {mode === "login" && renderLoginStep()}
          {mode === "register" && renderRegisterStep()}
        </AnimatePresence>
      </div>
    </div>
  );
}
