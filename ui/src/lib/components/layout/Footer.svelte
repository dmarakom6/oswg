<script lang="ts">
	import { onMount } from 'svelte';

	let version = $state('...');

	onMount(async () => {
		try {
			const res = await fetch('/');
			const data = await res.json();
			version = data.version;
		} catch {
			version = '?';
		}
	});
</script>

<footer class="flex items-center justify-between border-t border-border bg-card px-6 py-2 text-xs text-muted-foreground">
	<span>OSWG v{version}</span>
	<span>MIT License</span>
</footer>
