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
	if (!notificationsSupported() || Notification.permission !== 'granted') return false;
	try {
		const notification = new Notification(title, { body, tag, icon: '/favicon.svg' });
		notification.onclick = () => {
			window.focus();
			notification.close();
		};
		return true;
	} catch {
		// Mobile browsers throw a TypeError for the Notification constructor.
		return false;
	}
}