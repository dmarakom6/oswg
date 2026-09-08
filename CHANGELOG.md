# CHANGELOG

<!-- version list -->

## v0.5.0 (2026-09-08)


## v0.4.0 (2026-09-03)

### Bug Fixes

- Expander leaks disabled mutation variants
  ([`1acd94f`](https://github.com/dmarakom6/oswg/commit/1acd94fdb309f370c3f25a814cdb4ee1a6056a35))

- Follow redirects and report failed page scraping
  ([`448136a`](https://github.com/dmarakom6/oswg/commit/448136abd54307f022465e5d9cc351bc9b294a90))

- Keep leet basic/advanced control adjacent to its toggle
  ([`937e13a`](https://github.com/dmarakom6/oswg/commit/937e13a84d3873eab2e4d771918281f0babff180))

- Use protego robots parser; add -v to scrape
  ([`ccdd3ea`](https://github.com/dmarakom6/oswg/commit/ccdd3ea2d00991c39664ce611f5c2f7db0a3adb7))

### Chores

- Restyle URL input and header/cookie fields
  ([`51bd76f`](https://github.com/dmarakom6/oswg/commit/51bd76f75f2b029e36d8ece7fab48b8b84f8f155))

### Features

- --timeout option that defaults to 30sec
  ([`59e52d6`](https://github.com/dmarakom6/oswg/commit/59e52d6aa5705f9a1a73ec29c06d7174857406fc))

- Add --case-permutations to the mutate command
  ([`2dbe355`](https://github.com/dmarakom6/oswg/commit/2dbe35507421bb661cb6c0d16d6d1d38ae656789))

- Add --common-subs for whole-word alias substitution (mutator)
  ([`f5e7b3c`](https://github.com/dmarakom6/oswg/commit/f5e7b3c27629ad5843d621459984360ca1d86cbb))

- Add --dry-run to preview wordlist without writing a file
  ([`65f7959`](https://github.com/dmarakom6/oswg/commit/65f7959d1cb914c02ff5a2b80c81ea10b76cd92a))

- Add --header and --cookie for custom request headers
  ([`5c927da`](https://github.com/dmarakom6/oswg/commit/5c927dafe5ac463e3898d0c8d8826738aabe83cd))

- Add --no-uppercase option to disable case mutations
  ([`23d744a`](https://github.com/dmarakom6/oswg/commit/23d744a33ec21ab7c610e91ed5903b05d79f85cc))

- Add --prepend and --append to the mutate command
  ([`7c51c4c`](https://github.com/dmarakom6/oswg/commit/7c51c4c90f759cf6959c648a5d06832b5d93b304))

- Add --proxy to route requests through a proxy
  ([`319176a`](https://github.com/dmarakom6/oswg/commit/319176a85afd7af7a4846ba87de33bec53f000f6))

- Add --rate-limit and --jitter for request pacing
  ([`a1df40f`](https://github.com/dmarakom6/oswg/commit/a1df40f968ccc76c93c9fc8f2309ed7eea4f6a4d))

- Add --respect-robots to obey robots.txt rules
  ([`10d8772`](https://github.com/dmarakom6/oswg/commit/10d87726b3d090b6d408cca55207b4dd78fad5d3))

- Add --reverse-leet to convert l33t back to letters
  ([`b522b31`](https://github.com/dmarakom6/oswg/commit/b522b31226b55267121df2e5fcb034e5b09232b0))

- Add --user-agent for custom request headers
  ([`8101f80`](https://github.com/dmarakom6/oswg/commit/8101f802eec7c02bad51422e68df1aed5b13088c))

- Add --years and --special-chars config options
  ([`e4f11be`](https://github.com/dmarakom6/oswg/commit/e4f11be25eb20f7bcf4c6525bc829c57030e7ac7))

- Merge external wordlists (rockyou/custom) into generation
  ([`c0215b5`](https://github.com/dmarakom6/oswg/commit/c0215b55741cd96ad4f88ef3ee35e4ad26ba629a))

- Print OSWG banner on --version
  ([`a51006d`](https://github.com/dmarakom6/oswg/commit/a51006d614bba9d8af75e4443578dd790f0262fe))

- Round-robin sampling instead of head-slice truncation
  ([`bae974f`](https://github.com/dmarakom6/oswg/commit/bae974f7153e01ecda80c139bafc7bd317d529db))

- UI Tab persistence & draggable divider
  ([`c840bb5`](https://github.com/dmarakom6/oswg/commit/c840bb53a1b82fda02966db59554161ec8bc96d1))

- Warn when wordlist is truncated to target size
  ([`19c65ba`](https://github.com/dmarakom6/oswg/commit/19c65ba22a4b5579c662096201a5b4ba7fb62fc4))


## v0.3.0 (2026-08-06)

### Chores

- Makefile & stopwords set
  ([`65fb120`](https://github.com/dmarakom6/oswg/commit/65fb120d44895b5eacef5e93e479a021f4e6b92e))

### Features

- Add --verbose flag for detailed scraping progress
  ([`bb6379f`](https://github.com/dmarakom6/oswg/commit/bb6379f6572e63219142487748452bd524e8e4f6))

- Stopwords
  ([`c8507de`](https://github.com/dmarakom6/oswg/commit/c8507de41100253e637f3ee9f94b1b0b0439fd4f))


## v0.2.4 (2026-08-02)

### Bug Fixes

- Disable duplicate release notes from softprops
  ([`2749d19`](https://github.com/dmarakom6/oswg/commit/2749d197c4162ee79c00b5c2cb27a13de45d7616))


## v0.2.3 (2026-08-02)


## v0.2.2 (2026-08-01)

### Bug Fixes

- Add workflow_dispatch to release-binaries for manual tag builds
  ([`8113a48`](https://github.com/dmarakom6/oswg/commit/8113a48616b7f44485845fb17771291e8a8b58dc))


## v0.2.1 (2026-08-01)

### Bug Fixes

- Add /api/v1/info endpoint so footer shows version
  ([`7f70dd1`](https://github.com/dmarakom6/oswg/commit/7f70dd1874345c7242bd45cab1b2d09d9ece0f3e))


## v0.2.0 (2026-08-01)

### Bug Fixes

- Correct semantic-release command in release workflow
  ([`729d4b3`](https://github.com/dmarakom6/oswg/commit/729d4b331078cfaaf93fc73de8c1f554cf084e2c))

- Correct version sourcing, rebuild frontend, fix semantic-release config
  ([`7d0f342`](https://github.com/dmarakom6/oswg/commit/7d0f3422f3985f8826a51a3669dcfecf48cf6880))

- Correct version_toml path to use dot-notation
  ([`19ad572`](https://github.com/dmarakom6/oswg/commit/19ad5725be562d5f6685bf0749cf692c459cdfb9))

- Make --no-deduplicate fully disable all deduplication
  ([`d82cfc3`](https://github.com/dmarakom6/oswg/commit/d82cfc3354a7f461323c515a54f4d35a4db83895))

- Pass GH_TOKEN to python-semantic-release
  ([`c1ee7da`](https://github.com/dmarakom6/oswg/commit/c1ee7da921ae488a210148368c6de08a04a963ac))

- Remove build_command from semantic-release config
  ([`ce5c278`](https://github.com/dmarakom6/oswg/commit/ce5c27804157d6f0cf86a1defe51bf8a95a26fa6))

- Set allow_zero_version=true to prevent 0.x→1.0.0 jumps
  ([`fb9f456`](https://github.com/dmarakom6/oswg/commit/fb9f456cad0cc5452d73b98d6df141771252e4ff))

- Suppress ASGI handshake errors and wait for server before opening browser
  ([`5bbbf37`](https://github.com/dmarakom6/oswg/commit/5bbbf378cb4cd4f8bbf394a27ccfa52ceffe17ad))

### Chores

- Remove wordlist.txt from tracking, add to gitignore
  ([`48cbb52`](https://github.com/dmarakom6/oswg/commit/48cbb527944c81f973ce11bfab0b3fd0e6d0689a))

### Features

- Add SVG favicon with dark/light mode support
  ([`e314dd2`](https://github.com/dmarakom6/oswg/commit/e314dd27d2de83650713ed44c7a541e8a2ada7fd))

- Auto-versioning via semantic-release, Advanced UI section with deduplicate
  ([`98fddc4`](https://github.com/dmarakom6/oswg/commit/98fddc4b560b7c89d348e23fad3be99f58ad4d58))


## v0.1.8 (2026-08-01)

### Bug Fixes

- Apply config params, rewrite scraper with recursive crawl + sitemap
  ([`696b197`](https://github.com/dmarakom6/oswg/commit/696b1971914b0f1a1c92ff85f8f1adc6fb189301))


## v0.1.7 (2026-07-31)

### Bug Fixes

- Correct artifact paths in release workflow for onedir zips
  ([`1976f6b`](https://github.com/dmarakom6/oswg/commit/1976f6bdeaa99b3ccb4db1afd3c273a429f97c55))

- Switch to onedir mode, resolve binary hang
  ([`f87c516`](https://github.com/dmarakom6/oswg/commit/f87c5160f3fd49af9a0954c1532c203942d1f135))


## v0.1.5 (2026-07-31)

### Bug Fixes

- Build wheel only for PyPI to avoid sdist force-include failure; bump to 0.1.5
  ([`498a656`](https://github.com/dmarakom6/oswg/commit/498a65614fb8eb1c935798181a169dda35b85be7))


## v0.1.4 (2026-07-31)

### Bug Fixes

- Build frontend before pip install so wheel force-include succeeds; drop redundant build job from
  semantic-release workflow
  ([`8085c21`](https://github.com/dmarakom6/oswg/commit/8085c21f5d16bf5719a410e3271e56ba03651c69))

### Features

- Bundle SvelteKit web UI into package and binaries
  ([`a9ae96c`](https://github.com/dmarakom6/oswg/commit/a9ae96cff09c828b6bb6064b21b6179f61522740))


## v0.1.3 (2026-07-31)

- Initial Release
