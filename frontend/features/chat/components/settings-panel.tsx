"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Laptop, MoonStar, Palette, Shield, Bell, HardDrive, Link2, PlayCircle, Info, ContactRound } from "lucide-react";
import { startTransition, useState, useRef } from "react";
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
  username: z.string().min(3).max(30).optional(),
  bio: z.string().max(140).optional(),
  avatar_url: z.string().optional(),
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
      username: user?.username || "",
      bio: user?.bio || "",
      avatar_url: user?.avatar_url || "",
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
    <aside className="w-full md:w-[320px] shrink-0 border-l border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900">
      <div className="flex h-14 items-center justify-between border-b border-neutral-200 dark:border-neutral-800 px-4">
        <div>
          <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Settings</p>
          <h3 className="mt-1 text-lg font-semibold text-white">Your Signal workspace</h3>
        </div>
        <Button size="sm" variant="ghost" onClick={closeSettings}>
          Close
        </Button>
      </div>

      <div className="flex h-[calc(100vh-56px)] flex-col">
        <nav className="border-b border-neutral-200 dark:border-neutral-800 p-2 overflow-x-auto">
          <div className="flex space-x-1">
            {sections.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={`flex shrink-0 items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition ${
                  activeSection === id ? "bg-neutral-200 dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100" : "text-neutral-500 dark:text-neutral-500 hover:bg-neutral-200 dark:hover:bg-neutral-200 dark:bg-neutral-800/50 hover:text-neutral-300"
                }`}
                onClick={() => startTransition(() => openSettings(id))}
                type="button"
              >
                <Icon className="h-4 w-4" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </nav>

        <div className="flex-1 overflow-y-auto p-4 bg-white dark:bg-neutral-950">
          {activeSection === "contacts" ? (
            <div className="space-y-4">
              <Badge className="bg-neutral-200 dark:bg-neutral-800 text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-200 dark:bg-neutral-800">Contacts</Badge>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">Add a contact using their Signal user ID.</p>
              <Input className="bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 h-9" value={contactUserId} onChange={(event) => setContactUserId(event.target.value)} placeholder="Contact user ID" />
              <Input className="bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 h-9" value={contactNickname} onChange={(event) => setContactNickname(event.target.value)} placeholder="Nickname (optional)" />
              <Button className="w-full bg-blue-600 hover:bg-blue-700 h-9" disabled={!contactUserId.trim() || contactMutation.isPending} onClick={() => contactMutation.mutate()} type="button">
                {contactMutation.isPending ? "Adding…" : "Add contact"}
              </Button>
              <div className="space-y-2">
                {contactsQuery.data?.map((contact) => (
                  <div key={contact.id} className="flex flex-col gap-2 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900 p-3 text-sm">
                    <div className="min-w-0">
                      <p className="truncate font-medium text-neutral-900 dark:text-neutral-200">{contact.nickname || contact.contact_user?.display_name || contact.contact_user?.username || contact.contact_user?.phone}</p>
                      <p className="truncate text-xs text-neutral-500 dark:text-neutral-500">{contact.contact_user?.phone || contact.contact_user_id}</p>
                    </div>
                    <div className="flex gap-2 w-full mt-1">
                      <Button className="flex-1 h-8 bg-blue-600 hover:bg-blue-700 text-white" size="sm" onClick={() => startConversationMutation.mutate(contact.contact_user_id)} type="button">Chat</Button>
                      <Button className="flex-1 h-8 bg-neutral-200 dark:bg-neutral-800 hover:bg-red-900/50 hover:text-red-400 text-neutral-600 dark:text-neutral-400" size="sm" variant="ghost" onClick={() => deleteContactMutation.mutate(contact.id)} type="button">Remove</Button>
                    </div>
                  </div>
                ))}
                {contactsQuery.isLoading ? <p className="text-sm text-slate-400">Loading contacts…</p> : null}
                {!contactsQuery.isLoading && !contactsQuery.data?.length ? <p className="text-sm text-slate-400">No contacts yet.</p> : null}
              </div>
            </div>
          ) : null}
          {activeSection === "profile" ? (
            <div className="space-y-6">
              <Badge className="bg-neutral-200 dark:bg-neutral-800 text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-200 dark:bg-neutral-800">Profile</Badge>
              <div className="flex flex-col items-center gap-4">
                <div className="relative h-24 w-24 overflow-hidden rounded-full bg-neutral-200 dark:bg-neutral-800 flex items-center justify-center">
                  {form.watch("avatar_url") ? (
                    <img src={form.watch("avatar_url")} alt="Avatar" className="h-full w-full object-cover" />
                  ) : (
                    <span className="text-2xl text-neutral-500 dark:text-neutral-500">{user?.display_name?.slice(0, 2).toUpperCase()}</span>
                  )}
                  <label className="absolute inset-0 flex cursor-pointer items-center justify-center bg-black/50 opacity-0 transition hover:opacity-100">
                    <span className="text-xs font-medium text-white">Change</span>
                    <input
                      type="file"
                      className="hidden"
                      accept="image/*"
                      onChange={async (e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        try {
                          const { uploadMedia } = await import("@/services/chat");
                          const data = await uploadMedia(accessToken!, file);
                          const url = data?.playback_url || data?.url;
                          if (url) {
                            form.setValue("avatar_url", url as string, { shouldDirty: true });
                            profileMutation.mutate(form.getValues());
                          }
                        } catch (err) {
                          useSignalStore.getState().setFeatureNotice("Failed to upload avatar");
                        }
                      }}
                    />
                  </label>
                </div>
              </div>
              <form className="space-y-4" onSubmit={form.handleSubmit((values) => profileMutation.mutate(values))}>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-600 dark:text-neutral-400">Display Name</label>
                  <Input className="bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 h-9" {...form.register("display_name")} placeholder="Display name" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-600 dark:text-neutral-400">Username</label>
                  <Input className="bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 h-9" {...form.register("username")} placeholder="Username" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-neutral-600 dark:text-neutral-400">Bio</label>
                  <Textarea className="bg-neutral-100 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 min-h-[80px]" {...form.register("bio")} placeholder="Write a short bio" />
                </div>
                <Button className="w-full bg-blue-600 hover:bg-blue-700 h-9" type="submit" disabled={profileMutation.isPending || !form.formState.isDirty}>
                  {profileMutation.isPending ? "Saving..." : "Save profile"}
                </Button>
              </form>
            </div>
          ) : null}

          {activeSection === "appearance" ? (
            <div className="space-y-4">
              <Badge className="bg-neutral-200 dark:bg-neutral-800 text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-200 dark:bg-neutral-800">Appearance</Badge>
              <p className="text-sm text-neutral-600 dark:text-neutral-400">Switch between light, dark, or system theme modes.</p>
              <div className="grid gap-2">
                {(["light", "dark", "system"] as ThemeMode[]).map((mode) => (
                  <button
                    key={mode}
                    className={`rounded-lg border px-3 py-3 text-left transition ${
                      theme === mode ? "border-blue-500 bg-blue-500/10" : "border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900 hover:bg-neutral-200 dark:hover:bg-neutral-200 dark:bg-neutral-800"
                    }`}
                    onClick={() => setTheme(mode)}
                    type="button"
                  >
                    <div className="font-medium capitalize text-neutral-900 dark:text-neutral-200 text-sm">{mode}</div>
                    <div className="text-xs text-neutral-500 dark:text-neutral-500 mt-1">
                      {mode === "system" ? "Match the device preference." : `Use ${mode} appearance.`}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {activeSection === "notifications" ? (
            <ComingSoon title="Notifications" body="Notification settings will be available in a future update." />
          ) : null}
          {activeSection === "privacy" ? (
            <ComingSoon title="Privacy" body="Signal-like privacy controls will be available in a future update." />
          ) : null}
          {activeSection === "storage" ? (
            <ComingSoon title="Storage" body="Media and file gallery management will be available in a future update." />
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
    <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-neutral-100 dark:bg-neutral-900 p-4">
      <h4 className="font-medium text-neutral-900 dark:text-neutral-200 text-sm">{title}</h4>
      <p className="mt-1.5 text-xs leading-5 text-neutral-600 dark:text-neutral-400">{body}</p>
    </div>
  );
}

function ComingSoon({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex h-full min-h-[240px] flex-col items-center justify-center rounded-lg border border-dashed border-neutral-200 dark:border-neutral-800 bg-neutral-50/50 dark:bg-neutral-100 dark:bg-neutral-900/50 p-6 text-center">
      <Badge className="bg-neutral-200 dark:bg-neutral-800 text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-200 dark:bg-neutral-800">{title}</Badge>
      <h4 className="mt-4 text-lg font-semibold text-neutral-900 dark:text-neutral-200">Coming Soon</h4>
      <p className="mt-2 max-w-[200px] text-xs leading-5 text-neutral-500 dark:text-neutral-500">{body}</p>
    </div>
  );
}
