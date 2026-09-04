import { clearMessages } from "../utils/store";

// Empties the local archive only. The queue itself holds no memory of a message
// already read, so there is nothing to ask the broker here.
export default defineEventHandler(() => {
  clearMessages();
  return { ok: true };
});
