import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Safely unwrap list responses whether returned as a flat array or
 * a paginated DRF envelope ({ count, next, previous, results }).
 */
export function unwrapList<T>(res: unknown): T[] {
  if (Array.isArray(res)) return res
  if (
    res &&
    typeof res === 'object' &&
    'results' in res &&
    Array.isArray((res as { results: unknown }).results)
  ) {
    return (res as { results: T[] }).results
  }
  return []
}
