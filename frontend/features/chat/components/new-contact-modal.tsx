import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { X, UserPlus, Phone, Search } from "lucide-react";

import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { searchUserByPhone, ApiUserSummary } from "@/services/chat";
import { createContact } from "@/services/contacts";
import { apiRequest } from "@/services/api";

interface NewContactModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NewContactModal({ isOpen, onClose }: NewContactModalProps) {
  const [phone, setPhone] = useState("");
  const [searchResult, setSearchResult] = useState<ApiUserSummary | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const { accessToken, user: currentUser } = useSessionStore();
  const { selectConversation, setFeatureNotice } = useSignalStore();
  const queryClient = useQueryClient();

  // Reset state when closing/opening
  const handleClose = () => {
    setPhone("");
    setSearchResult(null);
    setHasSearched(false);
    onClose();
  };

  const searchMutation = useMutation({
    mutationFn: async () => {
      if (!phone.trim()) throw new Error("Phone number is required");
      return searchUserByPhone(accessToken!, phone.trim());
    },
    onSuccess: (user) => {
      setSearchResult(user);
      setHasSearched(true);
    },
    onError: (error: Error) => {
      setSearchResult(null);
      setHasSearched(true);
      setFeatureNotice(error.message || "Search failed");
    },
  });

  const addContactMutation = useMutation({
    mutationFn: async () => {
      if (!searchResult) throw new Error("No user to add");
      if (searchResult.id === currentUser?.id) {
        throw new Error("Cannot add yourself as a contact");
      }

      // 1. Add contact
      await createContact(accessToken!, searchResult.id, searchResult.display_name || undefined);

      // 2. Start direct conversation
      const convRes = await apiRequest<{ id: string }>("/api/v1/conversations", {
        method: "POST",
        token: accessToken!,
        body: JSON.stringify({ participant_id: searchResult.id }),
      });

      return convRes.id;
    },
    onSuccess: (conversationId) => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setFeatureNotice("Contact added successfully");
      selectConversation(conversationId);
      handleClose();
    },
    onError: (error: Error) => {
      setFeatureNotice(error.message || "Failed to add contact");
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;
    searchMutation.mutate();
  };

  const handlePhoneChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPhone(e.target.value);
    setHasSearched(false);
    setSearchResult(null);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-sm overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900 shadow-2xl"
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-800">
              <h3 className="text-lg font-semibold text-neutral-100">Add New Contact</h3>
              <button onClick={handleClose} className="p-1 hover:bg-neutral-800 rounded-full text-neutral-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4 space-y-4">
              <form onSubmit={handleSearch} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-neutral-300">Phone Number</label>
                  <div className="flex gap-2">
                    <div className="relative flex-1">
                      <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                      <Input
                        className="h-10 w-full rounded-md border border-neutral-700 bg-neutral-950 pl-10 text-sm text-neutral-200 placeholder-neutral-500 focus-visible:ring-1 focus-visible:ring-blue-500"
                        placeholder="+1234567890"
                        value={phone}
                        onChange={handlePhoneChange}
                        autoFocus
                        required
                      />
                    </div>
                    <Button
                      type="submit"
                      disabled={searchMutation.isPending || !phone.trim()}
                      className="bg-neutral-700 hover:bg-neutral-600 text-white"
                    >
                      {searchMutation.isPending ? (
                        <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                      ) : (
                        <Search className="w-4 h-4" />
                      )}
                    </Button>
                  </div>
                  <p className="text-xs text-neutral-500">Include country code (e.g. +1)</p>
                </div>
              </form>

              {hasSearched && (
                <div className="pt-4 border-t border-neutral-800">
                  {searchResult ? (
                    <div className="space-y-4">
                      <div className="flex items-center gap-3 p-3 rounded-lg bg-neutral-800/50">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-blue-600 text-sm font-semibold text-white">
                          {searchResult.avatar_url ? (
                            <img src={searchResult.avatar_url} alt="Avatar" className="h-full w-full rounded-full object-cover" />
                          ) : (
                            searchResult.display_name?.slice(0, 2).toUpperCase() || searchResult.username?.slice(0, 2).toUpperCase() || "U"
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="truncate text-sm font-medium text-neutral-100">
                            {searchResult.display_name || "Unknown"}
                          </p>
                          {searchResult.username && (
                            <p className="truncate text-xs text-neutral-400">@{searchResult.username}</p>
                          )}
                          <p className="truncate text-xs text-neutral-500 mt-0.5">{searchResult.phone}</p>
                        </div>
                      </div>

                      {searchResult.id === currentUser?.id ? (
                        <p className="text-sm text-yellow-500 text-center">This is your own phone number.</p>
                      ) : (
                        <Button
                          onClick={() => addContactMutation.mutate()}
                          disabled={addContactMutation.isPending}
                          className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium h-10 flex items-center justify-center gap-2"
                        >
                          {addContactMutation.isPending ? (
                            <div className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                          ) : (
                            <>
                              <UserPlus className="w-4 h-4" />
                              Add Contact
                            </>
                          )}
                        </Button>
                      )}
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-400 text-center py-4">
                      No user found with this phone number.
                    </p>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
