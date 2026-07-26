import { useState, useDeferredValue, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Users, X, Loader2, UserPlus, Edit2, Shield, Trash2, Check, Search } from "lucide-react";

import { useSessionStore } from "@/store/use-session-store";
import { useSignalStore } from "@/store/use-signal-store";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { fetchContacts } from "@/services/contacts";
import { updateGroup, addGroupMember, removeGroupMember, fetchConversation } from "@/services/chat";

interface ConversationInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ConversationInfoModal({ isOpen, onClose }: ConversationInfoModalProps) {
  const { accessToken, user } = useSessionStore();
  const { activeConversationId, setFeatureNotice } = useSignalStore();
  const queryClient = useQueryClient();
  const currentUserId = user?.id || "";

  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [isAddingMember, setIsAddingMember] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const deferredSearch = useDeferredValue(searchQuery);

  const conversationQuery = useQuery({
    queryKey: ["conversation", activeConversationId, accessToken],
    queryFn: () => fetchConversation(accessToken!, activeConversationId!),
    enabled: Boolean(isOpen && activeConversationId && accessToken),
  });

  const contactsQuery = useQuery({
    queryKey: ["contacts", accessToken],
    queryFn: () => fetchContacts(accessToken!),
    enabled: Boolean(isOpen && isAddingMember && accessToken),
  });

  const conversation = conversationQuery.data;
  const members = conversation?.members || [];
  
  // Find current user's role
  const currentUserMember = members.find(m => m.user_id === currentUserId && !m.left_at);
  const isAdmin = currentUserMember?.role === "ADMIN" || currentUserMember?.role === "OWNER";
  const isGroup = conversation?.type === "GROUP";

