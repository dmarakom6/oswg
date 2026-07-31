import { browser } from '$app/environment';
import { writable } from 'svelte/store';
import type { ThemeMode } from '$lib/api/types';

function createThemeStore() {
	const initial: ThemeMode =
		(browser && (localStorage.getItem('oswg-theme') as ThemeMode)) || 'system';

	const { subscribe, set } = writable<ThemeMode>(initial);

	function apply(mode: ThemeMode) {
		if (!browser) return;
		const root = document.documentElement;
		const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

		if (mode === 'dark' || (mode === 'system' && systemDark)) {
			root.classList.add('dark');
		} else {
			root.classList.remove('dark');
		}
	}

	return {
		subscribe,
		set(mode: ThemeMode) {
			if (browser) localStorage.setItem('oswg-theme', mode);
			apply(mode);
			set(mode);
		},
		init() {
			if (!browser) return;
			const stored = (localStorage.getItem('oswg-theme') as ThemeMode) || 'system';
			apply(stored);

			window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
				let current: ThemeMode = 'system';
				subscribe((v) => (current = v))();
				if (current === 'system') apply('system');
			});
		}
	};
}

export const theme = createThemeStore();
