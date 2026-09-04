<script setup lang="ts">
interface WitnessMessage {
  id: string;
  body: unknown;
  correlationId?: string;
  replyTo?: string;
  contentType?: string;
  bytes: number;
  receivedAt: string;
}

interface State {
  queue: string;
  host: string;
  user: string;
  messages: WitnessMessage[];
  connected: boolean;
  lastError: string;
}

const { data, refresh } = await useFetch<State>("/api/messages");

const pretty = (value: unknown) => (typeof value === "string" ? value : JSON.stringify(value, null, 2));

// A beep on arrival, synthesised rather than loaded: no asset to ship, and it
// works offline.
const sound = ref(true);
// A browser refuses to play a sound before the page has been interacted with,
// and creating the context earlier only produces a suspended one. So the first
// click anywhere on the page opens it, which is the gesture the policy asks
// for, and nothing else has to be done to hear the next message.
const unlocked = ref(false);
const GESTURES = ["pointerdown", "keydown", "touchstart"] as const;
let audio: AudioContext | undefined;

const unlock = async () => {
  audio ??= new AudioContext();
  if (audio.state !== "running") await audio.resume();
  const running = audio.state === "running";
  // The confirmation beep is the point of arming: it says out loud that the
  // next message will be heard, instead of leaving it to be discovered later.
  if (running && !unlocked.value) {
    unlocked.value = true;
    beep();
  }
  return running;
};

// A sine, the softest timbre there is: the loudness comes from the amplitude,
// not from the harmonics of a square, which is what turns a beep into a buzzer.
const pulse = (at: number, frequency: number, seconds: number) => {
  if (!audio) return;
  const oscillator = audio.createOscillator();
  const gain = audio.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(frequency, at);
  // Ramped up and down rather than switched, which would click.
  gain.gain.setValueAtTime(0.0001, at);
  gain.gain.exponentialRampToValueAtTime(0.12, at + 0.02);
  gain.gain.exponentialRampToValueAtTime(0.0001, at + seconds);
  oscillator.connect(gain).connect(audio.destination);
  oscillator.start(at);
  oscillator.stop(at + seconds + 0.01);
};

const beep = () => {
  if (!sound.value || !audio || audio.state !== "running") return;
  pulse(audio.currentTime, 880, 0.14);
};

const toggleSound = async () => {
  sound.value = !sound.value;
  if (!sound.value) return;
  await unlock();
  beep();
};

let timer: ReturnType<typeof setInterval> | undefined;
let stream: EventSource | undefined;

onMounted(() => {
  // The list still refreshes on its own, as the safety net if the stream drops.
  timer = setInterval(() => void refresh(), 2000);

  // Tried straight away, since a reload sometimes carries the permission over,
  // then retried on every interaction until the context actually runs. Not
  // `once`: a gesture the browser judges insufficient would consume the only
  // listener and leave the page mute for good.
  const arm = () => {
    void unlock().then((running) => {
      if (!running) return;
      for (const type of GESTURES) window.removeEventListener(type, arm);
    });
  };
  void unlock();
  for (const type of GESTURES) window.addEventListener(type, arm);

  // Pushed by the server the instant the message is acknowledged: the beep is
  // heard when it lands, not up to two seconds later.
  stream = new EventSource("/api/stream");
  stream.onmessage = () => {
    beep();
    void refresh();
  };
});

onUnmounted(() => {
  clearInterval(timer);
  stream?.close();
});

const purging = ref(false);
const purge = async () => {
  purging.value = true;
  try {
    await $fetch("/api/messages", { method: "DELETE" });
    await refresh();
  } finally {
    purging.value = false;
  }
};

// Opened by default so the newest message is readable without a click, closed
// for the rest: a folder announcement carries 366 columns.
const opened = ref<Record<string, boolean>>({});
const isOpen = (message: WitnessMessage, index: number) => opened.value[message.id] ?? index === 0;
const toggle = (message: WitnessMessage, index: number) => {
  opened.value[message.id] = !isOpen(message, index);
};
</script>

<template>
  <UContainer class="py-6 space-y-6 max-w-5xl">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div class="min-w-0">
        <h1 class="text-xl font-semibold">Témoin de queue</h1>
        <p class="font-mono text-sm text-muted truncate">{{ data?.queue }}</p>
      </div>
      <div class="flex items-center gap-2">
        <UBadge :color="data?.connected ? 'success' : 'error'" variant="subtle">
          {{ data?.connected ? "connecté" : "déconnecté" }}
        </UBadge>
        <UBadge color="neutral" variant="subtle">{{ data?.messages.length ?? 0 }} message(s)</UBadge>
        <UButton
          variant="ghost"
          :color="sound ? 'primary' : 'neutral'"
          size="xs"
          :icon="sound ? 'i-lucide-volume-2' : 'i-lucide-volume-x'"
          @click="toggleSound"
        >
          {{ sound ? "Bip activé" : "Bip coupé" }}
        </UButton>
        <UButton
          v-if="data?.messages.length"
          variant="ghost"
          color="error"
          size="xs"
          icon="i-lucide-trash-2"
          :loading="purging"
          @click="purge"
        >
          Purger
        </UButton>
      </div>
    </div>

    <UCard>
      <div class="grid gap-2 sm:grid-cols-3 text-sm">
        <div class="min-w-0">
          <p class="text-muted">Broker</p>
          <p class="font-mono truncate">{{ data?.host }}</p>
        </div>
        <div class="min-w-0">
          <p class="text-muted">Compte</p>
          <p class="font-mono truncate">{{ data?.user }}</p>
        </div>
        <div class="min-w-0">
          <p class="text-muted">Queue écoutée</p>
          <p class="font-mono truncate">{{ data?.queue }}</p>
        </div>
      </div>
      <p v-if="data?.lastError" class="text-sm text-error mt-3">{{ data.lastError }}</p>
    </UCard>

    <UCard>
      <template #header>
        <h2 class="font-medium">Ce que la queue a reçu</h2>
      </template>

      <div v-if="!data?.messages.length" class="text-sm text-muted">
        Rien pour l'instant. Cette app consomme
        <span class="font-mono">{{ data?.queue }}</span> et affiche chaque message dès qu'il arrive.
      </div>

      <div v-else class="space-y-3">
        <div v-for="(message, index) in data.messages" :key="message.id" class="border border-default rounded-md">
          <button
            class="w-full flex items-center justify-between gap-2 p-3 text-left cursor-pointer"
            @click="toggle(message, index)"
          >
            <div class="flex items-baseline gap-2 flex-wrap min-w-0">
              <span class="text-sm font-medium">{{ new Date(message.receivedAt).toLocaleString() }}</span>
              <span class="font-mono text-xs text-muted truncate">{{ message.correlationId ?? "sans correlationId" }}</span>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <UBadge color="neutral" variant="subtle">{{ message.bytes }} o</UBadge>
              <UIcon :name="isOpen(message, index) ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'" />
            </div>
          </button>
          <div v-if="isOpen(message, index)" class="px-3 pb-3 space-y-2">
            <div v-if="message.replyTo" class="text-xs text-muted font-mono">replyTo: {{ message.replyTo }}</div>
            <pre class="text-xs bg-elevated rounded-md p-3 overflow-x-auto">{{ pretty(message.body) }}</pre>
          </div>
        </div>
      </div>
    </UCard>
  </UContainer>
</template>
