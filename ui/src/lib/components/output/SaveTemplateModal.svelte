<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import { bumpTemplates } from '$lib/stores/templates';

	let {
		jobId,
		jobType,
		onclose
	}: {
		jobId: string;
		jobType: 'generate' | 'scrape';
		onclose: () => void;
	} = $props();

	let name = $state('');
	let saving = $state(false);
	let error = $state('');
	let saved = $state(false);

	async function save() {
		if (!name.trim()) return;
		saving = true;
		error = '';
		try {
			await endpoints.saveTemplate({ name: name.trim(), type: jobType, from_job: jobId });
			saved = true;
			bumpTemplates();
			setTimeout(onclose, 700);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save template';
			saving = false;
		}
	}
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'Escape') onclose(); }} />

<div
	class="fixed inset-0 z-50 flex items-center justify-center bg-background/80 p-4"
	role="presentation"
	onclick={(e) => {
		if (e.target === e.currentTarget) onclose();
	}}
>
	<div
		class="w-full max-w-md rounded-lg border border-border bg-background p-5 shadow-xl"
		role="dialog"
		tabindex="-1"
		aria-modal="true"
		aria-label="Save template"
	>
		{#if saved}
			<p class="text-sm text-success">Saved template &quot;{name}&quot;.</p>
		{:else}
			<h2 class="mb-3 text-base font-semibold text-foreground">Save template</h2>
			<input
				value={name}
				oninput={(e) => (name = e.currentTarget.value)}
				placeholder="Template name"
				class="mb-3 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
			/>
			{#if error}
				<p class="mb-3 text-sm text-destructive">{error}</p>
			{/if}
			<div class="flex justify-end gap-2">
				<button
					type="button"
					onclick={onclose}
					class="rounded-md border border-border px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-accent"
				>
					Cancel
				</button>
				<button
					type="button"
					onclick={save}
					disabled={!name.trim() || saving}
					class="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
				>
					{saving ? 'Saving…' : 'Save'}
				</button>
			</div>
		{/if}
	</div>
</div>