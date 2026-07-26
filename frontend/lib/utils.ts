import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merges class names safely using clsx and tailwind-merge.
 * Useful for building dynamic styling in reusable UI components.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
