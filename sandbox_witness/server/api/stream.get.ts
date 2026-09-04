import { createEventStream } from "h3";
import { subscribe } from "../utils/store";

// The page is told as the message is acknowledged, not at its next poll: a beep
// two seconds late is not a beep. Polling stays as the safety net for the list
// itself, this stream only carries the arrival.
export default defineEventHandler((event) => {
  const stream = createEventStream(event);

  const unsubscribe = subscribe((message) => {
    void stream.push(JSON.stringify({ id: message.id, receivedAt: message.receivedAt }));
  });

  stream.onClosed(async () => {
    unsubscribe();
    await stream.close();
  });

  return stream.send();
});
