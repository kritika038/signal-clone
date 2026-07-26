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
    <div className="relative flex min-h-screen overflow-hidden bg-[#0a121c] text-slate-100">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(95,148,255,0.2),_transparent_35%),radial-gradient(circle_at_bottom_right,_rgba(34,197,94,0.12),_transparent_30%)]" />
      <div className="relative z-10 grid min-h-screen w-full lg:grid-cols-[1.05fr_0.95fr]">
        <section className="hidden lg:flex flex-col justify-between border-r border-white/8 p-10">
          <div className="space-y-5">
            <Badge className="bg-signal-500/12 text-signal-100 border-signal-400/20">
              Signal Desktop Experience
            </Badge>
            <h1 className="max-w-lg text-5xl font-semibold tracking-tight text-white">
              Private messaging with the calm, focused feel of Signal.
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-300">
              Sign in to a desktop-first workspace with conversation search, message reactions,
              drafts, settings controls, reconnect feedback, and a polished multi-pane layout.
            </p>
          </div>
          <div className="grid gap-4">
            {[
              ["Signal-like shell", "Left rail, focused thread view, and profile/settings surfaces."],
              ["Real auth flow", "Registration, mock OTP verification, session persistence, logout."],
              ["Graceful backend gaps", "Chat UI is ready while missing APIs are explicitly identified."],
            ].map(([title, body]) => (
              <div key={title} className="rounded-[28px] border border-white/8 bg-white/5 p-5 backdrop-blur-xl">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium text-slate-100">
                  <ShieldCheck className="h-4 w-4 text-signal-300" />
                  {title}
                </div>
                <p className="text-sm leading-6 text-slate-400">{body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="relative flex items-center justify-center p-6 lg:p-10">
          <div className="w-full max-w-md rounded-[32px] border border-white/10 bg-[#0d1724]/88 p-6 shadow-2xl shadow-black/30 backdrop-blur-2xl">
            <div className="mb-6 flex items-center justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Secure Access</p>
                <h2 className="mt-1 text-3xl font-semibold text-white">
                  {mockOtp ? "Verify your number" : mode === "login" ? "Welcome back" : "Create account"}
                </h2>
              </div>
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-signal-500/12">
                {mockOtp ? <Sparkles className="h-5 w-5 text-signal-200" /> : <Lock className="h-5 w-5 text-signal-200" />}
              </div>
            </div>

            {!mockOtp ? (
              <>
                <div className="mb-6 grid grid-cols-2 gap-2 rounded-full bg-white/5 p-1">
                  <button
                    className={`rounded-full px-4 py-2 text-sm transition ${mode === "login" ? "bg-white text-slate-950" : "text-slate-300"}`}
                    onClick={() => setMode("login")}
                    type="button"
                  >
                    Login
                  </button>
                  <button
                    className={`rounded-full px-4 py-2 text-sm transition ${mode === "register" ? "bg-white text-slate-950" : "text-slate-300"}`}
                    onClick={() => setMode("register")}
                    type="button"
                  >
                    Register
                  </button>
                </div>

                {mode === "login" ? (
                  <form className="space-y-4" onSubmit={loginForm.handleSubmit((values) => loginMutation.mutate(values))}>
                    <Input placeholder="Phone or username" {...loginForm.register("login_id")} />
                    <Input type="password" placeholder="Password" {...loginForm.register("password")} />
                    <Button className="w-full" type="submit" disabled={loginMutation.isPending}>
                      {loginMutation.isPending ? "Signing in..." : "Login"}
                    </Button>
                    {loginMutation.error ? (
                      <p className="text-sm text-rose-300">{loginMutation.error.message}</p>
                    ) : null}
                  </form>
                ) : (
                  <form className="space-y-4" onSubmit={registerForm.handleSubmit((values) => registerMutation.mutate(values))}>
                    <Input placeholder="Display name" {...registerForm.register("display_name")} />
                    <Input placeholder="Username" {...registerForm.register("username")} />
                    <Input placeholder="Phone number" {...registerForm.register("phone")} />
                    <Input type="password" placeholder="Password" {...registerForm.register("password")} />
                    <Button className="w-full" type="submit" disabled={registerMutation.isPending}>
                      {registerMutation.isPending ? "Sending OTP..." : "Register"}
                    </Button>
                    {registerMutation.error ? (
                      <p className="text-sm text-rose-300">{registerMutation.error.message}</p>
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
                <div className="rounded-[24px] border border-signal-400/20 bg-signal-500/8 p-4 text-sm text-slate-200">
                  <div className="mb-2 flex items-center gap-2 font-medium text-white">
                    <MessageSquareMore className="h-4 w-4 text-signal-200" />
                    Mock OTP ready
                  </div>
                  <p>Use <span className="font-semibold text-signal-100">{mockOtp}</span> for development verification.</p>
                </div>
                <Input placeholder="6-digit OTP" {...otpForm.register("otp")} />
                <Button className="w-full" type="submit" disabled={verifyMutation.isPending}>
                  {verifyMutation.isPending ? "Verifying..." : "Verify OTP"}
                </Button>
                <Button
                  className="w-full"
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
                  <p className="text-sm text-rose-300">{verifyMutation.error.message}</p>
                ) : null}
              </form>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
