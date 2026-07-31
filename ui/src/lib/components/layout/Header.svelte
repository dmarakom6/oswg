<script lang="ts">
	import { theme } from '$lib/stores/theme';
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
</script>

<header class="flex items-center justify-between border-b border-border bg-card px-6 py-3">
	<div class="flex items-center gap-3">
		<span class="font-mono text-lg font-semibold text-primary">OSWG</span>
		<span class="hidden text-sm text-muted-foreground sm:inline">Oddly Specific Wordlist Generator</span>
	</div>

	<button
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
</header>
