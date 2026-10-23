/** Date-only parsing never uses the browser's timezone or repairs invalid dates. */
export function isISODate(value: unknown): value is string {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (year < 1 || month < 1 || month > 12 || day < 1) return false;
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  return day <= [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
}

const months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export function formatDocumentDate(value: string | null): string {
  if (!isISODate(value)) return "Date unverified";
  const [year, month, day] = value.split("-").map(Number);
  return `${months[month - 1]} ${day}, ${year}`;
}

export const formatDocumentDatesInText = (text: string) => text.replace(/\b\d{4}-\d{2}-\d{2}\b/g, value => isISODate(value) ? formatDocumentDate(value) : value);
