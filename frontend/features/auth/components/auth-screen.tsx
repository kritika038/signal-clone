"use client";

import { useMutation } from "@tanstack/react-query";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, Phone, User, KeyRound, MessageSquareMore, Sparkles } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Mail } from "lucide-react";
import { loginUser, registerUser, verifyOtp, sendOtp } from "@/services/auth";
import { useSessionStore } from "@/store/use-session-store";

type RegisterData = { phone: string; email: string; display_name: string; username: string; password: string };
type RegisterStep = "phone" | "otp" | "register" | "profile";
const STEPS: RegisterStep[] = ["phone", "otp", "register", "profile"];

export function AuthScreen() {
  const [mode, setMode] = useState<"welcome" | "login" | "register">("welcome");
  const [registerStep, setRegisterStep] = useState<RegisterStep>("phone");
  const [registerData, setRegisterData] = useState<RegisterData>({ phone: "", email: "", display_name: "", username: "", password: "" });
  const [loginId, setLoginId] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [otpError, setOtpError] = useState("");
  const [registrationToken, setRegistrationToken] = useState("");
  const setSession = useSessionStore((state) => state.setSession);

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
      setRegisterStep("register");
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
      sendOtpMutation.mutate({ phone: registerData.phone, email: registerData.email });
    } else if (registerStep === "otp" && otp.length === 6) {
      verifyOtpMutation.mutate({ phone: registerData.phone, email: registerData.email, otp });
    } else if (registerStep === "register" && registerData.username && registerData.password) {
      setRegisterStep("profile");
    } else if (registerStep === "profile" && registerData.display_name) {
      registerMutation.mutate({ ...registerData, registration_token: registrationToken });
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
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" placeholder="+1234567890" value={registerData.phone} onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && registerData.email && handleRegisterNext()} />
          </div>
          <div className="relative mt-2">
            <Mail className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" type="email" placeholder="you@example.com" value={registerData.email} onChange={(e) => setRegisterData({ ...registerData, email: e.target.value })} onKeyDown={(e) => e.key === "Enter" && registerData.phone && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.phone || !registerData.email || sendOtpMutation.isPending}>
            {sendOtpMutation.isPending ? "Sending code..." : "Next"} <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          {sendOtpMutation.error ? <p className="text-sm text-red-400 text-center">{sendOtpMutation.error.message}</p> : null}
        </motion.div>
      );
    }
    if (registerStep === "otp") {
      return (
        <motion.div key="otp" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Enter the 6-digit code sent to {registerData.email}</p>
          <Input className="bg-neutral-900 border-neutral-800 h-14 text-center tracking-[0.5em] text-2xl font-medium" placeholder="------" maxLength={6} value={otp} onChange={(e) => { setOtp(e.target.value); setOtpError(""); }} autoFocus onKeyDown={(e) => e.key === "Enter" && otp.length === 6 && handleRegisterNext()} />
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={otp.length !== 6 || verifyOtpMutation.isPending}>
            {verifyOtpMutation.isPending ? "Verifying..." : "Verify Code"}
          </Button>
          <Button variant="ghost" className="w-full text-neutral-400 hover:text-white" onClick={() => sendOtpMutation.mutate({ phone: registerData.phone, email: registerData.email })} disabled={sendOtpMutation.isPending}>
            Resend Code
          </Button>
          {otpError && <p className="text-sm text-red-400 text-center">{otpError}</p>}
          {sendOtpMutation.isSuccess && !verifyOtpMutation.isPending && <p className="text-sm text-green-400 text-center">Code sent successfully!</p>}
        </motion.div>
      );
    }
    if (registerStep === "register") {
      return (
        <motion.div key="register" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Choose a unique username and password.</p>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 font-medium">@</span>
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-8 text-lg" placeholder="username" value={registerData.username} onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })} autoFocus />
          </div>
          <div className="relative">
            <KeyRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" type="password" placeholder="Password" value={registerData.password} onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })} onKeyDown={(e) => e.key === "Enter" && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.username || !registerData.password}>Next <ArrowRight className="ml-2 h-4 w-4" /></Button>
        </motion.div>
      );
    }
    if (registerStep === "profile") {
      return (
        <motion.div key="profile" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">How should people see you?</p>
          <div className="flex justify-center mb-6">
            <div className="relative group cursor-pointer">
              <div className="h-24 w-24 rounded-full bg-neutral-800 flex items-center justify-center border-2 border-dashed border-neutral-700 group-hover:border-blue-500 transition-colors">
                <User className="h-10 w-10 text-neutral-500 group-hover:text-blue-400 transition-colors" />
              </div>
              <div className="absolute inset-0 bg-black/40 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <span className="text-xs font-medium text-white">Add Photo</span>
              </div>
            </div>
          </div>
          <div className="relative">
            <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" placeholder="Display Name" value={registerData.display_name} onChange={(e) => setRegisterData({ ...registerData, display_name: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.display_name || registerMutation.isPending}>
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
              setRegisterData({ phone: "", email: "", display_name: "", username: "", password: "" });
              setOtp("");
              setOtpError("");

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
              <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base rounded-xl" onClick={() => setMode("register")}>
                Create an account
              </Button>
              <Button className="w-full h-12 bg-neutral-800 hover:bg-neutral-700 text-white font-medium text-base rounded-xl" onClick={() => setMode("login")}>
                Sign in
              </Button>
            </motion.div>
          )}

          {mode === "login" && (
            <motion.div key="login" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
              <Input className="bg-neutral-900 border-neutral-800 h-12" placeholder="Phone or username" value={loginId} onChange={(e) => setLoginId(e.target.value)} autoFocus />
              <Input className="bg-neutral-900 border-neutral-800 h-12" type="password" placeholder="Password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} onKeyDown={(e) => e.key === "Enter" && loginMutation.mutate({ login_id: loginId, password: loginPassword })} />
              <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-2" onClick={() => loginMutation.mutate({ login_id: loginId, password: loginPassword })} disabled={!loginId || !loginPassword || loginMutation.isPending}>
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