  const updateMutation = useMutation({
    mutationFn: (name: string) => updateGroup(accessToken!, activeConversationId!, { name }),
    onSuccess: () => {
      setIsEditing(false);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["conversation", activeConversationId] });
    },
    onError: (error: any) => setFeatureNotice(error.message),
  });

  const addMemberMutation = useMutation({
    mutationFn: (userId: string) => addGroupMember(accessToken!, activeConversationId!, userId),
    onSuccess: () => {
      setSearchQuery("");
      setIsAddingMember(false);
      queryClient.invalidateQueries({ queryKey: ["conversation", activeConversationId] });
    },
    onError: (error: any) => setFeatureNotice(error.message),
  });

  const removeMemberMutation = useMutation({
    mutationFn: (memberId: string) => removeGroupMember(accessToken!, activeConversationId!, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversation", activeConversationId] });
    },
    onError: (error: any) => setFeatureNotice(error.message),
  });

  const handleClose = () => {
    setIsEditing(false);
    setIsAddingMember(false);
    setSearchQuery("");
    onClose();
  };

  const filteredContacts = useMemo(() => {
    if (!contactsQuery.data) return [];
    // Filter out existing active members
    const activeMemberIds = new Set(members.filter(m => !m.left_at).map(m => m.user_id));
    let available = contactsQuery.data.filter(c => c.contact_user && !activeMemberIds.has(c.contact_user.id));
    
    if (deferredSearch) {
      const term = deferredSearch.toLowerCase();
      available = available.filter(c => 
        c.contact_user!.display_name?.toLowerCase().includes(term) ||
        c.contact_user!.username?.toLowerCase().includes(term) ||
        c.nickname?.toLowerCase().includes(term)
      );
    }
    return available;
  }, [contactsQuery.data, members, deferredSearch]);

  if (!isOpen || !conversation) return null;

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="w-full max-w-md flex flex-col max-h-[80vh] overflow-hidden rounded-xl border border-neutral-800 bg-neutral-900 shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-neutral-800 shrink-0">
              <h3 className="text-lg font-semibold text-neutral-100">
                {isGroup ? "Group Info" : "Contact Info"}
              </h3>
              <button onClick={handleClose} className="p-1 hover:bg-neutral-800 rounded-full text-neutral-400 transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content area that scrolls */}
            <div className="flex-1 overflow-y-auto">
              <div className="p-6 flex flex-col items-center border-b border-neutral-800 bg-neutral-900/50">
                <div className="w-24 h-24 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-3xl font-semibold mb-4">
                  {conversation.avatar_url ? (
                    <img src={conversation.avatar_url} alt="Avatar" className="w-full h-full rounded-full object-cover" />
                  ) : isGroup ? (
                    <Users className="w-10 h-10" />
                  ) : (
                    conversation.name?.charAt(0).toUpperCase() || "?"
                  )}
                </div>
                
                {isEditing ? (
                  <div className="flex items-center gap-2 w-full max-w-xs">
                    <Input 
                      value={editName} 
                      onChange={(e) => setEditName(e.target.value)}
                      className="bg-neutral-950 border-neutral-700 h-9"
                      placeholder="Group name"
                      autoFocus
                    />
                    <Button 
                      size="icon" 
                      className="h-9 w-9 bg-blue-600 hover:bg-blue-700 text-white shrink-0"
                      onClick={() => updateMutation.mutate(editName)}
                      disabled={!editName.trim() || updateMutation.isPending}
                    >
                      {updateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                    </Button>
                    <Button size="icon" variant="ghost" className="h-9 w-9 text-neutral-400 shrink-0" onClick={() => setIsEditing(false)}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <h2 className="text-xl font-bold text-neutral-100">{conversation.name || "Unknown"}</h2>
                    {isGroup && isAdmin && (
                      <button onClick={() => { setEditName(conversation.name || ""); setIsEditing(true); }} className="text-neutral-500 hover:text-white transition-colors">
                        <Edit2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                )}
                {isGroup && <p className="text-sm text-neutral-500 mt-1">{members.filter(m => !m.left_at).length} members</p>}
              </div>

              {isGroup && (
                <div className="p-4">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="text-sm font-semibold text-neutral-400 uppercase tracking-wider">Members</h4>
                    {isAdmin && !isAddingMember && (
                      <Button size="sm" variant="ghost" className="h-8 text-blue-400 hover:text-blue-300 hover:bg-blue-500/10" onClick={() => setIsAddingMember(true)}>
                        <UserPlus className="w-4 h-4 mr-2" /> Add
                      </Button>
                    )}
                  </div>

                  {isAddingMember && (
                    <div className="mb-6 bg-neutral-950 rounded-lg p-3 border border-neutral-800">
                      <div className="flex justify-between items-center mb-3">
                        <span className="text-sm font-medium">Add Member</span>
                        <button onClick={() => setIsAddingMember(false)} className="text-neutral-500 hover:text-white"><X className="w-4 h-4"/></button>
                      </div>
                      <div className="relative mb-3">
                        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-500" />
                        <Input
                          className="h-9 w-full rounded-md border-neutral-800 bg-neutral-900 pl-9 text-sm focus-visible:ring-1 focus-visible:ring-blue-500"
                          placeholder="Search contacts..."
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                        />
                      </div>
                      <div className="max-h-48 overflow-y-auto space-y-1">
                        {contactsQuery.isLoading ? (
                          <div className="py-4 flex justify-center"><Loader2 className="w-4 h-4 animate-spin text-blue-500" /></div>
                        ) : filteredContacts.length === 0 ? (
                          <p className="py-4 text-center text-xs text-neutral-500">No contacts available to add.</p>
                        ) : (
                          filteredContacts.map(contact => (
                            <div key={contact.id} className="flex items-center justify-between p-2 hover:bg-neutral-800 rounded-md">
                              <div className="flex items-center gap-2 overflow-hidden">
                                <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-xs text-white shrink-0">
                                  {contact.contact_user!.display_name?.charAt(0).toUpperCase()}
                                </div>
                                <span className="text-sm truncate">{contact.nickname || contact.contact_user!.display_name}</span>
                              </div>
                              <Button 
                                size="sm" 
                                className="h-7 text-xs bg-blue-600 hover:bg-blue-700 text-white shrink-0" 
                                onClick={() => addMemberMutation.mutate(contact.contact_user!.id)}
                                disabled={addMemberMutation.isPending}
                              >
                                Add
                              </Button>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    {members.filter(m => !m.left_at).map(member => {
                      const isMe = member.user_id === currentUserId;
                      return (
                        <div key={member.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-neutral-800/50 group">
                          <div className="flex items-center gap-3 overflow-hidden">
                            <div className="w-10 h-10 rounded-full bg-neutral-700 flex items-center justify-center font-medium text-white shrink-0">
                              {member.user?.display_name?.charAt(0).toUpperCase() || "?"}
                            </div>
                            <div className="flex flex-col truncate">
                              <span className="text-sm font-medium text-neutral-200">
                                {isMe ? "You" : member.nickname || member.user?.display_name}
                              </span>
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-neutral-500">@{member.user?.username}</span>
                                {(member.role === "ADMIN" || member.role === "OWNER") && (
                                  <span className="flex items-center text-[10px] uppercase font-bold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                                    <Shield className="w-3 h-3 mr-1" /> {member.role}
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                          {isAdmin && !isMe && member.role !== "OWNER" && (
                            <Button 
                              size="icon" 
                              variant="ghost" 
                              className="h-8 w-8 text-neutral-500 hover:text-red-400 hover:bg-red-950/30 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                              onClick={() => removeMemberMutation.mutate(member.user_id)}
                              title="Remove member"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      );
                    })}
                    {members.some(m => m.left_at) && (
                      <div className="pt-4 mt-4 border-t border-neutral-800/50">
                        <p className="text-xs text-neutral-500 mb-2 font-medium">Past Members</p>
                        {members.filter(m => m.left_at).map(member => (
                          <div key={member.id} className="flex items-center gap-3 p-2 opacity-50">
                            <div className="w-8 h-8 rounded-full bg-neutral-800 flex items-center justify-center text-xs shrink-0">
                              {member.user?.display_name?.charAt(0).toUpperCase() || "?"}
                            </div>
                            <span className="text-sm">{member.nickname || member.user?.display_name} (Left)</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
