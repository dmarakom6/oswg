export function isValidUrl(url: string): boolean {
	try {
		const parsed = new URL(url);
		return parsed.protocol === 'http:' || parsed.protocol === 'https:';
	} catch {
		return false;
	}
}

export function isInRange(value: number, min: number, max: number): boolean {
	return Number.isFinite(value) && value >= min && value <= max;
}

export function parseWordsInput(input: string): string[] {
	return input
		.split('\n')
		.map((w) => w.trim())
		.filter((w) => w.length > 0);
}

/** Soft cap for drag & dropped wordlists, to avoid loading huge files into the UI. */
export const MAX_DROP_WORDS = 1_000_000;
export const MAX_DROP_BYTES = 20 * 1024 * 1024; // 20 MB

export function parseWordlistText(text: string): string[] {
	return text
		.split('\n')
		.map((w) => w.trim())
		.filter((w) => w.length > 0);
}

export function formatNumber(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
	return n.toString();
}

export function formatFileSize(bytes: number): string {
	if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
	if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
	return `${bytes} B`;
}
