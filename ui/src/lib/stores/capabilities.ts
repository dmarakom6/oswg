import { writable } from 'svelte/store';
import { endpoints } from '$lib/api/endpoints';

export const jsAvailable = writable<boolean>(false);

export async function loadJsAvailability() {
	try {
		const info = await endpoints.getInfo();
		jsAvailable.set(info.js_available);
	} catch {
		jsAvailable.set(false);
	}
}