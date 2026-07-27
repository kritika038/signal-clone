import {
  format,
  formatDistanceToNowStrict,
  isSameDay,
  isToday,
  isYesterday,
  parseISO,
  differenceInDays,
  isThisYear,
} from "date-fns";

import type { Conversation, SearchResult, ThemeMode } from "@/types/chat";

export function formatSidebarTime(value: string) {
  const date = parseISO(value);
  if (isToday(date)) {
    return format(date, "p");
  }
  if (isYesterday(date)) {
    return "Yesterday";
  }
  if (differenceInDays(new Date(), date) < 7) {
    return format(date, "EEEE");
  }
  if (isThisYear(date)) {
    return format(date, "MMM d");
  }
  return format(date, "MMM d, yyyy");
}

export function formatMessageTime(value: string) {
  return format(parseISO(value), "p");
}

export function formatDayLabel(value: string) {
  const date = parseISO(value);
  if (isToday(date)) {
    return "Today";
  }
  if (isYesterday(date)) {
    return "Yesterday";
  }
  if (isThisYear(date)) {
    return format(date, "EEEE, MMM d");
  }
  return format(date, "EEEE, MMM d, yyyy");
}

export function groupMessagesByDay(conversation: Conversation) {
  return conversation.messages.reduce<Array<{ day: string; ids: string[] }>>((groups, message) => {
    const existing = groups.at(-1);
    if (!existing || !isSameDay(parseISO(existing.ids[0]!), parseISO(message.timestamp))) {
      groups.push({ day: formatDayLabel(message.timestamp), ids: [message.timestamp] });
      return groups;
    }
    existing.ids.push(message.timestamp);
    return groups;
  }, []);
}

export function filterConversations(conversations: Conversation[], query: string) {
  if (!query.trim()) {
    return conversations;
  }
  const normalized = query.toLowerCase();
  return conversations.filter((conversation) => {
    return (
      conversation.title.toLowerCase().includes(normalized) ||
      conversation.lastMessage.toLowerCase().includes(normalized) ||
      conversation.messages.some((message) => message.content.toLowerCase().includes(normalized))
    );
  });
}

export function buildSearchResults(conversations: Conversation[], query: string): SearchResult[] {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return [];
  }

  const results: SearchResult[] = [];

  for (const conversation of conversations) {
    if (conversation.title.toLowerCase().includes(normalized)) {
      results.push({
        id: `conversation-${conversation.id}`,
        type: "conversation",
        title: conversation.title,
        subtitle: conversation.lastMessage,
        conversationId: conversation.id,
        highlight: query,
      });
    }

    for (const member of conversation.members) {
      if (member.name.toLowerCase().includes(normalized)) {
        results.push({
          id: `contact-${member.id}`,
          type: "contact",
          title: member.name,
          subtitle: member.about,
          conversationId: conversation.id,
          highlight: query,
        });
      }
    }

    for (const message of conversation.messages) {
      if (message.content.toLowerCase().includes(normalized)) {
        results.push({
          id: `message-${message.id}`,
          type: "message",
          title: conversation.title,
          subtitle: message.content,
          conversationId: conversation.id,
          highlight: query,
        });
      }
    }
  }

  return results.slice(0, 12);
}

export function cycleThemeMode(theme: ThemeMode): ThemeMode {
  if (theme === "light") {
    return "dark";
  }
  if (theme === "dark") {
    return "system";
  }
  return "light";
}

export function formatPresenceText(lastSeen: string | null) {
  if (!lastSeen) {
    return "Online now";
  }
  return `Seen ${formatDistanceToNowStrict(parseISO(lastSeen), { addSuffix: true })}`;
}
