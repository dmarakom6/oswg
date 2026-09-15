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
			<span class="text-base">{notify.enabled ? '🔔' : '🔕'}</span>
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