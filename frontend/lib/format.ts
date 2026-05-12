export function formatRao(amount: number): string {
  const tao = amount / 1_000_000_000;
  if (tao >= 1) {
    return `${tao.toFixed(2)} TAO`;
  }
  if (amount >= 1_000_000) {
    return `${(amount / 1_000_000).toFixed(2)} mRao`;
  }
  return `${amount.toLocaleString()} Rao`;
}
