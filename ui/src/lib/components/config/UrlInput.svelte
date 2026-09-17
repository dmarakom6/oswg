<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';

	let {
		value,
		onchange,
		error,
		placeholder = 'https://example.com',
		focusSignal = 0
	}: {
		value: string;
		onchange: (val: string) => void;
		error?: string;
		placeholder?: string;
		/** Increment to ask this input to focus itself. */
		focusSignal?: number;
	} = $props();

	const PROTOCOLS = ['http://', 'https://'];
	const PROTOCOL_RE = /^https?:\/\//i;

	let protocol = $state('');
	let rest = $state('');
	let lastEmitted = $state('');
	let inputRef = $state<HTMLInputElement | null>(null);

	let suggestions = $state<string[]>([]);
	let open = $state(false);
	let highlight = $state(-1);
	let debounceTimer: ReturnType<typeof setTimeout> | null = null;
	let requestSeq = 0;
	let rootRef = $state<HTMLDivElement | null>(null);

	$effect(() => {
		if (focusSignal > 0) {
			inputRef?.focus();
		}
	});

	$effect(() => {
		const root = rootRef;
		if (!root) return;
		const onDown = (e: PointerEvent) => {
			const target = e.target as Node;
			if (!root.contains(target)) open = false;
		};
		document.addEventListener('pointerdown', onDown);
		return () => document.removeEventListener('pointerdown', onDown);
	});

	function splitValue(v: string) {
		const m = PROTOCOL_RE.exec(v);
		if (m) {
			protocol = m[0].toLowerCase();
			rest = v.slice(m[0].length);
		} else {
			protocol = '';
			rest = v;
		}
	}

	function isAllowedProtocolText(text: string): boolean {
		if (PROTOCOL_RE.test(text)) return true;
		return PROTOCOLS.some((p) => p.startsWith(text.toLowerCase()));
	}

	function emit(full: string) {
		lastEmitted = full;
		onchange(full);
	}

	function handlePlainInput(newText: string) {
		if (!isAllowedProtocolText(newText)) return;
		const m = PROTOCOL_RE.exec(newText);
		if (m) {
			protocol = m[0].toLowerCase();
			rest = newText.slice(m[0].length);
			emit(protocol + rest);
		} else {
			rest = newText;
			emit(newText);
		}
	}

	function handleRestInput(newText: string) {
		rest = newText;
		emit(protocol + rest);
	}

	function releaseProtocol() {
		if (!protocol) return;
		rest = protocol;
		protocol = '';
		emit(rest);
	}

	const currentInput = $derived(protocol + rest);

	async function fetchSuggestions(q: string) {
		const seq = ++requestSeq;
		try {
			const res = await endpoints.getUrlHistory(q, 10);
			if (seq !== requestSeq) return;
			suggestions = res.urls.map((u) => u.url).filter((u) => u !== currentInput);
			open = suggestions.length > 0;
			highlight = -1;
		} catch {
			if (seq !== requestSeq) return;
			suggestions = [];
			open = false;
		}
	}

	function scheduleFetch() {
		if (debounceTimer) clearTimeout(debounceTimer);
		debounceTimer = setTimeout(() => fetchSuggestions(currentInput), 200);
	}

	function handleFocus() {
		fetchSuggestions(currentInput);
	}

	function selectSuggestion(url: string) {
		splitValue(url);
		lastEmitted = url;
		onchange(url);
		open = false;
		highlight = -1;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (protocol && rest === '' && (e.key === 'Backspace' || e.key === 'Delete')) {
			e.preventDefault();
			releaseProtocol();
			return;
		}

		if (!open || suggestions.length === 0) return;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			highlight = (highlight + 1) % suggestions.length;
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			highlight = (highlight - 1 + suggestions.length) % suggestions.length;
		} else if (e.key === 'Enter' || e.key === 'Tab') {
			if (highlight >= 0) {
				e.preventDefault();
				selectSuggestion(suggestions[highlight]);
			}
		} else if (e.key === 'Escape') {
			e.preventDefault();
			open = false;
			highlight = -1;
		}
	}

	$effect(() => {
		if (value !== lastEmitted && value !== protocol + rest) {
			splitValue(value);
			lastEmitted = value;
		}
	});
</script>

<div class="space-y-1.5">
	<label for="url-input" class="block text-sm font-medium text-foreground">Target URL</label>
	<div bind:this={rootRef} class="relative">
		<div
			class="flex w-full items-stretch overflow-hidden rounded-md border border-border bg-background transition-colors focus-within:border-primary focus-within:ring-1 focus-within:ring-primary {error ? 'border-destructive' : ''}"
		>
			{#if protocol}
				<span
					class="flex shrink-0 items-center gap-1 border-r border-border bg-muted/40 px-2 font-mono text-sm text-primary"
				>
					{protocol}
					<button
						type="button"
						onclick={releaseProtocol}
						class="text-muted-foreground transition-colors hover:text-foreground"
						aria-label="Edit protocol"
						title="Edit protocol"
					>✎</button>
				</span>
			{/if}
			<input
				bind:this={inputRef}
				id="url-input"
				type="text"
				value={protocol ? rest : value}
				oninput={(e) => {
					protocol ? handleRestInput(e.currentTarget.value) : handlePlainInput(e.currentTarget.value);
					scheduleFetch();
				}}
				onfocus={handleFocus}
				onkeydown={handleKeydown}
				placeholder={protocol ? 'example.com' : placeholder}
				class="w-full bg-transparent px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
				aria-invalid={!!error}
				aria-describedby={error ? 'url-error' : undefined}
				role="combobox"
				aria-expanded={open}
				aria-haspopup="listbox"
				aria-controls="url-suggestions"
			/>
		</div>

		{#if open && suggestions.length > 0}
			<ul
				id="url-suggestions"
				class="absolute left-0 right-0 top-full z-20 mt-1 max-h-64 overflow-y-auto rounded-md border border-border bg-card shadow-lg"
				role="listbox"
			>
				{#each suggestions as url, i}
					<li role="option" aria-selected={i === highlight}>
						<button
							type="button"
							onmousedown={(e) => {
								e.preventDefault();
								selectSuggestion(url);
							}}
							onmouseenter={() => (highlight = i)}
							class="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm
								{i === highlight ? 'bg-accent text-accent-foreground' : 'text-foreground'}"
						>
							<span class="truncate font-mono text-xs">{url}</span>
						</button>
					</li>
				{/each}
			</ul>
		{/if}
	</div>
	{#if error}
		<p id="url-error" class="text-xs text-destructive">{error}</p>
	{/if}
</div>