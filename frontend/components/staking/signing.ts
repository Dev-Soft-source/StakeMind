export function createDemoTxHash(unsignedPayload: Record<string, unknown>): string {
  const serialized = JSON.stringify(unsignedPayload);
  let hash = 0;
  for (let index = 0; index < serialized.length; index += 1) {
    hash = (hash * 31 + serialized.charCodeAt(index)) >>> 0;
  }
  return `0x${hash.toString(16).padStart(16, "0")}`;
}

export function createDemoSignedExtrinsic(unsignedPayload: Record<string, unknown>): string {
  return `demo-signed:${createDemoTxHash(unsignedPayload)}`;
}
