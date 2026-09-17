<script lang="ts">
	import { onMount } from 'svelte';
	import { helpOpen } from '$lib/stores/shortcuts';

	let version = $state('...');

	onMount(async () => {
		try {
			const res = await fetch('/api/v1/info');
			const data = await res.json();
			version = data.version;
		} catch {
			version = '?';
		}
	});
</script>

<footer class="flex items-center justify-between border-t border-border bg-card px-4 py-2 text-xs text-muted-foreground sm:px-6">
	<span>OSWG v{version}</span>
	<div class="flex items-center gap-4">
		<button
			type="button"
			onclick={() => helpOpen.update((v) => !v)}
			class="flex items-center gap-1.5 rounded border border-border bg-muted/40 px-2 py-1 text-muted-foreground transition-colors hover:text-foreground"
			title="Keyboard shortcuts"
		>
			Shortcuts
			<kbd class="rounded bg-background px-1 text-[10px] text-foreground">?</kbd>
		</button>
		<span class="hidden sm:inline">MIT License</span>
	</div>
</footer>
