import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { z } from "zod";

const messageSchema = z.object({
  id: z.string(),
  body: z.unknown(),
  // The AMQP properties worth reading back, kept apart from the body so a
  // malformed payload still shows who sent it and when.
  correlationId: z.string().optional(),
  replyTo: z.string().optional(),
  contentType: z.string().optional(),
  bytes: z.number(),
  receivedAt: z.string(),
});

export type WitnessMessage = z.infer<typeof messageSchema>;

const DATA_DIR = join(process.cwd(), ".data");
const MESSAGES_FILE = join(DATA_DIR, "messages.json");
const MAX_MESSAGES = 200;

const load = () => {
  try {
    return messageSchema.array().parse(JSON.parse(readFileSync(MESSAGES_FILE, "utf8")));
  } catch {
    return [];
  }
};

// Kept on disk so a restart of the dev server does not lose what was read: a
// message consumed here is gone from the queue, this file is the only copy.
const messages = load();
let connected = false;
let lastError = "";

const persist = () => {
  try {
    mkdirSync(DATA_DIR, { recursive: true });
    writeFileSync(MESSAGES_FILE, JSON.stringify(messages));
  } catch {
    // Losing the archive must never break the consumer.
  }
};

// Pages waiting to be told the instant a message lands, rather than finding out
// at their next poll. A listener is an open request: it must be dropped when
// the page closes, which is what the returned function is for.
type Listener = (message: WitnessMessage) => void;
const listeners = new Set<Listener>();

export const subscribe = (listener: Listener) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

export const addMessage = (message: WitnessMessage) => {
  messages.unshift(message);
  if (messages.length > MAX_MESSAGES) messages.length = MAX_MESSAGES;
  persist();
  for (const listener of listeners) listener(message);
};

export const clearMessages = () => {
  messages.length = 0;
  persist();
};

export const setStatus = (isConnected: boolean, error = "") => {
  connected = isConnected;
  lastError = error;
};

export const readState = () => ({ messages, connected, lastError });
