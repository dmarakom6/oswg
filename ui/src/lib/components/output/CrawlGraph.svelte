<script lang="ts">
	import { endpoints } from '$lib/api/endpoints';
	import type { CrawlGraph } from '$lib/api/types';

	let { jobId }: { jobId: string } = $props();

	let graph = $state<CrawlGraph | null>(null);
	let error = $state('');
	let selected = $state<string | null>(null);

	const NODE_W = 140;
	const NODE_H = 26;
	const NODE_STEP = NODE_W + 44;
	const LEVEL_GAP = 90;
	const PAD = 10;

	$effect(() => {
		if (!jobId) return;
		let cancelled = false;
		endpoints.getGraph(jobId)
			.then((g) => {
				if (!cancelled) graph = g;
			})
			.catch(() => {
				if (!cancelled) error = 'Crawl graph unavailable';
			});
		return () => {
			cancelled = true;
		};
	});

	// Compute depth (level) per node via BFS over the directed graph.
	function computeLevels(g: CrawlGraph): Map<string, number> {
		const levels = new Map<string, number>();
		const roots = g.nodes.map((n) => n.id).filter((id) => !g.edges.some(([, to]) => to === id));
		const queue = roots.length ? roots : g.nodes.map((n) => n.id).slice(0, 1);
		for (const r of queue) levels.set(r, 0);
		let qi = 0;
		while (qi < queue.length) {
			const cur = queue[qi++];
			const level = levels.get(cur)!;
			for (const [from, to] of g.edges) {
				if (from === cur && !levels.has(to)) {
					levels.set(to, level + 1);
					queue.push(to);
				}
			}
		}
		// Any unreachable node (disconnected) gets its own level at the end.
		let fallback = levels.size ? Math.max(...levels.values()) + 1 : 0;
		for (const n of g.nodes) {
			if (!levels.has(n.id)) {
				levels.set(n.id, fallback++);
			}
		}
		return levels;
	}

	function shortLabel(url: string): string {
		try {
			const u = new URL(url);
			const label = u.pathname === '/' ? u.hostname : u.pathname;
			const max = Math.max(8, Math.floor((NODE_W - 16) / 6));
			return label.length > max ? label.slice(0, max - 1) + '…' : label;
		} catch {
			const max = Math.max(8, Math.floor((NODE_W - 16) / 6));
			return url.length > max ? url.slice(0, max - 1) + '…' : url;
		}
	}

	$effect(() => {
		if (graph && !selected && graph.nodes.length) {
			selected = graph.nodes[0].id;
		}
	});

	// Layout: x = node index within level, y = level.
	let layout = $derived.by(() => {
		if (!graph) return { width: 0, height: 0, nodes: [], edges: [] };
		const levels = computeLevels(graph);
		const byLevel = new Map<number, string[]>();
		for (const [id, lvl] of levels) {
			if (!byLevel.has(lvl)) byLevel.set(lvl, []);
			byLevel.get(lvl)!.push(id);
		}
		const maxLevel = Math.max(...byLevel.keys(), 0);
		const maxWidth = Math.max(...[...byLevel.values()].map((v) => v.length), 1);
		const width = Math.max(320, maxWidth * NODE_STEP + PAD * 2);
		const height = maxLevel * LEVEL_GAP + NODE_H + PAD * 2;

		const pos = new Map<string, { x: number; y: number }>();
		for (const [lvl, ids] of byLevel) {
			const total = ids.length;
			const startX = (width - total * NODE_STEP) / 2;
			ids.forEach((id, i) => {
				pos.set(id, { x: startX + i * NODE_STEP, y: PAD + lvl * LEVEL_GAP });
			});
		}

		const nodes = graph.nodes.map((n) => ({ id: n.id, ...pos.get(n.id)! }));
		const edges = graph.edges
			.filter(([from, to]) => pos.has(from) && pos.has(to))
			.map(([from, to]) => ({ from, to, ...pos.get(from)!, x2: pos.get(to)!.x, y2: pos.get(to)!.y }));
		return { width, height, nodes, edges };
	});
</script>

<div class="space-y-2">
	<div class="flex items-center justify-between">
		<span class="text-xs font-medium text-foreground">Crawl graph</span>
		{#if graph}
			<span class="text-xs text-muted-foreground">
				{graph.nodes.length} pages · {graph.crawl_strategy?.toUpperCase() ?? ''}
			</span>
		{/if}
	</div>

	{#if error}
		<p class="text-xs text-destructive">{error}</p>
	{:else if layout.width > 0}
		<div class="overflow-x-auto rounded-md border border-border bg-muted/20 p-2">
			<svg width={layout.width} height={layout.height} class="block">
				{#each layout.edges as e}
					<line x1={e.x + NODE_W / 2} y1={e.y + NODE_H} x2={e.x2 + NODE_W / 2} y2={e.y2} stroke="currentColor" class="text-muted-foreground/40" stroke-width="1" />
				{/each}
				{#each layout.nodes as n}
					<g
						class="cursor-pointer"
						role="button"
						tabindex="0"
						onclick={() => (selected = n.id)}
						onkeydown={(e) => {
							if (e.key === 'Enter' || e.key === ' ') {
								e.preventDefault();
								selected = n.id;
							}
						}}
						transform={`translate(${n.x}, ${n.y})`}
					>
						<rect
							width={NODE_W}
							height={NODE_H}
							rx="5"
							class="transition-colors"
							fill={selected === n.id ? 'var(--primary)' : 'var(--background)'}
							stroke={selected === n.id ? 'var(--primary)' : 'var(--border)'}
							stroke-width="1"
						/>
						<text
							x={NODE_W / 2}
							y={NODE_H / 2 + 4}
							text-anchor="middle"
							class="font-mono"
							fill={selected === n.id ? 'var(--primary-foreground)' : 'var(--foreground)'}
							font-size="10"
						>
							{shortLabel(n.id)}
						</text>
						<title>{n.id}</title>
					</g>
				{/each}
			</svg>
		</div>
		{#if selected}
			<p class="break-all font-mono text-[11px] text-muted-foreground">{selected}</p>
		{/if}
	{/if}
</div>