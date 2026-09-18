<script lang="ts">
	import SegmentedControl from './SegmentedControl.svelte';
	import { endpoints } from '$lib/api/endpoints';
	import { jobsStore } from '$lib/stores/jobs';
	import { connectJobWs } from '$lib/websocket/job-ws';
	import { testTools } from '$lib/stores/capabilities';
	import type { JobListItem, TestRequest } from '$lib/api/types';

	const TOOLS = ['hashcat', 'john', 'hydra', 'medusa', 'ncrack', 'gobuster', 'aircrack-ng'];

	let sourceMode = $state<'recent' | 'paste'>('recent');
	let recentJobs = $state<JobListItem[]>([]);
	let wordlistJobId = $state('');
	let wordlistText = $state('');
	let tool = $state('hashcat');
	let mode = $state('');
	let hashesText = $state('');
	let usersText = $state('');
	let rulesText = $state('');
	let host = $state('');
	let service = $state('');
	let url = $state('');
	let captureText = $state('');
	let submitting = $state(false);

	$effect(() => {
		endpoints.listJobs().then((jobs) => {
			recentJobs = jobs
				.filter((j) => j.type === 'generate' && j.status === 'completed')
				.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
			if (!wordlistJobId && recentJobs.length) wordlistJobId = recentJobs[0].job_id;
		});
	});

	const hasWordlist = $derived(
		sourceMode === 'recent' ? !!wordlistJobId : wordlistText.trim().length > 0
	);
	const toolInstalled = $derived($testTools[tool] ?? false);
	const toolInputsOk = $derived(
		tool === 'hashcat' || tool === 'john'
			? hashesText.trim().length > 0
			: tool === 'hydra' || tool === 'medusa' || tool === 'ncrack'
				? host.trim().length > 0 && service.trim().length > 0 && usersText.trim().length > 0
				: tool === 'gobuster'
					? url.trim().length > 0
					: tool === 'aircrack-ng'
						? captureText.trim().length > 0
						: false
	);
	const canSubmit = $derived(hasWordlist && toolInstalled && toolInputsOk && !submitting);

	function shortLabel(job: JobListItem): string {
		const u = job.url ?? job.job_id;
		return u.length > 48 ? u.slice(0, 47) + '…' : u;
	}

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;
		try {
			const payload: TestRequest = {
				tool,
				...(sourceMode === 'recent'
					? { wordlist_job_id: wordlistJobId }
					: { wordlist_text: wordlistText }),
				...(mode.trim() ? { mode: parseInt(mode, 10) } : {}),
				...(hashesText.trim() ? { hashes_text: hashesText } : {}),
				...(usersText.trim() ? { users_text: usersText } : {}),
				...(rulesText.trim() ? { rules_text: rulesText } : {}),
				...(host.trim() ? { host: host.trim() } : {}),
				...(service.trim() ? { service: service.trim() } : {}),
				...(url.trim() ? { url: url.trim() } : {}),
				...(captureText.trim() ? { capture_text: captureText } : {})
			};
			const response = await endpoints.test(payload);
			jobsStore.upsert({
				job_id: response.job_id,
				type: 'test',
				status: 'pending',
				progress: 0,
				created_at: new Date().toISOString(),
				updated_at: new Date().toISOString(),
				completed_at: null,
				error_message: null,
				result_file: null
			});
			jobsStore.setCurrent('test', response.job_id);
			connectJobWs(response.job_id, (msg) => {
				jobsStore.upsert({
					job_id: msg.job_id,
					status: msg.status,
					progress: msg.progress
				});
			});
		} catch {
			// error is surfaced in the output panel
		} finally {
			submitting = false;
		}
	}
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-6">
	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Wordlist</h2>
		<SegmentedControl
			value={sourceMode}
			onchange={(v) => (sourceMode = v as 'recent' | 'paste')}
			options={[
				{ value: 'recent', label: 'Recent' },
				{ value: 'paste', label: 'Paste' }
			]}
		/>
		{#if sourceMode === 'recent'}
			<div class="space-y-1.5">
				<label for="test-wordlist" class="block text-sm font-medium text-foreground">
					Recent wordlist
				</label>
				<select
					id="test-wordlist"
					value={wordlistJobId}
					onchange={(e) => (wordlistJobId = e.currentTarget.value)}
					class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
				>
					{#if recentJobs.length === 0}
						<option value="">No completed wordlists yet</option>
					{/if}
					{#each recentJobs as job}
						<option value={job.job_id}>{shortLabel(job)}</option>
					{/each}
				</select>
				<p class="text-xs text-muted-foreground">
					Uses the stored wordlist of a recent unexpired Generate job.
				</p>
			</div>
		{:else}
			<textarea
				bind:value={wordlistText}
				placeholder="One word per line"
				rows="6"
				class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
			></textarea>
		{/if}
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Tool</h2>
		<div class="space-y-1.5">
			<label for="test-tool" class="block text-sm font-medium text-foreground">Cracker</label>
			<select
				id="test-tool"
				value={tool}
				onchange={(e) => (tool = e.currentTarget.value)}
				class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:border-primary focus:outline-none"
			>
				{#each TOOLS as t}
					<option value={t} disabled={!($testTools[t] ?? false)}>
						{t}{($testTools[t] ?? false) ? '' : ' (not installed)'}
					</option>
				{/each}
			</select>
			{#if !toolInstalled}
				<p class="text-xs text-muted-foreground">
					Run <span class="font-mono">oswg setup</span> to see how to install {tool}.
				</p>
			{/if}
		</div>

		{#if tool === 'hashcat'}
			<div class="space-y-1.5">
				<label for="test-mode" class="block text-sm font-medium text-foreground">Hash mode</label>
				<input
					id="test-mode"
					type="number"
					value={mode}
					oninput={(e) => (mode = e.currentTarget.value)}
					placeholder="0 (MD5), 1000 (NTLM), 3200 (bcrypt)…"
					class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
				/>
			</div>
		{/if}

		{#if tool === 'hashcat' || tool === 'john'}
			<div class="space-y-1.5">
				<label for="test-hashes" class="block text-sm font-medium text-foreground">Hashes</label>
				<textarea
					id="test-hashes"
					bind:value={hashesText}
					placeholder="One hash per line"
					rows="5"
					class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				></textarea>
			</div>
		{/if}

		{#if tool === 'hashcat' || tool === 'john'}
			<div class="space-y-1.5">
				<label for="test-rules" class="block text-sm font-medium text-foreground">Rules (optional)</label>
				<textarea
					id="test-rules"
					bind:value={rulesText}
					placeholder="Paste cracker rules (one per line)"
					rows="3"
					class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				></textarea>
			</div>
		{/if}

		{#if tool === 'hydra' || tool === 'medusa' || tool === 'ncrack'}
			<div class="grid grid-cols-2 gap-3">
				<div class="space-y-1.5">
					<label for="test-host" class="block text-sm font-medium text-foreground">Host</label>
					<input
						id="test-host"
						value={host}
						oninput={(e) => (host = e.currentTarget.value)}
						placeholder="192.168.1.10"
						class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
					/>
				</div>
				<div class="space-y-1.5">
					<label for="test-service" class="block text-sm font-medium text-foreground">Service</label>
					<input
						id="test-service"
						value={service}
						oninput={(e) => (service = e.currentTarget.value)}
						placeholder="ssh"
						class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
					/>
				</div>
			</div>
			<div class="space-y-1.5">
				<label for="test-users" class="block text-sm font-medium text-foreground">Usernames</label>
				<textarea
					id="test-users"
					bind:value={usersText}
					placeholder="One username per line"
					rows="3"
					class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				></textarea>
			</div>
		{/if}

		{#if tool === 'gobuster'}
			<div class="space-y-1.5">
				<label for="test-url" class="block text-sm font-medium text-foreground">Base URL</label>
				<input
					id="test-url"
					value={url}
					oninput={(e) => (url = e.currentTarget.value)}
					placeholder="http://192.168.1.10"
					class="w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
				/>
			</div>
		{/if}

		{#if tool === 'aircrack-ng'}
			<div class="space-y-1.5">
				<label for="test-capture" class="block text-sm font-medium text-foreground">Capture</label>
				<textarea
					id="test-capture"
					bind:value={captureText}
					placeholder="Paste the capture file contents"
					rows="5"
					class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
				></textarea>
			</div>
		{/if}
	</div>

	<button
		type="submit"
		disabled={!canSubmit}
		class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
	>
		{#if submitting}
			Starting…
		{:else}
			Run Test
		{/if}
	</button>
</form>