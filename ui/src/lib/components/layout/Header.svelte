<script lang="ts">
	import { theme } from '$lib/stores/theme';
	import { browserNotifications } from '$lib/stores/notifications';
	import type { ThemeMode } from '$lib/api/types';

	const options: { value: ThemeMode; label: string; icon: string }[] = [
		{ value: 'system', label: 'System', icon: '◐' },
		{ value: 'light', label: 'Light', icon: '☀' },
		{ value: 'dark', label: 'Dark', icon: '☾' }
	];

	function cycleTheme() {
		const order: ThemeMode[] = ['system', 'light', 'dark'];
		let current: ThemeMode = 'system';
		theme.subscribe((v) => (current = v))();
		const idx = order.indexOf(current);
		theme.set(order[(idx + 1) % order.length]);
	}

	const notify = $derived($browserNotifications);
	const notifySupported = $derived(notify.permission !== 'unsupported');
	const notifyBlocked = $derived(notify.permission === 'denied');

	function toggleNotifications() {
		if (!notifySupported || notifyBlocked) return;
		if (notify.enabled) {
			browserNotifications.disable();
		} else {
			browserNotifications.enable();
		}
	}

	const notifyTitle = $derived(
		!notifySupported
			? 'Browser notifications need localhost or HTTPS'
			: notifyBlocked
				? 'Notifications are blocked in your browser settings'
				: notify.enabled
					? 'Disable browser notifications'
					: 'Notify me when a job finishes'
	);
</script>

<header class="flex items-center justify-between border-b border-border bg-card px-6 py-3">
	<div class="flex items-center gap-3">
		<span class="font-mono text-lg font-semibold text-primary">OSWG</span>
		<span class="hidden text-sm text-muted-foreground sm:inline">Oddly Specific Wordlist Generator</span>
	</div>

	<div class="flex items-center gap-2">
		<button
			type="button"
			onclick={toggleNotifications}
			disabled={!notifySupported || notifyBlocked}
			class="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm transition-colors
				{notify.enabled ? 'text-primary' : 'text-muted-foreground'}
				hover:bg-accent hover:text-accent-foreground disabled:cursor-not-allowed disabled:opacity-40"
			title={notifyTitle}
			aria-pressed={notify.enabled}
			aria-label={notifyTitle}
		>
			<span class="flex h-6 w-6 items-center justify-center">
				{#if notify.enabled}
					<svg viewBox="0 0 24 24" class="h-4 w-4" fill="currentColor" aria-hidden="true">
						<path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z" />
					</svg>
				{:else}
					<svg viewBox="0 0 24 24" class="h-4 w-4" fill="currentColor" aria-hidden="true">
						<path d="M20 18.69L7.84 6.14 5.27 3.49 4 4.76l2.8 2.8v.01c-.52.99-.8 2.16-.8 3.42v5l-2 2v1h13.24l2.52 2.52L20 18.69zM12 22c1.11 0 2-.89 2-2h-4c0 1.11.89 2 2 2zm6-7.32V11c0-3.08-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5S11.5 3.17 11.5 4v.68c-.15.03-.29.08-.42.12L18 14.68z" />
					</svg>
				{/if}
			</span>
			<span class="hidden sm:inline">
				{notify.enabled ? 'On' : 'Off'}
			</span>
		</button>

		<button
			type="button"
			onclick={cycleTheme}
			class="flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
			title="Toggle theme"
		>
			<span class="text-base">
				{#if $theme === 'dark'}
					☾
				{:else if $theme === 'light'}
					☀
				{:else}
					◐
				{/if}
			</span>
			<span class="hidden sm:inline">
				{options.find((o) => o.value === $theme)?.label}
			</span>
		</button>
	</div>
</header>