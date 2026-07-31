<script lang="ts">
	import ToggleSwitch from './ToggleSwitch.svelte';
	import SegmentedControl from './SegmentedControl.svelte';
	import { DEFAULTS } from '$lib/constants';
	import { parseWordsInput } from '$lib/utils/validators';
	import { endpoints } from '$lib/api/endpoints';
	import { notifications } from '$lib/stores/notifications';

	let { onResult }: { onResult: (result: { words: string[]; count: number; source_count: number }) => void } = $props();

	let wordsInput = $state('');
	let enableLeet = $state(DEFAULTS.enableLeet);
	let enableNumbers = $state(DEFAULTS.enableNumbers);
	let enableSpecial = $state(DEFAULTS.enableSpecial);
	let leetLevel = $state<1 | 2>(DEFAULTS.leetLevel);
	let submitting = $state(false);
	let fileName = $state<string | null>(null);

	let words = $derived(parseWordsInput(wordsInput));
	let uniqueWords = $derived([...new Set(words)]);
	let canSubmit = $derived(uniqueWords.length > 0 && !submitting);

	async function handleFileUpload(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;

		if (!file.name.endsWith('.txt')) {
			notifications.add('error', 'Only .txt files are accepted');
			input.value = '';
			return;
		}

		const text = await file.text();
		const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);
		const deduped = [...new Set(lines)];
		wordsInput = deduped.join('\n');
		fileName = file.name;
		notifications.add('success', `Loaded ${deduped.length} unique words from ${file.name}`);
		input.value = '';
	}

	function clearFile() {
		fileName = null;
	}

	async function handleSubmit() {
		if (!canSubmit) return;
		submitting = true;

		try {
			const result = await endpoints.mutate({
				words: uniqueWords,
				enable_leet: enableLeet,
				enable_numbers: enableNumbers,
				enable_special: enableSpecial,
				leet_level: leetLevel
			});

			onResult(result);
			notifications.add('success', `Generated ${result.count} mutations`);
		} catch (err) {
			notifications.add('error', err instanceof Error ? err.message : 'Mutation failed');
		} finally {
			submitting = false;
		}
	}
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-6">
	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Input</h2>
		<div class="space-y-1.5">
			<label for="words-input" class="block text-sm font-medium text-foreground">
				Words (one per line)
			</label>
			<textarea
				id="words-input"
				bind:value={wordsInput}
				placeholder="password&#10;admin&#10;login"
				rows="8"
				class="w-full resize-y rounded-md border border-border bg-background px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
			></textarea>
			<div class="flex items-center justify-between gap-2">
				<p class="text-xs text-muted-foreground">
					{words.length} words · {uniqueWords.length} unique
				</p>
				<label class="cursor-pointer text-xs text-primary hover:text-primary/80">
					Upload .txt
					<input
						type="file"
						accept=".txt,text/plain"
						onchange={handleFileUpload}
						class="hidden"
					/>
				</label>
			</div>
			{#if fileName}
				<div class="flex items-center gap-2 rounded-md border border-border bg-muted/30 px-2 py-1">
					<span class="flex-1 truncate text-xs text-muted-foreground">📄 {fileName}</span>
					<button
						type="button"
						onclick={clearFile}
						class="text-xs text-muted-foreground hover:text-foreground"
					>
						✕
					</button>
				</div>
			{/if}
		</div>
	</div>

	<div class="space-y-4">
		<h2 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Mutations</h2>
		<div class="space-y-3">
			<ToggleSwitch checked={enableLeet} onchange={(v) => (enableLeet = v)} label="L33t speak" />
			{#if enableLeet}
				<div class="ml-12 space-y-1.5">
					<SegmentedControl
						value={leetLevel}
						onchange={(v) => (leetLevel = v as 1 | 2)}
						options={[{ value: 1, label: 'Basic' }, { value: 2, label: 'Advanced' }]}
					/>
					{#if leetLevel === 2}
						<p class="text-xs text-muted-foreground">
							Advanced applies multiple l33t substitutions per word (e.g. <span class="font-mono">password</span> → <span class="font-mono">p@$$w0rd</span>, <span class="font-mono">p455w0r!</span>), generating more variations.
						</p>
					{/if}
				</div>
			{/if}
			<ToggleSwitch checked={enableNumbers} onchange={(v) => (enableNumbers = v)} label="Numbers" />
			<ToggleSwitch checked={enableSpecial} onchange={(v) => (enableSpecial = v)} label="Special chars" />
		</div>
	</div>

	<button
		type="submit"
		disabled={!canSubmit}
		class="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
	>
		{#if submitting}
			<span class="flex items-center justify-center gap-2">
				<span class="h-4 w-4 animate-spin rounded-full border-2 border-primary-foreground border-t-transparent"></span>
				Mutating...
			</span>
		{:else}
			Mutate Words
		{/if}
	</button>
</form>
