import { addMinutes, subDays, subHours, subMinutes } from "date-fns";

import type { Contact, Conversation } from "@/types/chat";

const contacts: Contact[] = [
  {
    id: "me",
    name: "You",
    phone: "+1 202 555 0199",
    avatar: "YK",
    status: "online",
    about: "Focused mode on. Replies soon.",
  },
  {
    id: "nora",
    name: "Nora Patel",
    phone: "+1 202 555 0142",
    avatar: "NP",
    status: "online",
    about: "Designing the impossible.",
  },
  {
    id: "leo",
    name: "Leo Walker",
    phone: "+1 202 555 0160",
    avatar: "LW",
    status: "away",
    about: "On the train. Signal me.",
  },
  {
    id: "maya",
    name: "Maya Chen",
    phone: "+1 202 555 0120",
    avatar: "MC",
    status: "offline",
    about: "Weekend photo dump incoming.",
  },
  {
    id: "crew",
    name: "Product Crew",
    phone: "",
    avatar: "PC",
    status: "online",
    about: "Group thread",
  },
];

const now = new Date();

export function getMockContacts() {
  return contacts.filter((contact) => contact.id !== "crew");
}

export function getMockConversations(): Conversation[] {
  return [
    {
      id: "conv-nora",
      kind: "direct",
      title: "Nora Patel",
      avatar: "NP",
      members: [contacts[1]],
      unreadCount: 2,
      isMuted: false,
      lastMessage: "I tightened the spacing so it feels closer to Signal Desktop.",
      lastMessageAt: subMinutes(now, 3).toISOString(),
      typingText: "Nora is typing…",
      messages: [
        {
          id: "m1",
          senderId: "nora",
          content: "I tightened the spacing so it feels closer to Signal Desktop.",
          timestamp: subMinutes(now, 3).toISOString(),
          status: "read",
          isOutgoing: false,
          reactions: [{ emoji: "👌", count: 1, reacted: false }],
        },
        {
          id: "m2",
          senderId: "me",
          content: "Perfect. Keep the message composer compact and the bubbles soft.",
          timestamp: subMinutes(now, 2).toISOString(),
          status: "read",
          isOutgoing: true,
          pinned: true,
        },
        {
          id: "m3",
          senderId: "nora",
          content: "On it. I also added a clearer draft state in the sidebar.",
          timestamp: subMinutes(now, 1).toISOString(),
          status: "delivered",
          isOutgoing: false,
          quotedMessageId: "m2",
        },
      ],
    },
    {
      id: "conv-crew",
      kind: "group",
      title: "Product Crew",
      avatar: "PC",
      members: [contacts[1], contacts[2], contacts[3]],
      unreadCount: 0,
      isMuted: true,
      lastMessage: "Leo: Shipment landed. Let's review in the morning.",
      lastMessageAt: subHours(now, 2).toISOString(),
      messages: [
        {
          id: "gm1",
          senderId: "leo",
          content: "Shipment landed. Let's review in the morning.",
          timestamp: subHours(now, 2).toISOString(),
          status: "read",
          isOutgoing: false,
          forwardedFrom: "Ops Desk",
          disappearingLabel: "1 day",
        },
        {
          id: "gm2",
          senderId: "me",
          content: "Pinned the launch checklist so no one has to search for it.",
          timestamp: subHours(now, 1).toISOString(),
          status: "read",
          isOutgoing: true,
          pinned: true,
          reactions: [{ emoji: "📌", count: 3, reacted: true }],
        },
      ],
    },
    {
      id: "conv-maya",
      kind: "direct",
      title: "Maya Chen",
      avatar: "MC",
      members: [contacts[3]],
      unreadCount: 0,
      isMuted: false,
      lastMessage: "Shared three edits and a reference clip.",
      lastMessageAt: subDays(now, 1).toISOString(),
      draft: "Need the final export dimensions",
      messages: [
        {
          id: "mm1",
          senderId: "maya",
          content: "Shared three edits and a reference clip.",
          timestamp: subDays(now, 1).toISOString(),
          status: "read",
          isOutgoing: false,
          attachments: [
            {
              id: "att1",
              name: "signal-motion-reference.mp4",
              type: "video",
              sizeLabel: "18 MB",
              progress: 100,
            },
          ],
        },
      ],
    },
    {
      id: "conv-leo",
      kind: "direct",
      title: "Leo Walker",
      avatar: "LW",
      members: [contacts[2]],
      unreadCount: 0,
      isMuted: false,
      lastMessage: "Scheduled for 8:30 AM.",
      lastMessageAt: addMinutes(subHours(now, 5), 30).toISOString(),
      messages: [
        {
          id: "lm1",
          senderId: "me",
          content: "Scheduled for 8:30 AM.",
          timestamp: subHours(now, 5).toISOString(),
          status: "sent",
          isOutgoing: true,
          scheduledFor: addMinutes(subHours(now, 5), 30).toISOString(),
        },
      ],
    },
  ];
}
