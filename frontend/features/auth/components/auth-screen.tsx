"use client";

import { useMutation } from "@tanstack/react-query";
import { Lock, ArrowRight, ArrowLeft, CheckCircle2, Phone, User, KeyRound, MessageSquareMore, Sparkles } from "lucide-react";
import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { loginUser, registerUser, verifyOtp } from "@/services/auth";
import { useSessionStore } from "@/store/use-session-store";

type RegisterData = { phone: string; display_name: string; username: string; password: string };

export function AuthScreen() {
  const [mode, setMode] = useState<"welcome" | "login" | "register">("welcome");
  const [registerStep, setRegisterStep] = useState<"phone" | "display_name" | "username" | "password" | "otp">("phone");
  const [registerData, setRegisterData] = useState<RegisterData>({ phone: "", display_name: "", username: "", password: "" });
  const [loginId, setLoginId] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [otp, setOtp] = useState("");
  const [mockOtp, setMockOtp] = useState<string | null>(null);
  const setSession = useSessionStore((state) => state.setSession);

  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (payload) => setSession(payload),
  });

  const registerMutation = useMutation({
    mutationFn: registerUser,
    onSuccess: (payload) => {
      setMockOtp(payload.otp_mock);
      setOtp(payload.otp_mock);
      setRegisterStep("otp");
    },
  });

  const verifyMutation = useMutation({
    mutationFn: verifyOtp,
    onSuccess: (payload) => setSession(payload),
  });

  const handleRegisterNext = () => {
    if (registerStep === "phone" && registerData.phone) setRegisterStep("display_name");
    else if (registerStep === "display_name" && registerData.display_name) setRegisterStep("username");
    else if (registerStep === "username" && registerData.username) setRegisterStep("password");
    else if (registerStep === "password" && registerData.password) {
      registerMutation.mutate(registerData);
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
          <p className="text-sm text-neutral-400">Enter your phone number to get started.</p>
          <div className="relative">
            <Phone className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" placeholder="+1234567890" value={registerData.phone} onChange={(e) => setRegisterData({ ...registerData, phone: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.phone}>Next <ArrowRight className="ml-2 h-4 w-4" /></Button>
        </motion.div>
      );
    }
    if (registerStep === "display_name") {
      return (
        <motion.div key="display_name" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">How should people see you?</p>
          <div className="relative">
            <User className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" placeholder="Display Name" value={registerData.display_name} onChange={(e) => setRegisterData({ ...registerData, display_name: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.display_name}>Next <ArrowRight className="ml-2 h-4 w-4" /></Button>
        </motion.div>
      );
    }
    if (registerStep === "username") {
      return (
        <motion.div key="username" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Choose a unique username.</p>
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500 font-medium">@</span>
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-8 text-lg" placeholder="username" value={registerData.username} onChange={(e) => setRegisterData({ ...registerData, username: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.username}>Next <ArrowRight className="ml-2 h-4 w-4" /></Button>
        </motion.div>
      );
    }
    if (registerStep === "password") {
      return (
        <motion.div key="password" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          <p className="text-sm text-neutral-400">Secure your account with a password.</p>
          <div className="relative">
            <KeyRound className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-neutral-500" />
            <Input className="bg-neutral-900 border-neutral-800 h-12 pl-10 text-lg" type="password" placeholder="Password" value={registerData.password} onChange={(e) => setRegisterData({ ...registerData, password: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && handleRegisterNext()} />
          </div>
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={handleRegisterNext} disabled={!registerData.password || registerMutation.isPending}>
            {registerMutation.isPending ? "Creating account..." : "Complete Registration"}
          </Button>
          {registerMutation.error ? <p className="text-sm text-red-400 text-center">{registerMutation.error.message}</p> : null}
        </motion.div>
      );
    }
    if (registerStep === "otp") {
      return (
        <motion.div key="otp" custom={1} variants={slideVariants} initial="enter" animate="center" exit="exit" transition={{ duration: 0.3 }} className="space-y-4">
          {mockOtp && (
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-3 text-sm text-blue-200">
              <div className="mb-1 flex items-center gap-2 font-medium text-blue-100">
                <MessageSquareMore className="h-4 w-4" /> Mock OTP ready
              </div>
              <p>Code: <span className="font-bold text-white tracking-widest">{mockOtp}</span></p>
            </div>
          )}
          <p className="text-sm text-neutral-400">Enter the 6-digit code sent to {registerData.phone}</p>
          <Input className="bg-neutral-900 border-neutral-800 h-14 text-center tracking-[0.5em] text-2xl font-medium" placeholder="------" maxLength={6} value={otp} onChange={(e) => setOtp(e.target.value)} autoFocus onKeyDown={(e) => e.key === "Enter" && otp.length === 6 && verifyMutation.mutate({ phone: registerData.phone, otp })} />
          <Button className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium text-base mt-4" onClick={() => verifyMutation.mutate({ phone: registerData.phone, otp })} disabled={otp.length !== 6 || verifyMutation.isPending}>
            {verifyMutation.isPending ? "Verifying..." : "Verify Code"}
          </Button>
          {verifyMutation.error ? <p className="text-sm text-red-400 text-center">{verifyMutation.error.message}</p> : null}
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
            if (mode === "register" && registerStep !== "phone" && registerStep !== "otp") {
              const steps: Array<"phone" | "display_name" | "username" | "password" | "otp"> = ["phone", "display_name", "username", "password", "otp"];
              setRegisterStep(steps[steps.indexOf(registerStep) - 1]);
            } else {
              setMode("welcome");
              setRegisterStep("phone");
              setRegisterData({ phone: "", display_name: "", username: "", password: "" });
              setOtp("");
              setMockOtp(null);
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
