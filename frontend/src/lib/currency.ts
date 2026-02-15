const CURRENCY_SYMBOLS: Record<string, string> = {
  SGD: "S$",
  MYR: "RM",
  USD: "$",
  EUR: "€",
  GBP: "£",
  JPY: "¥",
  CNY: "¥",
  KRW: "₩",
  THB: "฿",
  IDR: "Rp",
  PHP: "₱",
  VND: "₫",
  INR: "₹",
  AUD: "A$",
  CAD: "C$",
  HKD: "HK$",
  TWD: "NT$",
  NZD: "NZ$",
};

export function getCurrencySymbol(code: string): string {
  return CURRENCY_SYMBOLS[code.toUpperCase()] || code;
}

export const COMMON_CURRENCIES = [
  "SGD", "MYR", "USD", "EUR", "GBP", "JPY", "CNY",
  "KRW", "THB", "IDR", "PHP", "VND", "INR",
  "AUD", "CAD", "HKD", "TWD", "NZD",
];
