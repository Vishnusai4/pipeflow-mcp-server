/**
 * Normalizes an app slug to match the backend's expected format.
 * Converts to lowercase and replaces spaces and dashes with underscores.
 * 
 * @param slug The app slug to normalize
 * @returns The normalized slug
 */
export function normalizeAppSlug(slug: string): string {
  if (!slug) return '';
  return slug.toLowerCase().replace(/[\s-]/g, '_');
}

/**
 * Validates if a slug is in the correct format.
 * Only allows lowercase letters, numbers, and underscores.
 * 
 * @param slug The slug to validate
 * @returns boolean indicating if the slug is valid
 */
export function isValidAppSlug(slug: string): boolean {
  if (!slug) return false;
  return /^[a-z0-9_]+$/.test(slug);
}
