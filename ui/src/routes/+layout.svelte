<script lang="ts">
	import '../routes/layout.css';
	import Header from '$lib/components/layout/Header.svelte';
	import TabBar from '$lib/components/layout/TabBar.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';
	import { theme } from '$lib/stores/theme';
	import { activeTab } from '$lib/stores/tabs';
	import type { ActiveTab } from '$lib/api/types';

	let { children } = $props();

	theme.init();

	function handleKeydown(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
		if (e.key === '1') activeTab.set('generate');
		if (e.key === '2') activeTab.set('scrape');
		if (e.key === '3') activeTab.set('mutate');
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="flex h-screen flex-col">
	<Header />
	<TabBar activeTab={$activeTab} onchange={(t) => activeTab.set(t)} />

	<main class="flex flex-1 overflow-hidden">
		{@render children()}
	</main>

	<Footer />
</div>
