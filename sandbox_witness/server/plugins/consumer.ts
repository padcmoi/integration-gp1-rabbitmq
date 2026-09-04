import { runWitnessConsumer } from "../utils/amqp";

export default defineNitroPlugin(() => {
  void runWitnessConsumer();
});
