<script lang="ts">
	import NumberStepper from './NumberStepper.svelte';
	import ToggleSwitch from './ToggleSwitch.svelte';
	import { DEFAULTS, LIMITS } from '$lib/constants';
	import { notifications } from '$lib/stores/notifications';

	let {
		value,
		onchange
	}: {
		value: {
			merge_words: string[];
			merge_max: number;
			merge_builtin: boolean;
			merge_rockyou: boolean;
		};
		onchange: (v: {
			merge_words: string[];
			merge_max: number;
			merge_builtin: boolean;
			merge_rockyou: boolean;
		}) => void;
	} = $props();

	let fileNames = $state<string[]>([]);

	function emit() {
		onchange({ ...value });
	}

	async function handleFiles(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const files = Array.from(input.files ?? []);
		if (!files.length) return;

		const words: string[] = [];
		const names: string[] = [];
		for (const file of files) {
			if (!file.name.endsWith('.txt')) {
				notifications.add('error', `Skipped ${file.name} - only .txt files are accepted`);
				continue;
			}
			const text = await file.text();
			words.push(...text.split('\n').map((l) => l.trim()).filter((l) => l.length > 0));
			names.push(file.name);
		}
		if (!words.length) {
			input.value = '';
			return;
		}

		value.merge_words = [...value.merge_words, ...words];
		fileNames = [...fileNames, ...names];
		emit();
		notifications.add('success', `Merged ${words.length} words from ${names.length} file(s)`);
		input.value = '';
	}

	function removeFile(index: number) {
		// Rebuild words by dropping this file's contribution is not tracked per-file,
		// so clearing is handled by removing all uploaded words and toggling presets.
		value.merge_words = [];
		fileNames = fileNames.filter((_, i) => i !== index);
		emit();
	}
</script>

<div class="space-y-3 rounded-md border border-border bg-muted/20 p-3">
	<p class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Merge external wordlists</p>

	<div class="space-y-1.5">
		<label class="cursor-pointer text-xs text-primary hover:text-primary/80">
			Upload .txt wordlist(s)
			<input
				type="file"
				accept=".txt,text/plain"
				multiple
				onchange={handleFiles}
				class="hidden"
			/>
		</label>
		{#if fileNames.length > 0}
			<span class="ml-2 text-xs text-success">✓ {fileNames.length} file(s) uploaded</span>
		{/if}
		{#if fileNames.length > 0}
			<div class="space-y-1">
				{#each fileNames as name, i}
					<div class="flex items-center gap-2 rounded-md border border-border bg-background px-2 py-1">
						<span class="flex-1 truncate font-mono text-xs text-foreground">{name}</span>
						<button
							type="button"
							onclick={() => removeFile(i)}
							class="text-xs text-muted-foreground hover:text-destructive"
							title="Clear uploaded words"
						>✕</button>
					</div>
				{/each}
			</div>
		{/if}
		{#if value.merge_words.length > 0}
			<p class="text-xs text-muted-foreground">
				{value.merge_words.length} words uploaded (mutated like scraped words).
			</p>
		{/if}
	</div>

	<div class="space-y-2">
		<ToggleSwitch checked={value.merge_builtin} onchange={(v) => { value.merge_builtin = v; emit(); }} label="Merge bundled common passwords" />
		<p class="text-xs text-muted-foreground">No system wordlists needed.</p>
	</div>

	<NumberStepper
		value={value.merge_max}
		onchange={(v) => { value.merge_max = v; emit(); }}
		label="Merge cap"
		min={LIMITS.mergeMax.min}
		max={LIMITS.mergeMax.max}
		step={1000}
	/>
</div>
