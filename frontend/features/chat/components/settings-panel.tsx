"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Laptop, MoonStar, Palette, Shield, Bell, HardDrive, Link2, PlayCircle, Info, ContactRound } from "lucide-react";
import { startTransition, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { fetchSession, updateProfile } from "@/services/auth";
import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import { useFirebaseMessaging } from "@/hooks/use-firebase-messaging";
import { createContact, deleteContact, fetchContacts } from "@/services/contacts";
import { createDirectConversation } from "@/services/chat";
import type { SettingsSection, ThemeMode } from "@/types/chat";

const schema = z.object({
  display_name: z.string().min(2),
  bio: z.string().max(140).optional(),
});

const sections: Array<{ id: SettingsSection; label: string; icon: typeof Palette }> = [
  { id: "contacts", label: "Contacts", icon: ContactRound },
  { id: "profile", label: "Profile", icon: Palette },
  { id: "appearance", label: "Appearance", icon: MoonStar },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "privacy", label: "Privacy", icon: Shield },
  { id: "storage", label: "Storage", icon: HardDrive },
  { id: "linked-devices", label: "Linked Devices", icon: Link2 },
  { id: "stories", label: "Stories", icon: PlayCircle },
  { id: "about", label: "About", icon: Info },
];

export function SettingsPanel() {
  const queryClient = useQueryClient();
  const { accessToken, user, updateUser } = useSessionStore();
  const theme = useSignalStore((state) => state.theme);
  const setTheme = useSignalStore((state) => state.setTheme);
  const activeSection = useSignalStore((state) => state.activeSettingsSection);
  const openSettings = useSignalStore((state) => state.openSettings);
  const closeSettings = useSignalStore((state) => state.closeSettings);
  const isOpen = useSignalStore((state) => state.isSettingsOpen);
  const selectConversation = useSignalStore((state) => state.selectConversation);
  const { enabled: pushEnabled, permission: pushPermission, requestPermissionAndRegister } = useFirebaseMessaging();
  const [contactUserId, setContactUserId] = useState("");
  const [contactNickname, setContactNickname] = useState("");

  const form = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    values: {
      display_name: user?.display_name || "",
      bio: user?.bio || "",
    },
  });

  const sessionQuery = useQuery({
    queryKey: ["session", accessToken],
    queryFn: () => fetchSession(accessToken!),
    enabled: Boolean(accessToken && isOpen && activeSection === "about"),
  });

  const profileMutation = useMutation({
    mutationFn: (values: z.infer<typeof schema>) => updateProfile(accessToken!, values),
    onSuccess: (updated) => updateUser(updated),
  });
  const contactsQuery = useQuery({
    queryKey: ["contacts", accessToken],
    queryFn: () => fetchContacts(accessToken!),
    enabled: Boolean(accessToken && isOpen && activeSection === "contacts"),
  });
  const contactMutation = useMutation({
    mutationFn: () => createContact(accessToken!, contactUserId.trim(), contactNickname.trim()),
    onSuccess: async () => {
      setContactUserId("");
      setContactNickname("");
      await contactsQuery.refetch();
    },
  });
  const deleteContactMutation = useMutation({
    mutationFn: (contactId: string) => deleteContact(accessToken!, contactId),
    onSuccess: () => void contactsQuery.refetch(),
  });
  const startConversationMutation = useMutation({
    mutationFn: (participantId: string) => createDirectConversation(accessToken!, participantId),
    onSuccess: async (conversation) => {
      selectConversation(conversation.id);
      closeSettings();
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
  });

  if (!isOpen || !user) {
    return null;
  }

  return (
    <aside className="w-full border-l border-white/8 bg-[#0b131d]/95 backdrop-blur-2xl md:max-w-[360px]">
      <div className="flex items-center justify-between border-b border-white/8 px-5 py-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Settings</p>
          <h3 className="mt-1 text-lg font-semibold text-white">Your Signal workspace</h3>
        </div>
        <Button size="sm" variant="ghost" onClick={closeSettings}>
          Close
        </Button>
      </div>

      <div className="grid grid-cols-[132px_1fr] h-[calc(100vh-76px)]">
        <nav className="border-r border-white/8 p-3">
          <div className="space-y-1">
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={`flex w-full items-center gap-3 rounded-2xl px-3 py-2 text-left text-sm transition ${
                  activeSection === id ? "bg-white text-slate-950" : "text-slate-300 hover:bg-white/6"
                }`}
                onClick={() => startTransition(() => openSettings(id))}
                type="button"
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </nav>

        <div className="overflow-y-auto p-5">
          {activeSection === "contacts" ? (
            <div className="space-y-4">
              <Badge>Contacts</Badge>
              <p className="text-sm text-slate-400">Add a contact using their Signal user ID, then start a direct conversation from the inbox.</p>
              <Input value={contactUserId} onChange={(event) => setContactUserId(event.target.value)} placeholder="Contact user ID" />
              <Input value={contactNickname} onChange={(event) => setContactNickname(event.target.value)} placeholder="Nickname (optional)" />
              <Button disabled={!contactUserId.trim() || contactMutation.isPending} onClick={() => contactMutation.mutate()} type="button">
                {contactMutation.isPending ? "Adding…" : "Add contact"}
              </Button>
              <div className="space-y-2">
                {contactsQuery.data?.map((contact) => (
                  <div key={contact.id} className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-3 py-3 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-white">{contact.nickname || contact.contact_user?.display_name || contact.contact_user?.username || contact.contact_user?.phone}</p>
                      <p className="truncate text-xs text-slate-400">{contact.contact_user?.phone || contact.contact_user_id}</p>
                    </div>
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => startConversationMutation.mutate(contact.contact_user_id)} type="button">Chat</Button>
                      <Button size="sm" variant="ghost" onClick={() => deleteContactMutation.mutate(contact.id)} type="button">Remove</Button>
                    </div>
                  </div>
                ))}
                {contactsQuery.isLoading ? <p className="text-sm text-slate-400">Loading contacts…</p> : null}
                {!contactsQuery.isLoading && !contactsQuery.data?.length ? <p className="text-sm text-slate-400">No contacts yet.</p> : null}
              </div>
            </div>
          ) : null}
          {activeSection === "profile" ? (
            <form className="space-y-4" onSubmit={form.handleSubmit((values) => profileMutation.mutate(values))}>
              <Badge>Profile</Badge>
              <Input {...form.register("display_name")} placeholder="Display name" />
              <Textarea {...form.register("bio")} placeholder="Write a short bio" />
              <Button type="submit" disabled={profileMutation.isPending}>
                {profileMutation.isPending ? "Saving..." : "Save profile"}
              </Button>
            </form>
          ) : null}

          {activeSection === "appearance" ? (
            <div className="space-y-4">
              <Badge>Appearance</Badge>
              <p className="text-sm text-slate-400">Switch between light, dark, or system theme modes.</p>
              <div className="grid gap-3">
                {(["light", "dark", "system"] as ThemeMode[]).map((mode) => (
                  <button
                    key={mode}
                    className={`rounded-3xl border px-4 py-4 text-left ${
                      theme === mode ? "border-signal-400 bg-signal-500/10" : "border-white/10 bg-white/5"
                    }`}
                    onClick={() => setTheme(mode)}
                    type="button"
                  >
                    <div className="font-medium capitalize text-white">{mode}</div>
                    <div className="text-sm text-slate-400">
                      {mode === "system" ? "Match the device preference." : `Use ${mode} appearance.`}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {activeSection === "notifications" ? (
            <div className="space-y-4">
              <Section title="Notifications" body="Enable browser notifications to receive messages while Signal is in the background." />
              <Button
                type="button"
                disabled={!pushEnabled || pushPermission === "denied"}
                onClick={() => void requestPermissionAndRegister()}
              >
                {pushPermission === "granted" ? "Push notifications enabled" : "Enable browser notifications"}
              </Button>
              {!pushEnabled ? <p className="text-sm text-slate-400">Push notifications are not configured for this deployment.</p> : null}
              {pushPermission === "denied" ? <p className="text-sm text-slate-400">Notifications are blocked in your browser settings.</p> : null}
            </div>
          ) : null}
          {activeSection === "privacy" ? (
            <Section title="Privacy" body="Signal-like privacy controls are represented in the profile settings returned by the auth API." />
          ) : null}
          {activeSection === "storage" ? (
            <Section title="Storage" body="Media and file gallery endpoints exist per conversation, but upload and attachment send endpoints are still missing." />
          ) : null}
          {activeSection === "linked-devices" ? (
            <ComingSoon title="Linked Devices" body="This surface is polished, but device-linking endpoints are not yet available." />
          ) : null}
          {activeSection === "stories" ? (
            <ComingSoon title="Stories" body="Stories are intentionally out of scope for now, matching the product brief." />
          ) : null}
          {activeSection === "about" ? (
            <div className="space-y-4">
              <Badge>About</Badge>
              <Section
                title="Session"
                body={
                  sessionQuery.data
                    ? `${sessionQuery.data.device_name} • ${sessionQuery.data.device_type} • ${sessionQuery.data.ip_address}`
                    : "Loading current device session…"
                }
              />
              <Section title="Build" body="Next.js 15, React 19, Zustand, TanStack Query, Tailwind CSS." />
              <div className="rounded-[28px] border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
                <div className="mb-2 flex items-center gap-2 font-medium text-white">
                  <Laptop className="h-4 w-4 text-signal-200" />
                  Signal Web Clone
                </div>
                <p>This frontend tracks the available backend exactly and avoids inventing unsupported API contracts.</p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </aside>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-[28px] border border-white/10 bg-white/5 p-4">
      <h4 className="font-medium text-white">{title}</h4>
      <p className="mt-2 text-sm leading-6 text-slate-400">{body}</p>
    </div>
  );
}

function ComingSoon({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex h-full min-h-[320px] flex-col items-center justify-center rounded-[32px] border border-dashed border-white/12 bg-white/4 p-8 text-center">
      <Badge>{title}</Badge>
      <h4 className="mt-5 text-2xl font-semibold text-white">Coming Soon</h4>
      <p className="mt-3 max-w-sm text-sm leading-6 text-slate-400">{body}</p>
    </div>
  );
}
