import { useState, useDeferredValue } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Search, UserPlus, MessageSquare, X, Users } from "lucide-react";

import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { searchGlobal } from "@/services/chat";
import { createContact, fetchContacts } from "@/services/contacts";
import { apiRequest } from "@/services/api";

interface NewChatModalProps {
  isOpen: boolean;
  onClose: () => void;
  onNewGroup?: () => void;
}

export function NewChatModal({ isOpen, onClose, onNewGroup }: NewChatModalProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearch = useDeferredValue(searchQuery);
  const { accessToken, user } = useSessionStore();
  const { selectConversation, setFeatureNotice } = useSignalStore();
  const queryClient = useQueryClient();

  const searchResult = useQuery({
    queryKey: ["global-search", deferredSearch, accessToken],
    queryFn: () => searchGlobal(accessToken!, deferredSearch),
    enabled: Boolean(accessToken && deferredSearch.trim().length > 0),
  });

  const contactsQuery = useQuery({
    queryKey: ["contacts", accessToken],
    queryFn: () => fetchContacts(accessToken!),
    enabled: Boolean(accessToken),
  });

  const addContactMutation = useMutation({
    mutationFn: (contactUserId: string) => createContact(accessToken!, contactUserId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["contacts"] });
      setFeatureNotice("Contact Added");
    },
    onError: (error: any) => {
      setFeatureNotice(error.message || "Failed to add contact");
    }
  });

  const startDirectChatMutation = useMutation({
    mutationFn: (participantId: string) =>
      apiRequest<{ id: string }>("/api/v1/conversations", {
        method: "POST",
        token: accessToken!,
        body: JSON.stringify({ participant_id: participantId }),
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      selectConversation(data.id);
      onClose();
    },
    onError: (error: any) => {
      setFeatureNotice(error.message || "Failed to start conversation");
    }
  });

  const searchUsers = searchResult.data?.users || [];
  const contacts = contactsQuery.data || [];

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
              <h3 className="text-lg font-semibold text-neutral-100">New Chat</h3>
              <button onClick={onClose} className="p-1 hover:bg-neutral-800 rounded-full text-neutral-400">
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                <Input
                  className="h-10 w-full rounded-md border border-neutral-700 bg-neutral-950 pl-10 text-sm text-neutral-200 placeholder-neutral-500 focus-visible:ring-1 focus-visible:ring-blue-500"
                  placeholder="Search Phone, Username, or Display Name"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  autoFocus
                />
              </div>
              {!deferredSearch && (
                <button
                  onClick={onNewGroup}
                  className="mt-4 flex w-full items-center gap-3 rounded-lg p-2 hover:bg-neutral-800 transition-colors"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-neutral-800 border border-neutral-700">
                    <Users className="w-5 h-5 text-neutral-300" />
                  </div>
                  <span className="text-sm font-medium text-neutral-200">New Group</span>
                </button>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-2">
              {deferredSearch ? (
                <>
                  <p className="px-2 py-1 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Search Results</p>
                  {searchResult.isLoading ? (
                    <div className="flex justify-center p-4"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>
                  ) : searchUsers.length === 0 ? (
                    <p className="p-4 text-center text-sm text-neutral-500">No users found.</p>
                  ) : (
                    searchUsers.map((u: any) => {
                      const isSelf = u.id === user?.id;
                      const isContact = contacts.some(c => c.contact_user_id === u.id);
                      
                      return (
                        <div key={u.id} className="flex items-center justify-between p-2 hover:bg-neutral-800 rounded-lg group">
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-blue-600 font-semibold text-white">
                              {u.display_name?.charAt(0).toUpperCase() || u.username?.charAt(0).toUpperCase() || "?"}
                            </div>
                            <div className="flex flex-col">
                              <span className="text-sm font-medium text-neutral-200">{u.display_name}</span>
                              <span className="text-xs text-neutral-500">@{u.username} • {u.phone}</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            {isSelf ? (
                              <span className="text-xs text-neutral-500 bg-neutral-800 px-2 py-1 rounded">You</span>
                            ) : isContact ? (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 w-8 p-0 text-blue-400 hover:text-blue-300 hover:bg-blue-900/30 rounded-full"
                                onClick={() => startDirectChatMutation.mutate(u.id)}
                                disabled={startDirectChatMutation.isPending}
                              >
                                <MessageSquare className="w-4 h-4" />
                              </Button>
                            ) : (
                              <Button 
                                variant="ghost" 
                                size="sm" 
                                className="h-8 w-8 p-0 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded-full"
                                onClick={() => addContactMutation.mutate(u.id)}
                                disabled={addContactMutation.isPending}
                                title="Add Contact"
                              >
                                <UserPlus className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      );
                    })
                  )}
                </>
              ) : (
                <>
                  <p className="px-2 py-1 text-xs font-semibold text-neutral-500 uppercase tracking-wider">Your Contacts</p>
                  {contactsQuery.isLoading ? (
                    <div className="flex justify-center p-4"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div></div>
                  ) : contacts.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-40 text-center px-4">
                      <p className="text-sm text-neutral-400 mb-2">No contacts yet</p>
                      <p className="text-xs text-neutral-600">Search above to find and add people.</p>
                    </div>
                  ) : (
                    contacts.map((contact) => {
                      const u = contact.contact_user;
                      if (!u) return null;
                      return (
                        <div key={contact.id} className="flex items-center justify-between p-2 hover:bg-neutral-800 rounded-lg group cursor-pointer" onClick={() => startDirectChatMutation.mutate(u.id)}>
                          <div className="flex items-center gap-3">
                            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-600 font-semibold text-white">
                              {u.display_name?.charAt(0).toUpperCase() || u.username?.charAt(0).toUpperCase() || "?"}
                            </div>
                            <div className="flex flex-col">
                              <span className="text-sm font-medium text-neutral-200">{contact.nickname || u.display_name}</span>
                              <span className="text-xs text-neutral-500">@{u.username}</span>
                            </div>
                          </div>
                          <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                            <MessageSquare className="w-5 h-5 text-neutral-400" />
                          </div>
                        </div>
                      );
                    })
                  )}
                </>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
