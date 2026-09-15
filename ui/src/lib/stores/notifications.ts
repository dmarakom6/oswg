import { browser } from '$app/environment';
import { get, writable } from 'svelte/store';
import {
	notificationPermission,
	notificationsSupported,
	requestNotificationPermission,
	showNotification,
	type NotificationPermissionState
} from '$lib/browser-notifications';

interface NotificationState {
	enabled: boolean;
	permission: NotificationPermissionState;
}

function createNotificationStore() {
	const supported = browser && notificationsSupported();
	const permission = supported ? notificationPermission() : 'unsupported';
	const enabled =
		supported && permission === 'granted' && localStorage.getItem('oswg-notify') === 'on';

	const store = writable<NotificationState>({ enabled, permission });

	return {
		subscribe: store.subscribe,
		async enable() {
			if (!supported) return;
			const result = await requestNotificationPermission();
			const on = result === 'granted';
			if (browser && on) localStorage.setItem('oswg-notify', 'on');
			store.set({ enabled: on, permission: result });
		},
		disable() {
			if (browser) localStorage.setItem('oswg-notify', 'off');
			store.set({
				enabled: false,
				permission: supported ? notificationPermission() : 'unsupported'
			});
		},
		notify(title: string, body: string, tag?: string) {
			if (get(store).enabled) {
				showNotification(title, body, tag);
			} else {
				console.debug('[notify] skipped: notifications are off');
			}
		}
	};
}

export const browserNotifications = createNotificationStore();