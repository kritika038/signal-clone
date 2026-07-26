"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Lock, MessageSquareMore, ShieldCheck, Sparkles } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { loginUser, registerUser, verifyOtp } from "@/services/auth";
import { useSessionStore } from "@/store/use-session-store";

const loginSchema = z.object({
  login_id: z.string().min(3),
  password: z.string().min(8),
});

const registerSchema = z.object({
  phone: z.string().min(10),
  username: z.string().min(3),
  display_name: z.string().min(2),
  password: z.string().min(8),
});

const otpSchema = z.object({
  otp: z.string().length(6),
});

export function AuthScreen() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [pendingPhone, setPendingPhone] = useState("");
  const [mockOtp, setMockOtp] = useState<string | null>(null);
  const setSession = useSessionStore((state) => state.setSession);

  const loginForm = useForm<z.infer<typeof loginSchema>>({
    resolver: zodResolver(loginSchema),
    defaultValues: { login_id: "", password: "" },
  });

  const registerForm = useForm<z.infer<typeof registerSchema>>({
    resolver: zodResolver(registerSchema),
    defaultValues: { phone: "", username: "", display_name: "", password: "" },
  });

  const otpForm = useForm<z.infer<typeof otpSchema>>({
    resolver: zodResolver(otpSchema),
    defaultValues: { otp: "" },
  });

  const loginMutation = useMutation({
    mutationFn: loginUser,
    onSuccess: (payload) => setSession(payload),
  });

  const registerMutation = useMutation({
    mutationFn: registerUser,
    onSuccess: (payload, variables) => {
      setPendingPhone(variables.phone);
      setMockOtp(payload.otp_mock);
      otpForm.setValue("otp", payload.otp_mock);
    },
  });

  const verifyMutation = useMutation({
    mutationFn: verifyOtp,
    onSuccess: (payload) => setSession(payload),
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-neutral-950 text-neutral-100">
      <div className="w-full max-w-[400px] rounded-2xl border border-neutral-800 bg-neutral-900 p-8 shadow-2xl">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              {mockOtp ? "Verify Number" : mode === "login" ? "Sign In" : "Register"}
            </h2>
            <p className="text-sm text-neutral-400 mt-1">
              {mockOtp ? "Enter the verification code" : "Welcome to Signal Clone"}
            </p>
          </div>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-blue-500/10">
            {mockOtp ? <Sparkles className="h-6 w-6 text-blue-500" /> : <Lock className="h-6 w-6 text-blue-500" />}
          </div>
        </div>

        {!mockOtp ? (
          <>
            <div className="mb-8 grid grid-cols-2 gap-1 rounded-lg bg-neutral-950 p-1">
              <button
                className={`rounded-md px-4 py-2 text-sm font-medium transition ${mode === "login" ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-400 hover:text-white"}`}
                onClick={() => setMode("login")}
                type="button"
              >
                Login
              </button>
              <button
                className={`rounded-md px-4 py-2 text-sm font-medium transition ${mode === "register" ? "bg-neutral-800 text-white shadow-sm" : "text-neutral-400 hover:text-white"}`}
                onClick={() => setMode("register")}
                type="button"
              >
                Register
              </button>
            </div>

            {mode === "login" ? (
              <form className="space-y-4" onSubmit={loginForm.handleSubmit((values) => loginMutation.mutate(values))}>
                <Input className="bg-neutral-950 border-neutral-800 h-11" placeholder="Phone or username" {...loginForm.register("login_id")} />
                <Input className="bg-neutral-950 border-neutral-800 h-11" type="password" placeholder="Password" {...loginForm.register("password")} />
                <Button className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium" type="submit" disabled={loginMutation.isPending}>
                  {loginMutation.isPending ? "Signing in..." : "Login"}
                </Button>
                {loginMutation.error ? (
                  <p className="text-sm text-red-400">{loginMutation.error.message}</p>
                ) : null}
              </form>
            ) : (
              <form className="space-y-4" onSubmit={registerForm.handleSubmit((values) => registerMutation.mutate(values))}>
                <Input className="bg-neutral-950 border-neutral-800 h-11" placeholder="Display name" {...registerForm.register("display_name")} />
                <Input className="bg-neutral-950 border-neutral-800 h-11" placeholder="Username" {...registerForm.register("username")} />
                <Input className="bg-neutral-950 border-neutral-800 h-11" placeholder="Phone number" {...registerForm.register("phone")} />
                <Input className="bg-neutral-950 border-neutral-800 h-11" type="password" placeholder="Password" {...registerForm.register("password")} />
                <Button className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium" type="submit" disabled={registerMutation.isPending}>
                  {registerMutation.isPending ? "Sending OTP..." : "Register"}
                </Button>
                {registerMutation.error ? (
                  <p className="text-sm text-red-400">{registerMutation.error.message}</p>
                ) : null}
              </form>
            )}
          </>
        ) : (
          <form
            className="space-y-4"
            onSubmit={otpForm.handleSubmit((values) =>
              verifyMutation.mutate({
                phone: pendingPhone,
                otp: values.otp,
              })
            )}
          >
            <div className="rounded-lg border border-blue-500/20 bg-blue-500/10 p-4 text-sm text-blue-200">
              <div className="mb-2 flex items-center gap-2 font-medium text-blue-100">
                <MessageSquareMore className="h-4 w-4" />
                Mock OTP ready
              </div>
              <p>Use <span className="font-semibold text-white">{mockOtp}</span> for development verification.</p>
            </div>
            <Input className="bg-neutral-950 border-neutral-800 h-11 text-center tracking-widest text-lg" placeholder="123456" {...otpForm.register("otp")} />
            <Button className="w-full h-11 bg-blue-600 hover:bg-blue-700 text-white font-medium" type="submit" disabled={verifyMutation.isPending}>
              {verifyMutation.isPending ? "Verifying..." : "Verify OTP"}
            </Button>
            <Button
              className="w-full h-11 text-neutral-400 hover:text-white"
              type="button"
              variant="ghost"
              onClick={() => {
                setMockOtp(null);
                setPendingPhone("");
                otpForm.reset();
              }}
            >
              Back
            </Button>
            {verifyMutation.error ? (
              <p className="text-sm text-red-400">{verifyMutation.error.message}</p>
            ) : null}
          </form>
        )}
      </div>
    </div>
  );
}
