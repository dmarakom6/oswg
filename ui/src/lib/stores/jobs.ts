import { writable, derived, get } from 'svelte/store';
import type { ActiveTab, Job } from '$lib/api/types';

const jobMap = writable<Map<string, Job>>(new Map());
const currentJobId = writable<Map<ActiveTab, string>>(new Map());

export const activeJobs = derived(jobMap, ($map) =>
	[...$map.values()]
		.filter((j) => j.status === 'pending' || j.status === 'processing')
		.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
);

export const currentJobForTab = derived(
	[jobMap, currentJobId],
	([$map, $ids]) => (tab: ActiveTab) => {
		const id = $ids.get(tab);
		if (!id) return null;
		return $map.get(id) ?? null;
	}
);

export const jobsStore = {
	subscribe: jobMap.subscribe,
	upsert(job: Partial<Job> & { job_id: string }) {
		jobMap.update((map) => {
			const existing = map.get(job.job_id) ?? {};
			map.set(job.job_id, { ...existing, ...job } as Job);
			return new Map(map);
		});
	},
	setCurrent(tab: ActiveTab, jobId: string) {
		currentJobId.update((m) => {
			m.set(tab, jobId);
			return new Map(m);
		});
	},
	remove(jobId: string) {
		jobMap.update((map) => {
			map.delete(jobId);
			return new Map(map);
		});
	},
	get(jobId: string): Job | undefined {
		return get(jobMap).get(jobId);
	},
	clear() {
		jobMap.set(new Map());
		currentJobId.set(new Map());
	}
};
