<script lang="ts">
	import '../routes/layout.css';
	import Header from '$lib/components/layout/Header.svelte';
	import TabBar from '$lib/components/layout/TabBar.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';
	import ShortcutsDialog from '$lib/components/layout/ShortcutsDialog.svelte';
	import Toaster from '$lib/components/layout/Toaster.svelte';
	import { theme } from '$lib/stores/theme';
	import { activeTab } from '$lib/stores/tabs';
	import { focusUrlSignal, helpOpen, runSignal } from '$lib/stores/shortcuts';
	import { isMod, isTyping } from '$lib/shortcuts';
	import { loadJsAvailability } from '$lib/stores/capabilities';
	import type { ActiveTab } from '$lib/api/types';

	let { children } = $props();

	theme.init();
	loadJsAvailability();

	const TAB_KEYS: Record<string, ActiveTab> = {
		'1': 'generate',
		'2': 'scrape',
		'3': 'mutate'
	};

	function handleKeydown(e: KeyboardEvent) {
		// Run works from anywhere, including textareas.
		if (isMod(e) && e.key === 'Enter') {
			e.preventDefault();
			runSignal.update((n) => n + 1);
			return;
		}

		// Everything below must not fire while the user is typing.
		if (isTyping(e)) return;

		if (e.key in TAB_KEYS) {
			activeTab.set(TAB_KEYS[e.key]);
			return;
		}

		if (e.key === '/') {
			e.preventDefault();
			focusUrlSignal.update((n) => n + 1);
			return;
		}

		if (e.key === '?') {
			e.preventDefault();
			helpOpen.update((v) => !v);
			return;
		}

		if (e.key === 'Escape' && $helpOpen) {
			helpOpen.set(false);
		}
	}
function handleWindowDragOver(e: DragEvent) {
		e.preventDefault();
	}

	function handleWindowDrop(e: DragEvent) {
		e.preventDefault();
	}
</script>

<svelte:window onkeydown={handleKeydown} ondragover={handleWindowDragOver} ondrop={handleWindowDrop} />

<div class="flex h-screen flex-col">
	<Header />
	<TabBar activeTab={$activeTab} onchange={(t) => activeTab.set(t)} />

	<main class="flex flex-1 overflow-hidden">
		{@render children()}
	</main>

	<Footer />
</div>

<ShortcutsDialog />
<Toaster />
