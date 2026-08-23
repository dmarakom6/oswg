<script lang="ts">
	let {
		value,
		onchange,
		error,
		placeholder = 'https://example.com'
	}: {
		value: string;
		onchange: (val: string) => void;
		error?: string;
		placeholder?: string;
	} = $props();

	const PROTOCOLS = ['http://', 'https://'];
	const PROTOCOL_RE = /^https?:\/\//i;

	let protocol = $state('');
	let rest = $state('');
	let lastEmitted = $state('');

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

	function handleKeydown(e: KeyboardEvent) {
		if (protocol && rest === '' && (e.key === 'Backspace' || e.key === 'Delete')) {
			e.preventDefault();
			releaseProtocol();
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
	<div class="flex w-full items-stretch overflow-hidden rounded-md border border-border bg-background transition-colors focus-within:border-primary focus-within:ring-1 focus-within:ring-primary {error ? 'border-destructive' : ''}">
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
			id="url-input"
			type="text"
			value={protocol ? rest : value}
			oninput={(e) => (protocol ? handleRestInput(e.currentTarget.value) : handlePlainInput(e.currentTarget.value))}
			onkeydown={handleKeydown}
			placeholder={protocol ? 'example.com' : placeholder}
			class="w-full bg-transparent px-3 py-2 font-mono text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
			aria-invalid={!!error}
			aria-describedby={error ? 'url-error' : undefined}
		/>
	</div>
	{#if error}
		<p id="url-error" class="text-xs text-destructive">{error}</p>
	{/if}
</div>