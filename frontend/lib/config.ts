const DEFAULT_API_ORIGIN = "http://localhost:8000";

function normalizeOrigin(origin: string): string {
  return origin.replace(/\/$/, "");
}

export function getApiOrigin(): string {
  return normalizeOrigin(process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_ORIGIN);
}

export function getApiBase(): string {
  return `${getApiOrigin()}/api`;
}

export function getWsBase(): string {
  const origin = getApiOrigin();
  if (origin.startsWith("https://")) {
    return origin.replace("https://", "wss://");
  }
  if (origin.startsWith("http://")) {
    return origin.replace("http://", "ws://");
  }
  return `ws://${origin}`;
}
