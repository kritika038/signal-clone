import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { X, UserPlus, Phone, User as UserIcon } from "lucide-react";

import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { searchGlobal } from "@/services/chat";
import { createContact } from "@/services/contacts";
import { apiRequest } from "@/services/api";

interface NewContactModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function NewContactModal({ isOpen, onClose }: NewContactModalProps) {
  const [phone, setPhone] = useState("");
  const [nickname, setNickname] = useState("");
  const { accessToken } = useSessionStore();
  const { selectConversation, setFeatureNotice } = useSignalStore();
  const queryClient = useQueryClient();

  const addContactMutation = useMutation({
    mutationFn: async () => {
      // 1. Search for user by phone
      const searchRes = await searchGlobal(accessToken!, phone);
      const user = searchRes.users.find((u) => u.phone === phone);
      
      if (!user) {
        throw new Error("No user found with this phone number.");
      }

      // 2. Add contact
      await createContact(accessToken!, user.id, nickname || undefined);

      // 3. Start direct conversation
      const convRes = await apiRequest<{ id: string }>("/api/v1/conversations", {
        method: "POST",
        token: accessToken!,
        body: JSON.stringify({ participant_id: user.id }),
      });

      return convRes.id;
    },
    onSuccess: (conversationId) => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setFeatureNotice("Contact added successfully");
      selectConversation(conversationId);
      onClose();
      setPhone("");
      setNickname("");
    },
    onError: (error: Error) => {
      setFeatureNotice(error.message || "Failed to add contact");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!phone.trim()) return;
    addContactMutation.mutate();
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
              <button onClick={onClose} className="p-1 hover:bg-neutral-800 rounded-full text-neutral-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <form onSubmit={handleSubmit} className="p-4 space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-300">Phone Number</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                  <Input
                    className="h-10 w-full rounded-md border border-neutral-700 bg-neutral-950 pl-10 text-sm text-neutral-200 placeholder-neutral-500 focus-visible:ring-1 focus-visible:ring-blue-500"
                    placeholder="+1234567890"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    autoFocus
                    required
                  />
                </div>
                <p className="text-xs text-neutral-500">Include country code (e.g. +1)</p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-300">Nickname (Optional)</label>
                <div className="relative">
                  <UserIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                  <Input
                    className="h-10 w-full rounded-md border border-neutral-700 bg-neutral-950 pl-10 text-sm text-neutral-200 placeholder-neutral-500 focus-visible:ring-1 focus-visible:ring-blue-500"
                    placeholder="e.g. Mom"
                    value={nickname}
                    onChange={(e) => setNickname(e.target.value)}
                  />
                </div>
              </div>

              <Button 
                type="submit" 
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium h-10 mt-2 flex items-center justify-center gap-2"
                disabled={addContactMutation.isPending || !phone.trim()}
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
            </form>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
