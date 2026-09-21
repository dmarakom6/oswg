import { writable } from 'svelte/store';

export const templatesVersion = writable(0);

export function bumpTemplates() {
	templatesVersion.update((n) => n + 1);
}