import amqp from "amqplib";
import { AMQP_URL, RETRY_DELAY_MS, WATCHED_QUEUE } from "./env";
import { addMessage, setStatus } from "./store";

const decode = (raw: string) => {
  try {
    return JSON.parse(raw) satisfies unknown;
  } catch {
    // Not JSON: shown as it arrived rather than hidden behind a parse error.
    return raw;
  }
};

// One long-lived consumer on the queue of this namespace, reconnecting on its
// own. Nothing is ever published from here: this app is a pair of eyes.
//
// A consumed message is acknowledged and therefore leaves the queue for good.
// That is what a consumer does, and it is the only way to read a body through
// AMQP; the archive on disk is what makes it re-readable afterwards.
export const runWitnessConsumer = async () => {
  for (;;) {
    try {
      const connection = await amqp.connect(AMQP_URL);
      const channel = await connection.createChannel();
      // Ours to declare, so a queue deleted on the broker comes back at the
      // next start instead of leaving the app silently watching nothing.
      await channel.assertQueue(WATCHED_QUEUE, { durable: true });
      await channel.prefetch(1);
      await channel.consume(WATCHED_QUEUE, (message) => {
        if (message === null) return;
        const raw = message.content.toString();
        addMessage({
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          body: decode(raw),
          correlationId: message.properties.correlationId ?? undefined,
          replyTo: message.properties.replyTo ?? undefined,
          contentType: message.properties.contentType ?? undefined,
          bytes: message.content.byteLength,
          receivedAt: new Date().toISOString(),
        });
        channel.ack(message);
      });
      setStatus(true);
      console.info(`[witness] consuming ${WATCHED_QUEUE}`);
      await new Promise((resolve) => {
        connection.on("close", resolve);
        connection.on("error", resolve);
      });
      setStatus(false, "connexion fermee");
    } catch (error) {
      setStatus(false, error instanceof Error ? error.message : String(error));
      console.warn(`[witness] ${error instanceof Error ? error.message : String(error)}`);
    }
    console.warn(`[witness] reconnecting ${WATCHED_QUEUE} in ${RETRY_DELAY_MS}ms`);
    await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY_MS));
  }
};
