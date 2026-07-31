const API_BASE = '';

export class ApiError extends Error {
	constructor(
		public status: number,
		public code: string,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const res = await fetch(`${API_BASE}${path}`, {
		headers: { 'Content-Type': 'application/json', ...init?.headers },
		...init
	});

	if (!res.ok) {
		const body = await res.json().catch(() => ({ detail: res.statusText }));
		throw new ApiError(
			res.status,
			body.code ?? 'unknown',
			body.detail ?? body.error ?? 'Request failed'
		);
	}

	return res.json();
}

export const api = {
	post: <T>(path: string, body: unknown) =>
		request<T>(path, { method: 'POST', body: JSON.stringify(body) }),

	get: <T>(path: string) => request<T>(path),

	download: async (path: string): Promise<{ blob: Blob; filename: string }> => {
		const res = await fetch(`${API_BASE}${path}`);
		if (!res.ok) throw new ApiError(res.status, 'download_error', 'Download failed');
		const blob = await res.blob();
		const disposition = res.headers.get('content-disposition') ?? '';
		const match = disposition.match(/filename=(.+)/);
		const filename = match?.[1] ?? 'oswg_wordlist.txt';
		return { blob, filename };
	}
};
