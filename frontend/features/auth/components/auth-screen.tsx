"use client";

import { useMutation } from "@tanstack/react-query";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, Phone, User, Sparkles, Mail, Camera, Loader2, XCircle, Info } from "lucide-react";
import { useState, useEffect, useRef, KeyboardEvent, ClipboardEvent } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useRouter } from "next/navigation";

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

const isDemoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true" || process.env.APP_MODE === "demo";

const DemoNotice = () => {
  if (!isDemoMode) return null;
  return (
    <div className="mt-6 p-4 rounded-xl bg-blue-900/20 border border-blue-800/30 text-left relative overflow-hidden group">
      <div className="absolute inset-0 bg-blue-500/5 opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="relative flex items-center gap-2 text-blue-400 font-semibold mb-1.5">
        <Info className="h-4 w-4" />
        <h4 className="tracking-tight">Demo Build</h4>
      </div>
      <p className="relative text-[13px] leading-relaxed text-blue-200/80 mb-3">
        Phone verification is mocked for this assignment.
      </p>
      <div className="relative bg-blue-950/50 rounded-lg py-2.5 px-3.5 flex justify-between items-center border border-blue-900/50 shadow-inner">
        <span className="text-xs font-medium text-blue-300">Demo OTP</span>
        <span className="font-mono text-blue-400 font-bold tracking-[0.2em]">123456</span>
      </div>
    </div>
  );
};

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
  const router = useRouter();
  
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

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
    onSuccess: (payload) => {
      setSession(payload);
      router.push("/conversations");
    },
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
      router.push("/conversations");
    },
  });

  const handleRegisterNext = async () => {
    if (registerStep === "phone" && registerData.phone) {
      setResendCountdown(30);
      sendOtpMutation.mutate({ phone: registerData.phone });
    } else if (registerStep === "profile" && registerData.display_name && usernameStatus === "available") {
      let finalAvatarUrl = registerData.avatar_url;
      
      if (avatarFile) {
        setIsUploading(true);
        try {
          const formData = new FormData();
          formData.append("file", avatarFile);
          
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "https://signal-clone-backend-xja6.onrender.com";
          const response = await fetch(`${apiUrl}/api/v1/media/upload`, {
            method: "POST",
            body: formData,
          });
          
          const result = await response.json();
          if (result.success && result.data.url) {
            finalAvatarUrl = result.data.url;
          } else {
            console.error("Avatar upload failed:", result.error?.message || "Unknown error");
            finalAvatarUrl = BUILT_IN_AVATARS[0]; // Fallback to default
          }
        } catch (error) {
          console.error("Avatar upload failed:", error);
          finalAvatarUrl = BUILT_IN_AVATARS[0]; // Fallback to default
        } finally {
          setIsUploading(false);
        }
      }

      if (finalAvatarUrl.startsWith("data:")) {
        // Prevent sending Base64 strings to the backend which cause 413 Payload Too Large
        finalAvatarUrl = BUILT_IN_AVATARS[0];
      }

      registerMutation.mutate({ 
        phone: registerData.phone,
        display_name: registerData.display_name,
        username: registerData.username,
        avatar_url: finalAvatarUrl,
        registration_token: registrationToken 
      });
    }
  };

  const handleLoginNext = () => {
    if (loginStep === "identifier" && loginId) {
      setResendCountdown(30);
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
      setAvatarFile(file);
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
          <p className="text-sm text-neutral-400 text-center">Enter the 6-digit verification code.</p>
          <OTPInputBoxes value={otp} onChange={(val) => { setOtp(val); setOtpError(""); }} onComplete={onRegisterOtpComplete} error={otpError} />
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4 transition-all" onClick={onRegisterOtpComplete} disabled={otp.length !== 6 || verifyOtpMutation.isPending}>
            {verifyOtpMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
            {verifyOtpMutation.isPending ? "Verifying..." : "Verify Code"}
          </Button>
          <Button variant="ghost" className="w-full text-neutral-400 hover:text-white mt-2 transition-colors" onClick={() => { setResendCountdown(30); sendOtpMutation.mutate({ phone: registerData.phone }); }} disabled={resendCountdown > 0 || sendOtpMutation.isPending}>
            {resendCountdown > 0 ? `Resend Code in ${resendCountdown}s` : "Resend Code"}
          </Button>
          <div className="bg-blue-900/20 border border-blue-900/30 rounded-lg p-3 text-center">
            <span className="text-blue-300 font-mono text-sm">Demo OTP: 123456</span>
          </div>
          {otpError && <p className="text-sm text-red-400 text-center">{otpError}</p>}
        </motion.div>
      );
    }
    if (registerStep === "profile") {
      const isUsernameOk = usernameStatus === "available";
      const isValid = registerData.display_name.trim().length > 0 && isUsernameOk;
      
      const isBase64Avatar = registerData.avatar_url.startsWith('data:image');
      const isColorAvatar = registerData.avatar_url.startsWith('bg-');
      const initialLetter = registerData.display_name ? registerData.display_name.trim().charAt(0).toUpperCase() : "";

      return (
        <motion.div key="profile" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-5 max-h-[75vh] overflow-y-auto px-2 scrollbar-hide pb-4">
          <div className="text-center space-y-1 mb-4">
            <h3 className="text-xl font-semibold text-white tracking-tight">Profile Setup</h3>
            <p className="text-sm text-neutral-400">Complete your profile to finish registration.</p>
          </div>
          
          <div className="flex flex-col items-center mb-6 space-y-4">
            <input type="file" accept="image/*" className="hidden" ref={fileInputRef} onChange={handlePhotoUpload} aria-label="Upload profile photo file input" />
            <div 
              className={`relative h-28 w-28 rounded-full flex items-center justify-center border-4 border-neutral-800 shadow-2xl overflow-hidden cursor-pointer group transition-all duration-300 hover:border-neutral-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-4 focus-visible:ring-offset-neutral-950 ${isColorAvatar ? registerData.avatar_url : 'bg-neutral-800'}`}
              onClick={() => fileInputRef.current?.click()}
              tabIndex={0}
              role="button"
              aria-label="Upload profile photo"
              onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
            >
              {isBase64Avatar ? (
                <img src={registerData.avatar_url} alt="Avatar" className="h-full w-full object-cover" />
              ) : (
                <span className="text-5xl text-white/90 font-medium tracking-tight drop-shadow-md">
                  {initialLetter || <User className="h-12 w-12 text-white/50 group-hover:opacity-0 transition-opacity" />}
                </span>
              )}
              <div className="absolute inset-0 bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity backdrop-blur-[2px]">
                <Camera className="h-8 w-8 text-white drop-shadow-lg" />
              </div>
            </div>
            
            {isBase64Avatar && (
              <button
                type="button"
                onClick={() => {
                  setAvatarFile(null);
                  setRegisterData({ ...registerData, avatar_url: BUILT_IN_AVATARS[0] });
                }}
                className="text-sm font-medium text-red-400 hover:text-red-300 transition-colors focus-visible:outline-none focus-visible:underline"
                aria-label="Remove uploaded photo and revert to generated avatar"
              >
                Remove photo
              </button>
            )}
            
            {!isBase64Avatar && (
              <div className="grid grid-cols-6 gap-3 w-full max-w-[280px]" role="radiogroup" aria-label="Select avatar color">
                {BUILT_IN_AVATARS.map((color) => {
                  const isSelected = registerData.avatar_url === color;
                  return (
                    <button
                      key={color}
                      onClick={() => setRegisterData({ ...registerData, avatar_url: color })}
                      className={`relative h-10 w-10 rounded-full ${color} transition-all duration-300 flex items-center justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-neutral-950 ${isSelected ? 'scale-110 shadow-lg shadow-white/10 ring-2 ring-white ring-offset-2 ring-offset-neutral-950' : 'opacity-70 hover:opacity-100 hover:scale-105'}`}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      aria-label={`Select color ${color.replace('bg-', '').split('-')[0]}`}
                    >
                      <AnimatePresence>
                        {isSelected && (
                          <motion.div
                            initial={{ scale: 0, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0, opacity: 0 }}
                            transition={{ type: "spring", stiffness: 400, damping: 25 }}
                          >
                            <CheckCircle2 className="h-6 w-6 text-white/90 drop-shadow-md" />
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="space-y-4">
            <div className="relative group">
              <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500 group-focus-within:text-blue-500 transition-colors" aria-hidden="true" />
              <Input 
                className="bg-neutral-900 border-neutral-800 h-14 pl-11 text-base focus-visible:ring-blue-500 transition-all shadow-sm rounded-xl" 
                placeholder="Display Name (Required)" 
                value={registerData.display_name} 
                onChange={(e) => setRegisterData({ ...registerData, display_name: e.target.value })} 
                autoFocus 
                aria-required="true"
                aria-label="Display Name"
              />
            </div>
            <div className="relative group">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-neutral-500 font-medium group-focus-within:text-blue-500 transition-colors" aria-hidden="true">@</span>
              <Input 
                className="bg-neutral-900 border-neutral-800 h-14 pl-9 pr-12 text-base focus-visible:ring-blue-500 transition-all shadow-sm rounded-xl" 
                placeholder="Username (Required)" 
                value={registerData.username} 
                onChange={(e) => setRegisterData({ ...registerData, username: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })} 
                onKeyDown={(e) => e.key === "Enter" && isValid && handleRegisterNext()}
                aria-required="true"
                aria-label="Username"
              />
              <div className="absolute right-4 top-1/2 -translate-y-1/2 flex items-center">
                {usernameStatus === "checking" && <Loader2 className="h-5 w-5 animate-spin text-neutral-500" aria-label="Checking username availability" />}
                {usernameStatus === "available" && <CheckCircle2 className="h-5 w-5 text-green-500" aria-label="Username available" />}
                {usernameStatus === "taken" && <XCircle className="h-5 w-5 text-red-500" aria-label="Username taken" />}
              </div>
            </div>
          </div>

          <Button 
            className="w-full h-14 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg mt-6 transition-all rounded-xl shadow-lg shadow-blue-900/20 disabled:opacity-50 disabled:shadow-none" 
            onClick={handleRegisterNext} 
            disabled={!isValid || registerMutation.isPending || isUploading}
            aria-disabled={!isValid || registerMutation.isPending || isUploading}
          >
            {(registerMutation.isPending || isUploading) ? <Loader2 className="mr-3 h-5 w-5 animate-spin" /> : null}
            {(registerMutation.isPending || isUploading) ? "Completing Registration..." : "Complete Registration"}
          </Button>
          {registerMutation.error ? (
            <motion.p initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="text-sm text-red-400 text-center bg-red-950/50 p-2 rounded-lg border border-red-900/50">
              {registerMutation.error.message}
            </motion.p>
          ) : null}
        </motion.div>
      );
    }
  };

  const renderLoginStep = () => {
    if (loginStep === "identifier") {
      return (
        <motion.div key="login-identifier" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400 text-center">Enter your phone number or username to log in.</p>
          <div className="relative group">
            <User className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500 group-focus-within:text-blue-500 transition-colors" />
            <Input 
              className="bg-neutral-900 border-neutral-800 h-14 pl-11 text-base focus-visible:ring-blue-500 transition-all rounded-xl shadow-sm" 
              placeholder="Phone or Username" 
              value={loginId} 
              onChange={(e) => setLoginId(e.target.value)} 
              onKeyDown={(e) => e.key === "Enter" && loginId && handleLoginNext()}
              autoFocus 
            />
          </div>
          <Button className="w-full h-14 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg mt-4 transition-all rounded-xl shadow-lg shadow-blue-900/20 disabled:opacity-50" onClick={handleLoginNext} disabled={!loginId || sendLoginOtpMutation.isPending}>
            {sendLoginOtpMutation.isPending ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : null}
            {sendLoginOtpMutation.isPending ? "Continuing..." : "Continue"} {!sendLoginOtpMutation.isPending && <ArrowRight className="ml-2 h-4 w-4" />}
          </Button>
          {sendLoginOtpMutation.error ? <p className="text-sm text-red-400 text-center">{sendLoginOtpMutation.error.message}</p> : null}
        </motion.div>
      );
    }
    if (loginStep === "otp") {
      return (
        <motion.div key="login-otp" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400 text-center">Enter the 6-digit verification code.</p>
          <OTPInputBoxes value={otp} onChange={(val) => { setOtp(val); setOtpError(""); }} onComplete={onLoginOtpComplete} error={otpError} />
          <Button className="w-full h-14 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-lg mt-4 transition-all rounded-xl shadow-lg shadow-blue-900/20 disabled:opacity-50" onClick={onLoginOtpComplete} disabled={otp.length !== 6 || verifyLoginOtpMutation.isPending}>
            {verifyLoginOtpMutation.isPending ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : null}
            {verifyLoginOtpMutation.isPending ? "Verifying..." : "Verify Code"}
          </Button>
          <Button variant="ghost" className="w-full h-12 text-neutral-400 hover:text-white mt-2 transition-colors rounded-xl" onClick={() => { setResendCountdown(30); sendLoginOtpMutation.mutate({ login_id: loginId }); }} disabled={resendCountdown > 0 || sendLoginOtpMutation.isPending}>
            {resendCountdown > 0 ? `Resend Code in ${resendCountdown}s` : "Resend Code"}
          </Button>
          <div className="bg-blue-900/20 border border-blue-900/30 rounded-lg p-3 text-center">
            <span className="text-blue-300 font-mono text-sm">Demo OTP: 123456</span>
          </div>
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
          <button className="absolute left-4 top-4 p-2 text-neutral-400 hover:text-white transition-colors" onClick={() => {
            if (mode === "register" && registerStep !== "phone") {
              const prevIndex = REGISTER_STEPS.indexOf(registerStep) - 1;
              if (prevIndex >= 0) {
                if (REGISTER_STEPS[prevIndex] === "phone") {
                  sendOtpMutation.reset();
                  verifyOtpMutation.reset();
                  setOtpError("");
                  setOtp("");
                }
                setRegisterStep(REGISTER_STEPS[prevIndex]);
              }
            } else if (mode === "login" && loginStep !== "identifier") {
              const prevIndex = LOGIN_STEPS.indexOf(loginStep) - 1;
              if (prevIndex >= 0) {
                if (LOGIN_STEPS[prevIndex] === "identifier") {
                  sendLoginOtpMutation.reset();
                  verifyLoginOtpMutation.reset();
                  setOtpError("");
                  setOtp("");
                }
                setLoginStep(LOGIN_STEPS[prevIndex]);
              }
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
