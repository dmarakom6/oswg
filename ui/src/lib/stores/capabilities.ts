import { writable } from 'svelte/store';
import { endpoints } from '$lib/api/endpoints';

export const jsAvailable = writable<boolean>(false);
export const testTools = writable<Record<string, boolean>>({});

export async function loadJsAvailability() {
	try {
		const info = await endpoints.getInfo();
		jsAvailable.set(info.js_available);
		testTools.set(info.test_tools ?? {});
	} catch {
		jsAvailable.set(false);
		testTools.set({});
	}
}