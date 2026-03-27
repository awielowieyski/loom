"""GitHub API scraper for skill files."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    from loom.ingestion.config import RepoSource

logger = logging.getLogger(__name__)


@dataclass
class FileEntry:
    """A file discovered in a GitHub repo."""

    path: str
    sha: str
    size: int


@dataclass
class RawIngestionItem:
    """Raw content fetched from GitHub, ready for transformation."""

    source_uri: str  # github:owner/repo/path@sha
    file_path: str
    raw_content: str
    source_type: str
    repo_owner: str
    repo_name: str
    commit_sha: str | None = None
    detected_license: str | None = None


class GitHubScraper:
    """Fetches skill files from GitHub repositories."""

    def __init__(self, token: str | None = None) -> None:
        headers: dict[str, str] = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            headers=headers,
            timeout=30.0,
            follow_redirects=True,
        )
        self._raw_client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def list_files(self, source: RepoSource) -> list[FileEntry]:
        """Get all matching files from the repo tree."""
        url = f"/repos/{source.owner}/{source.repo}/git/trees/HEAD?recursive=1"
        resp = await self._client.get(url)

        if resp.status_code == 403:
            remaining = resp.headers.get("X-RateLimit-Remaining", "?")
            logger.warning("Rate limited (remaining: %s). Use GITHUB_TOKEN.", remaining)
            return []

        resp.raise_for_status()
        tree = resp.json().get("tree", [])

        entries: list[FileEntry] = []
        for item in tree:
            if item["type"] != "blob":
                continue
            path = item["path"]

            # Check if path matches any of the configured paths
            in_path = any(path.startswith(p) for p in source.paths) if source.paths else True
            if not in_path:
                continue

            # Check if filename matches any pattern
            filename = path.split("/")[-1]
            matches_pattern = any(fnmatch.fnmatch(filename, pat) for pat in source.file_patterns)
            if not matches_pattern:
                continue

            entries.append(FileEntry(path=path, sha=item["sha"], size=item.get("size", 0)))

        return entries

    async def fetch_content(self, owner: str, repo: str, path: str) -> str:
        """Fetch raw file content from GitHub."""
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{path}"
        resp = await self._raw_client.get(url)
        resp.raise_for_status()
        return resp.text

    async def get_default_branch_sha(self, owner: str, repo: str) -> str | None:
        """Get the SHA of the default branch HEAD."""
        resp = await self._client.get(f"/repos/{owner}/{repo}/commits/HEAD")
        if resp.status_code == 200:
            sha: str | None = resp.json().get("sha")
            return sha
        return None

    async def detect_license(self, owner: str, repo: str) -> str | None:
        """Detect the repo license via GitHub API."""
        resp = await self._client.get(f"/repos/{owner}/{repo}/license")
        if resp.status_code == 200:
            spdx_id: str | None = resp.json().get("license", {}).get("spdx_id")
            return spdx_id
        return None

    async def scrape_repo(self, source: RepoSource) -> list[RawIngestionItem]:
        """Fetch all matching files from a repo."""
        logger.info("Scanning %s/%s ...", source.owner, source.repo)

        files = await self.list_files(source)
        if not files:
            logger.info("  No matching files found.")
            return []

        logger.info("  Found %d matching files", len(files))

        # Get commit SHA and license
        commit_sha = await self.get_default_branch_sha(source.owner, source.repo)
        detected_license = source.license_override or await self.detect_license(
            source.owner, source.repo
        )

        items: list[RawIngestionItem] = []

        # Fetch content with concurrency limit to avoid rate limits
        sem = asyncio.Semaphore(5)

        async def fetch_one(entry: FileEntry) -> RawIngestionItem | None:
            async with sem:
                try:
                    content = await self.fetch_content(source.owner, source.repo, entry.path)
                    # Skip very small files (likely not real skills)
                    if len(content.strip()) < 50:
                        return None
                    return RawIngestionItem(
                        source_uri=(
                            f"github:{source.owner}/{source.repo}"
                            f"/{entry.path}@{commit_sha or entry.sha}"
                        ),
                        file_path=entry.path,
                        raw_content=content,
                        source_type=source.source_type,
                        repo_owner=source.owner,
                        repo_name=source.repo,
                        commit_sha=commit_sha,
                        detected_license=detected_license,
                    )
                except httpx.HTTPError as e:
                    logger.warning("  Failed to fetch %s: %s", entry.path, e)
                    return None

        results = await asyncio.gather(*[fetch_one(f) for f in files])
        items = [r for r in results if r is not None]

        logger.info("  Fetched %d items", len(items))
        return items

    async def close(self) -> None:
        await self._client.aclose()
        await self._raw_client.aclose()
