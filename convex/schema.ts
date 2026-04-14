import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  users: defineTable({
    email: v.string(),
    passwordHash: v.string(),
    name: v.string(),
    role: v.string(),
    organizerId: v.optional(v.string()),
    country: v.optional(v.string()),
    createdAt: v.number(),
  }).index("email", ["email"]),

  organizers: defineTable({
    name: v.string(),
    email: v.string(),
    createdAt: v.number(),
  }).index("email", ["email"]),

  events: defineTable({
    organizerId: v.string(),
    name: v.string(),
    startDate: v.optional(v.number()),
    endDate: v.optional(v.number()),
    description: v.optional(v.string()),
    createdAt: v.number(),
  }).index("organizerId", ["organizerId"]),

  committees: defineTable({
    eventId: v.string(),
    name: v.string(),
    agenda: v.optional(v.string()),
    chair: v.optional(v.string()),
    coChair: v.optional(v.string()),
    createdAt: v.number(),
  }).index("eventId", ["eventId"]),

  delegateAssignments: defineTable({
    eventId: v.string(),
    userId: v.string(),
    committeeId: v.optional(v.string()),
    createdAt: v.number(),
  }).index("eventId", ["eventId"])
    .index("userId", ["userId"]),

  documents: defineTable({
    eventId: v.string(),
    uploaderId: v.string(),
    docType: v.optional(v.string()),
    filename: v.string(),
    filePath: v.optional(v.string()),
    storageUrl: v.optional(v.string()),
    uploadedAt: v.number(),
  }).index("eventId", ["eventId"]),

  chatMessages: defineTable({
    eventId: v.string(),
    senderId: v.string(),
    message: v.string(),
    timestamp: v.number(),
  }).index("eventId", ["eventId"])
    .index("timestamp", ["timestamp"]),

  announcements: defineTable({
    eventId: v.string(),
    title: v.string(),
    content: v.string(),
    createdBy: v.string(),
    createdAt: v.number(),
    isPinned: v.boolean(),
  }).index("eventId", ["eventId"]),

  passwordResetTokens: defineTable({
    userId: v.string(),
    token: v.string(),
    createdAt: v.number(),
    expiresAt: v.number(),
    used: v.boolean(),
  }).index("token", ["token"]),
});
