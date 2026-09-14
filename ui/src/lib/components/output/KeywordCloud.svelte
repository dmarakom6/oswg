<script lang="ts">
	import type { WordCount } from '$lib/api/types';

	let { words }: { words: WordCount[] } = $props();

	const W = 800;
	const H = 520;
	const CX = W / 2;
	const CY = H / 2;
	const MAX_WORDS = 120;
	const MIN_FONT = 12;
	const MAX_FONT = 54;

	type Placed = { word: string; count: number; fs: number; x: number; y: number };

	function fontSize(count: number, lo: number, hi: number): number {
		if (hi <= lo) return (MIN_FONT + MAX_FONT) / 2;
		const t = (Math.sqrt(count) - Math.sqrt(lo)) / (Math.sqrt(hi) - Math.sqrt(lo));
		return MIN_FONT + t * (MAX_FONT - MIN_FONT);
	}

	function overlaps(
		a: { x: number; y: number; w: number; h: number },
		b: { x: number; y: number; w: number; h: number }
	): boolean {
		return !(a.x + a.w <= b.x || b.x + b.w <= a.x || a.y + a.h <= b.y || b.y + b.h <= a.y);
	}

	const layout = $derived.by(() => {
		const sorted = [...words].sort((a, b) => b.count - a.count).slice(0, MAX_WORDS);
		if (sorted.length === 0) return { placed: [] as Placed[], shown: 0 };

		const counts = sorted.map((w) => w.count);
		const lo = Math.min(...counts);
		const hi = Math.max(...counts);

		const placed: Placed[] = [];
		const boxes: { x: number; y: number; w: number; h: number }[] = [];
		const maxR = Math.min(W, H) / 2 - 8;

		for (const { word, count } of sorted) {
			const fs = fontSize(count, lo, hi);
			const tw = word.length * fs * 0.62;
			const th = fs * 1.05;
			let done = false;
			for (let t = 0; t < 4000; t += 0.4) {
				const r = 1.5 * t;
				if (r > maxR) break;
				const x = CX + r * Math.cos(t);
				const y = CY + r * Math.sin(t);
				const box = { x: x - tw / 2, y: y - th / 2, w: tw, h: th };
				if (box.x < 4 || box.y < 4 || box.x + box.w > W - 4 || box.y + box.h > H - 4) continue;
				if (boxes.some((b) => overlaps(b, box))) continue;
				placed.push({ word, count, fs, x, y });
				boxes.push(box);
				done = true;
				break;
			}
			if (!done) continue;
		}

		return { placed, shown: placed.length };
	});

	const maxCount = $derived(words.length ? Math.max(...words.map((w) => w.count)) : 1);
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-foreground">Keyword cloud</span>
		{#if words.length}
			<span class="text-xs text-muted-foreground">
				{layout.shown} of {words.length} words · top {maxCount}×
			</span>
		{/if}
	</div>

	{#if layout.placed.length > 0}
		<div class="overflow-auto rounded-md border border-border bg-muted/20 p-2">
			<svg viewBox={`0 0 ${W} ${H}`} class="mx-auto block h-auto w-full max-w-[900px]">
				{#each layout.placed as p (p.word)}
					<text
						x={p.x}
						y={p.y}
						text-anchor="middle"
						dominant-baseline="central"
						font-size={p.fs}
						font-weight="600"
						fill="var(--primary)"
						fill-opacity={0.45 + 0.55 * (p.fs - MIN_FONT) / (MAX_FONT - MIN_FONT)}
						class="cursor-default"
					>
						{p.word}
						<title>{p.word} · {p.count}×</title>
					</text>
				{/each}
			</svg>
		</div>
	{:else}
		<p class="text-xs text-muted-foreground">No keyword data to display.</p>
	{/if}
</div>