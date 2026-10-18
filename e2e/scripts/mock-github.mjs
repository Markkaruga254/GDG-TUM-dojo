#!/usr/bin/env node
/**
 * Minimal mock of the GitHub REST API surface the evaluation engine reads
 * (see backend/app/integrations/github.py). It serves one canned repository,
 * "e2e-labs/cloud-notes", that satisfies every check on the seeded E2E
 * challenge — evaluations therefore run offline and deterministically.
 *
 * Routes:
 *   GET /health                                 readiness probe
 *   GET /repos/{owner}/{repo}                   repository metadata
 *   GET /repos/{owner}/{repo}/readme            base64 README
 *   GET /repos/{owner}/{repo}/license           license metadata
 *   GET /repos/{owner}/{repo}/languages         language breakdown
 *   GET /repos/{owner}/{repo}/commits?per_page=N  commit list
 *   GET /repos/{owner}/{repo}/contents/{path}   file or directory entry
 *
 * Any other owner/repo or path returns 404, mirroring GitHub.
 */

import http from "node:http";

const PORT = Number(process.env.E2E_MOCK_GITHUB_PORT ?? "8990");
const OWNER = "e2e-labs";
const REPO = "cloud-notes";
const TOTAL_COMMITS = 12;

const README = `# Cloud Notes

A small notes application that keeps a notebook in sync across devices.

## Installation

\`\`\`bash
npm install
npm run dev
\`\`\`

## Usage

Open the app, sign in with GitHub and start writing. Notes sync in the
background; conflicts resolve last-write-wins while a device is offline.

## Development

Run \`npm test\` before pushing. The frontend is built with Vite and the
API uses PostgreSQL in development. Deployments use a single container.
`;

const FILES = new Map([
  ["README.md", { type: "file", path: "README.md", size: README.length }],
  ["package.json", { type: "file", path: "package.json", size: 512 }],
  ["src", { type: "dir", path: "src", size: 0 }],
]);

const REPOSITORY = {
  full_name: `${OWNER}/${REPO}`,
  name: REPO,
  owner: { login: OWNER },
  private: false,
  default_branch: "main",
  html_url: `https://github.com/${OWNER}/${REPO}`,
  archived: false,
  fork: false,
  description: "Canned repository served by the Build Arena E2E mock GitHub API.",
  size: 4096,
  stargazers_count: 7,
  pushed_at: "2026-10-01T12:00:00Z",
};

function json(res, status, body) {
  const payload = JSON.stringify(body);
  res.writeHead(status, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(payload),
  });
  res.end(payload);
}

function notFound(res) {
  json(res, 404, { message: "Not Found", documentation_url: "https://docs.github.com/rest" });
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url ?? "/", `http://127.0.0.1:${PORT}`);
  const segments = url.pathname.split("/").filter(Boolean);

  if (segments[0] === "health") {
    json(res, 200, { status: "ok" });
    return;
  }
  if (segments[0] !== "repos" || segments[1] !== OWNER || segments[2] !== REPO) {
    notFound(res);
    return;
  }

  const rest = segments.slice(3);
  if (rest.length === 0) {
    json(res, 200, REPOSITORY);
    return;
  }

  if (rest.length === 1) {
    switch (rest[0]) {
      case "readme":
        json(res, 200, {
          name: "README.md",
          path: "README.md",
          encoding: "base64",
          content: Buffer.from(README, "utf8").toString("base64"),
        });
        return;
      case "license":
        json(res, 200, { key: "mit", name: "MIT License", spdx_id: "MIT" });
        return;
      case "languages":
        json(res, 200, { TypeScript: 12000, CSS: 2500, HTML: 1500 });
        return;
      case "commits": {
        const requested = Number.parseInt(url.searchParams.get("per_page") ?? "30", 10);
        const count = Math.max(
          1,
          Math.min(Number.isFinite(requested) ? requested : 30, TOTAL_COMMITS),
        );
        json(
          res,
          200,
          Array.from({ length: count }, (_, index) => ({
            sha: `e2e${String(index).padStart(4, "0")}`,
            commit: { message: `Commit ${index + 1}`, author: { date: "2026-10-01T10:00:00Z" } },
          })),
        );
        return;
      }
      default:
        notFound(res);
        return;
    }
  }

  if (rest[0] === "contents") {
    const filePath = rest.slice(1).join("/");
    const entry = FILES.get(filePath);
    if (entry) {
      json(res, 200, entry);
    } else {
      notFound(res);
    }
    return;
  }

  notFound(res);
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`mock GitHub API listening on http://127.0.0.1:${PORT} (${OWNER}/${REPO})`);
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => server.close(() => process.exit(0)));
}
