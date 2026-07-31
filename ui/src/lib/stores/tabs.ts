import { writable } from 'svelte/store';
import type { ActiveTab } from '$lib/api/types';

function createTabStore() {
	const { subscribe, set } = writable<ActiveTab>('generate');

	return {
		subscribe,
		set,
		next(current: ActiveTab): ActiveTab {
			const order: ActiveTab[] = ['generate', 'scrape', 'mutate'];
			const idx = order.indexOf(current);
			const nextTab = order[(idx + 1) % order.length];
			set(nextTab);
			return nextTab;
		}
	};
}

export const activeTab = createTabStore();
