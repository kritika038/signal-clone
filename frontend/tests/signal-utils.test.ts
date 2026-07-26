import test from "node:test";
import assert from "node:assert/strict";

import { buildSearchResults, cycleThemeMode, filterConversations } from "@/utils/chat";
import { getMockConversations } from "@/features/chat/data/mock-data";

test("authentication shell can search conversations", () => {
  const conversations = getMockConversations();
  const results = filterConversations(conversations, "Signal Desktop");
  assert.equal(results.length, 1);
  assert.equal(results[0]?.title, "Nora Patel");
});

test("global search returns conversation and message matches", () => {
  const conversationResults = buildSearchResults(getMockConversations(), "product");
  const messageResults = buildSearchResults(getMockConversations(), "shipment");
  assert.ok(conversationResults.some((result) => result.type === "conversation"));
  assert.ok(messageResults.some((result) => result.type === "message"));
});

test("global search returns contact matches", () => {
  const results = buildSearchResults(getMockConversations(), "nora");
  assert.ok(results.some((result) => result.type === "contact"));
});

test("theme cycle covers light dark and system", () => {
  assert.equal(cycleThemeMode("light"), "dark");
  assert.equal(cycleThemeMode("dark"), "system");
  assert.equal(cycleThemeMode("system"), "light");
});

test("groups data includes a group conversation", () => {
  const conversations = getMockConversations();
  assert.ok(conversations.some((conversation) => conversation.kind === "group"));
});
