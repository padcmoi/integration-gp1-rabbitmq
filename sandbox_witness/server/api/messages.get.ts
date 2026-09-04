import { WATCHED_QUEUE, env } from "../utils/env";
import { readState } from "../utils/store";

export default defineEventHandler(() => ({
  queue: WATCHED_QUEUE,
  host: env.RABBITMQ_HOST,
  user: env.RABBITMQ_USER,
  ...readState(),
}));
