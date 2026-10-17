/** GitHub repository helpers shared by the submit form and its tests. */

export interface RepoRef {
  owner: string;
  repo: string;
}

export interface RepoParseResult {
  ref?: RepoRef;
  error?: string;
}

/** Parse a GitHub repository URL into an owner/repo pair. */
export function parseRepoUrl(value: string): RepoParseResult {
  const trimmed = value.trim();
  if (!trimmed) return { error: "Repository URL is required." };
  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return { error: "Enter a full URL like https://github.com/owner/repo." };
  }
  if (url.protocol !== "https:" && url.protocol !== "http:") {
    return { error: "Only http(s) URLs are supported." };
  }
  if (url.hostname !== "github.com" && url.hostname !== "www.github.com") {
    return { error: "Only github.com repositories are supported." };
  }
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length !== 2) {
    return { error: "Use the repository root — https://github.com/owner/repo." };
  }
  const owner = parts[0] as string;
  const repo = (parts[1] as string).replace(/\.git$/i, "");
  if (!/^[\w.-]+$/.test(owner) || !/^[\w.-]+$/.test(repo)) {
    return { error: "That does not look like a valid owner/repo pair." };
  }
  return { ref: { owner, repo } };
}

export function isHttpUrl(value: string): boolean {
  try {
    const url = new URL(value.trim());
    return url.protocol === "https:" || url.protocol === "http:";
  } catch {
    return false;
  }
}
