import { z } from "zod";

/**
 * Standard Authentication Schema for Login & Registration
 */
export const authSchema = z.object({
  phoneNumber: z
    .string()
    .min(10, "Phone number must be at least 10 digits")
    .max(15, "Phone number must not exceed 15 digits")
    .regex(/^\+?[1-9]\d{1,14}$/, "Please enter a valid E.164 phone number (e.g., +1234567890)"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .max(64, "Password must not exceed 64 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[a-z]/, "Password must contain at least one lowercase letter")
    .regex(/[0-9]/, "Password must contain at least one number")
    .regex(/[^A-Za-z0-9]/, "Password must contain at least one special character"),
});

/**
 * Message sending schema for real-time messaging
 */
export const sendMessageSchema = z.object({
  recipientId: z.string().uuid("Invalid recipient ID"),
  content: z.string().min(1, "Message content cannot be empty").max(2000, "Message is too long"),
});

export type AuthSchemaInput = z.infer<typeof authSchema>;
export type SendMessageSchemaInput = z.infer<typeof sendMessageSchema>;
