import { useState, useDeferredValue } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Users, Search, Check, X, Loader2, ArrowRight } from "lucide-react";
import { toast } from "sonner";

import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { fetchContacts } from "@/services/contacts";
import { createGroup, uploadMedia } from "@/services/chat";

interface CreateGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CreateGroupModal({ isOpen, onClose }: CreateGroupModalProps) {
  const [step, setStep] = useState<"select" | "details">("select");
  const [selectedContactIds, setSelectedContactIds] = useState<string[]>([]);
  const [groupName, setGroupName] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const deferredSearch = useDeferredValue(searchQuery);

  const { accessToken } = useSessionStore();
  const { selectConversation, setFeatureNotice } = useSignalStore();
  const queryClient = useQueryClient();

  const contactsQuery = useQuery({
    queryKey: ["contacts", accessToken],
    queryFn: () => fetchContacts(accessToken!),
    enabled: Boolean(accessToken),
  });

  const createGroupMutation = useMutation({
    mutationFn: () =>
      createGroup(accessToken!, {
        name: groupName,
        description: null,
        avatar_url: avatarUrl,
        member_ids: selectedContactIds,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      selectConversation(data.id);
      handleClose();
      toast.success("Group Created");
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to create group");
      setFeatureNotice(error.message || "Failed to create group");
    },
  });

  const handleClose = () => {
    setStep("select");
    setSelectedContactIds([]);
    setGroupName("");
    setSearchQuery("");
    setAvatarUrl(null);
    onClose();
  };

  const handleAvatarSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const data = await uploadMedia(accessToken!, file);
      setAvatarUrl(data.storage_key as string);
    } catch (err: any) {
      setFeatureNotice(err.message || "Failed to upload avatar");
    } finally {
      setIsUploading(false);
    }
  };

  const toggleContact = (id: string) => {
    setSelectedContactIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const contacts = contactsQuery.data || [];
  const filteredContacts = contacts.filter((c) => {
    if (!deferredSearch) return true;
    const term = deferredSearch.toLowerCase();
    const u = c.contact_user;
    if (!u) return false;
    return (
      u.display_name?.toLowerCase().includes(term) ||
      u.username?.toLowerCase().includes(term) ||
      c.nickname?.toLowerCase().includes(term)
    );
  });

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-md flex flex-col h-[500px] overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900 shadow-2xl"
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-800">
              <h3 className="text-lg font-semibold text-neutral-100">
                {step === "select" ? "Add Members" : "New Group"}
              </h3>
              <button
                onClick={handleClose}
                className="p-1 hover:bg-neutral-800 rounded-full text-neutral-400"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {step === "select" && (
              <>
                <div className="p-4 border-b border-neutral-800">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                    <Input
                      className="h-10 w-full rounded-md border border-neutral-700 bg-neutral-950 pl-10 text-sm text-neutral-200 placeholder-neutral-500 focus-visible:ring-1 focus-visible:ring-blue-500"
                      placeholder="Search contacts"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      autoFocus
                    />
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-2">
                  {contactsQuery.isLoading ? (
                    <div className="flex justify-center p-4">
                      <Loader2 className="w-6 h-6 animate-spin text-signal-blue-500" />
                    </div>
                  ) : filteredContacts.length === 0 ? (
                    <p className="p-4 text-center text-sm text-neutral-500">
                      No contacts found.
                    </p>
                  ) : (
                    filteredContacts.map((contact) => {
                      const u = contact.contact_user;
                      if (!u) return null;
                      const isSelected = selectedContactIds.includes(u.id);

                      return (
                        <div
                          key={contact.id}
                          className="flex items-center justify-between p-2 hover:bg-neutral-800 rounded-lg group cursor-pointer"
                          onClick={() => toggleContact(u.id)}
                        >
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-600 font-semibold text-white relative">
                              {u.display_name?.charAt(0).toUpperCase() || "?"}
                              {isSelected && (
                                <div className="absolute -bottom-1 -right-1 bg-signal-blue-500 rounded-full p-0.5 border border-neutral-900">
                                  <Check className="w-3 h-3 text-white" />
                                </div>
                              )}
                            </div>
                            <div className="flex flex-col">
                              <span className="text-sm font-medium text-neutral-200">
                                {contact.nickname || u.display_name}
                              </span>
                              <span className="text-xs text-neutral-500">
                                @{u.username}
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                <div className="p-4 border-t border-neutral-800">
                  <Button
                    className="w-full bg-signal-blue-500 hover:bg-blue-700 text-white"
                    onClick={() => setStep("details")}
                    disabled={selectedContactIds.length === 0}
                  >
                    Next <ArrowRight className="ml-2 w-4 h-4" />
                  </Button>
                </div>
              </>
            )}

            {step === "details" && (
              <div className="flex-1 flex flex-col p-4">
                <div className="flex-1 flex flex-col items-center justify-center space-y-6">
                  <label className="relative flex w-24 h-24 rounded-full bg-neutral-800 items-center justify-center border-2 border-neutral-700 cursor-pointer overflow-hidden group">
                    <input
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={handleAvatarSelect}
                      disabled={isUploading}
                    />
                    {isUploading ? (
                      <Loader2 className="w-8 h-8 text-neutral-500 animate-spin" />
                    ) : avatarUrl ? (
                      <img
                        src={`/api/v1/attachments/download/${avatarUrl}`}
                        alt="Group Avatar"
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <Users className="w-10 h-10 text-neutral-500 group-hover:text-neutral-400 transition-colors" />
                    )}
                    {!isUploading && !avatarUrl && (
                      <div className="absolute inset-0 bg-black/40 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                        <span className="text-[10px] font-medium text-white uppercase tracking-wider">Upload</span>
                      </div>
                    )}
                  </label>
                  <div className="w-full max-w-xs space-y-2">
                    <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">
                      Group Name
                    </label>
                    <Input
                      className="h-12 w-full rounded-xl border border-neutral-700 bg-neutral-950 px-4 text-base text-neutral-200 placeholder-neutral-500 focus-visible:ring-2 focus-visible:ring-blue-500"
                      placeholder="Name this group"
                      value={groupName}
                      onChange={(e) => setGroupName(e.target.value)}
                      autoFocus
                    />
                  </div>
                  <p className="text-sm text-neutral-500">
                    {selectedContactIds.length} member{selectedContactIds.length !== 1 ? "s" : ""} selected
                  </p>
                </div>

                <div className="flex gap-3 mt-auto">
                  <Button
                    variant="ghost"
                    className="flex-1 text-neutral-300 hover:text-white"
                    onClick={() => setStep("select")}
                  >
                    Back
                  </Button>
                  <Button
                    className="flex-1 bg-signal-blue-500 hover:bg-blue-700 text-white"
                    onClick={() => createGroupMutation.mutate()}
                    disabled={!groupName.trim() || createGroupMutation.isPending || isUploading}
                  >
                    {createGroupMutation.isPending ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                      "Create Group"
                    )}
                  </Button>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
