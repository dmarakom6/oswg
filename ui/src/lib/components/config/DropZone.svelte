<script lang="ts">
	import { MAX_DROP_BYTES, MAX_DROP_WORDS, parseWordlistText } from '$lib/utils/validators';

	let {
		onFiles,
		multiple = false,
		accept = '.txt,text/plain',
		label = 'Drop .txt wordlist here or click to browse',
		compact = false
	}: {
		/** Called with the validated, parsed word lists (one array per file). */
		onFiles: (files: { name: string; words: string[] }[]) => void;
		multiple?: boolean;
		accept?: string;
		label?: string;
		compact?: boolean;
	} = $props();

	let dragActive = $state(false);
	let inputRef = $state<HTMLInputElement | null>(null);

	async function handleData(files: File[]) {
		if (!files.length) return;

		const results: { name: string; words: string[] }[] = [];
		for (const file of files) {
			if (!file.name.toLowerCase().endsWith('.txt')) continue;
			if (file.size > MAX_DROP_BYTES) continue;
			const words = parseWordlistText(await file.text());
			if (words.length > MAX_DROP_WORDS) continue;
			results.push({ name: file.name, words });
		}

		if (results.length) onFiles(results);
	}

	async function handleInput(e: Event) {
		const input = e.currentTarget as HTMLInputElement;
		const files = Array.from(input.files ?? []);
		input.value = '';
		await handleData(files);
	}

	function onDragOver(e: DragEvent) {
		e.preventDefault();
		dragActive = true;
	}

	function onDragLeave(e: DragEvent) {
		if (e.target !== e.currentTarget) return;
		dragActive = false;
	}

	function onDrop(e: DragEvent) {
		e.preventDefault();
		dragActive = false;
		handleData(Array.from(e.dataTransfer?.files ?? []));
	}

	function onKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			inputRef?.click();
		}
	}
</script>

<div
	class="rounded-md border-2 border-dashed p-3 transition-colors
		{dragActive ? 'border-primary bg-primary/10' : 'border-border bg-muted/20 hover:border-primary/50'}"
	role="button"
	tabindex="0"
	aria-label={label}
	ondragover={onDragOver}
	ondragenter={onDragOver}
	ondragleave={onDragLeave}
	ondrop={onDrop}
	onkeydown={onKeyDown}
>
	<div class="{compact ? 'flex items-center justify-between gap-2' : 'space-y-2'}">
		<label
			for="drop-zone-file"
			class="cursor-pointer text-xs font-medium text-primary hover:text-primary/80"
		>
			{dragActive ? 'Drop to upload…' : label}
		</label>

		<input
			bind:this={inputRef}
			id="drop-zone-file"
			type="file"
			accept={accept}
			multiple={multiple}
			onchange={handleInput}
			class="hidden"
		/>
	</div>
</div>
