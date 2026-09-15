export type NotificationPermissionState = 'default' | 'granted' | 'denied' | 'unsupported';

export function notificationsSupported(): boolean {
	return (
		typeof window !== 'undefined' &&
		'Notification' in window &&
		window.isSecureContext === true
	);
}

export function notificationPermission(): NotificationPermissionState {
	if (!notificationsSupported()) return 'unsupported';
	return Notification.permission as NotificationPermissionState;
}

export async function requestNotificationPermission(): Promise<NotificationPermissionState> {
	if (!notificationsSupported()) return 'unsupported';
	try {
		return await Notification.requestPermission();
	} catch {
		return 'denied';
	}
}

export function showNotification(title: string, body: string, tag?: string): boolean {
	if (!notificationsSupported()) {
		console.debug('[notify] skipped: unsupported (needs localhost or HTTPS)');
		return false;
	}
	if (Notification.permission !== 'granted') {
		console.debug('[notify] skipped: permission is', Notification.permission);
		return false;
	}
	try {
		const notification = new Notification(title, { body, tag, icon: '/favicon.svg' });
		notification.onclick = () => {
			window.focus();
			notification.close();
		};
		console.debug('[notify] shown:', title);
		return true;
	} catch (error) {
		// Mobile browsers throw a TypeError for the Notification constructor.
		console.debug('[notify] constructor threw:', error);
		return false;
	}
}