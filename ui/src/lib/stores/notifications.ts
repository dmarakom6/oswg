import { writable } from 'svelte/store';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
	id: string;
	type: NotificationType;
	message: string;
	dismissAfter?: number;
}

function createNotificationsStore() {
	const { subscribe, update } = writable<Notification[]>([]);

	return {
		subscribe,
		add(type: NotificationType, message: string, dismissAfter = 5000) {
			const id = crypto.randomUUID();
			const notification: Notification = { id, type, message, dismissAfter };

			update((notifications) => [...notifications, notification]);

			if (dismissAfter > 0) {
				setTimeout(() => {
					update((notifications) => notifications.filter((n) => n.id !== id));
				}, dismissAfter);
			}

			return id;
		},
		dismiss(id: string) {
			update((notifications) => notifications.filter((n) => n.id !== id));
		},
		clear() {
			update(() => []);
		}
	};
}

export const notifications = createNotificationsStore();
