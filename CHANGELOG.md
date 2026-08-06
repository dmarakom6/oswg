# CHANGELOG

<!-- version list -->

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
