import { readFileSync } from "node:fs";
import { join } from "node:path";

const values: Record<string, string> = {};

for (const line of readFileSync(join(process.cwd(), ".env"), "utf8").split("\n")) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
  const index = trimmed.indexOf("=");
  values[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim();
}

export const env = values;
// The only queue this app looks at, derived from the namespace like everywhere
// else on the bus. It watches, it never sends.
export const WATCHED_QUEUE = `${values.RABBITMQ_NAMESPACE}.queue`;
export const RETRY_DELAY_MS = Number(values.RABBITMQ_UNKNOWN_TYPE_RETRY_DELAY_MS ?? "3000");
export const AMQP_URL =
  `${values.RABBITMQ_PROTOCOL}://${encodeURIComponent(values.RABBITMQ_USER ?? "")}:` +
  `${encodeURIComponent(values.RABBITMQ_PASSWORD ?? "")}@${values.RABBITMQ_HOST}:${values.RABBITMQ_PORT}` +
  `/${encodeURIComponent(values.RABBITMQ_VHOST ?? "/")}?heartbeat=${values.RABBITMQ_HEARTBEAT ?? "30"}`;
