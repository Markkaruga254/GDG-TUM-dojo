import { describe, expect, it } from "vitest";

import { isHttpUrl, parseRepoUrl } from "./repo";

describe("parseRepoUrl", () => {
  it("parses a canonical GitHub repository URL", () => {
    expect(parseRepoUrl("https://github.com/gdg-tum/build-arena")).toEqual({
      ref: { owner: "gdg-tum", repo: "build-arena" },
    });
  });

  it("accepts www.github.com and strips a .git suffix", () => {
    expect(parseRepoUrl("https://www.github.com/owner/repo.git")).toEqual({
      ref: { owner: "owner", repo: "repo" },
    });
  });

  it("tolerates a trailing slash and surrounding whitespace", () => {
    expect(parseRepoUrl("  https://github.com/owner/repo/  ")).toEqual({
      ref: { owner: "owner", repo: "repo" },
    });
  });

  it("rejects empty input", () => {
    expect(parseRepoUrl("").error).toBe("Repository URL is required.");
  });

  it("rejects non-URL text", () => {
    expect(parseRepoUrl("not a url").error).toMatch(/full URL/);
  });

  it("rejects non-http protocols", () => {
    expect(parseRepoUrl("ftp://github.com/owner/repo").error).toMatch(/http\(s\)/);
  });

  it("rejects hosts other than github.com", () => {
    expect(parseRepoUrl("https://gitlab.com/owner/repo").error).toMatch(/github\.com/);
  });

  it("rejects deep paths such as a file inside the repo", () => {
    expect(parseRepoUrl("https://github.com/owner/repo/tree/main/src").error).toMatch(
      /repository root/,
    );
  });

  it("rejects owner-only URLs", () => {
    expect(parseRepoUrl("https://github.com/owner").error).toMatch(/repository root/);
  });
});

describe("isHttpUrl", () => {
  it("accepts http and https", () => {
    expect(isHttpUrl("https://example.com/demo")).toBe(true);
    expect(isHttpUrl("http://example.com/demo")).toBe(true);
  });

  it("rejects other protocols and malformed values", () => {
    expect(isHttpUrl("javascript:alert(1)")).toBe(false);
    expect(isHttpUrl("example.com")).toBe(false);
    expect(isHttpUrl("")).toBe(false);
  });
});
