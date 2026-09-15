<script lang="ts">
	import '../routes/layout.css';
	import Header from '$lib/components/layout/Header.svelte';
	import TabBar from '$lib/components/layout/TabBar.svelte';
	import Footer from '$lib/components/layout/Footer.svelte';
	import ShortcutsDialog from '$lib/components/layout/ShortcutsDialog.svelte';
	import { theme } from '$lib/stores/theme';
	import { activeTab } from '$lib/stores/tabs';
	import { focusUrlSignal, helpOpen, runSignal } from '$lib/stores/shortcuts';
	import { isMod, isTyping } from '$lib/shortcuts';
	import { loadJsAvailability } from '$lib/stores/capabilities';
	import { jobsStore } from '$lib/stores/jobs';
	import { browserNotifications } from '$lib/stores/notifications';
	import { get } from 'svelte/store';
	import type { ActiveTab } from '$lib/api/types';

	let { children } = $props();

	theme.init();
	loadJsAvailability();

	// Notify (only while the tab is hidden) as jobs finish or fail.
	$effect(() => {
		const lastStatus = new Map<string, string>();
		const notified = new Set<string>();
		let originalTitle: string | null = null;

		function fire(job: { job_id: string; status: string; error_message?: string | null }) {
			notified.add(job.job_id);
			const label = job.status === 'completed' ? '● Done' : '● Failed';
			if (originalTitle === null) originalTitle = document.title;
			document.title = `${label} — OSWG`;
			browserNotifications.notify(
				job.status === 'completed' ? 'Wordlist ready' : 'Job failed',
				job.status === 'completed'
					? 'Your wordlist finished generating.'
					: (job.error_message ?? 'The job failed.'),
				job.job_id
			);
		}

		const terminal = (status?: string) => status === 'completed' || status === 'failed';

		const unsub = jobsStore.subscribe((jobs) => {
			for (const job of jobs.values()) {
				const previous = lastStatus.get(job.job_id);
				lastStatus.set(job.job_id, job.status);
				if (previous !== 'pending' && previous !== 'processing') continue;
				if (!terminal(job.status)) continue;
				if (!document.hidden) {
					console.debug('[notify] finished while visible:', job.job_id);
					continue;
				}
				fire(job);
			}
		});

		// Catch up: if a job finished while the tab was visible, notify when the
		// user switches away. Restore the title when they come back.
		const onVisibility = () => {
			if (!document.hidden) {
				if (originalTitle !== null) {
					document.title = originalTitle;
					originalTitle = null;
				}
				return;
			}
			for (const job of get(jobsStore).values()) {
				if (terminal(job.status) && !notified.has(job.job_id)) fire(job);
			}
		};
		document.addEventListener('visibilitychange', onVisibility);

		return () => {
			unsub();
			document.removeEventListener('visibilitychange', onVisibility);
		};
	});

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

<svelte:head>
	<title>OSWG</title>
</svelte:head>

<div class="flex h-screen flex-col">
	<Header />
	<TabBar activeTab={$activeTab} onchange={(t) => activeTab.set(t)} />

	<main class="flex flex-1 overflow-hidden">
		{@render children()}
	</main>

	<Footer />
</div>

<ShortcutsDialog />
