import { describe, expect, it } from "vitest";

import {
  avatarUrl,
  describeDeadline,
  displayNameOf,
  formatNumber,
  formatRelative,
  initials,
  pluralize,
} from "./utils";

const HOUR = 3_600_000;

describe("formatNumber", () => {
  it("groups thousands", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(12345)).toBe("12,345");
  });
});

describe("pluralize", () => {
  it("handles singular and plural", () => {
    expect(pluralize(1, "day")).toBe("day");
    expect(pluralize(0, "day")).toBe("days");
    expect(pluralize(2, "badge", "badges")).toBe("badges");
  });
});

describe("initials", () => {
  it("takes the first letters of up to two name parts", () => {
    expect(initials("Ada Lovelace")).toBe("AL");
    expect(initials("mark")).toBe("M");
    expect(initials("gdg_tum build arena")).toBe("GT");
  });
});

describe("avatarUrl", () => {
  it("prefers the stored avatar", () => {
    expect(avatarUrl({ avatar_url: "https://cdn.example/a.png", github_username: "ada" })).toBe(
      "https://cdn.example/a.png",
    );
  });

  it("falls back to the GitHub avatar endpoint", () => {
    expect(avatarUrl({ avatar_url: null, github_username: "ada" })).toBe(
      "https://github.com/ada.png?size=160",
    );
  });

  it("returns null without a username", () => {
    expect(avatarUrl({ avatar_url: null, github_username: "" })).toBeNull();
  });
});

describe("displayNameOf", () => {
  it("prefers a non-blank display name", () => {
    expect(displayNameOf({ display_name: "Ada", github_username: "ada" })).toBe("Ada");
    expect(displayNameOf({ display_name: "   ", github_username: "ada" })).toBe("ada");
    expect(displayNameOf({ display_name: null, github_username: "ada" })).toBe("ada");
  });
});

describe("describeDeadline", () => {
  const now = new Date("2026-01-10T12:00:00Z").getTime();

  it("describes open-ended challenges", () => {
    expect(describeDeadline(null, now)).toEqual({ label: "Open ended", tone: "none" });
  });

  it("marks closed challenges", () => {
    const endsAt = new Date(now - HOUR).toISOString();
    expect(describeDeadline(endsAt, now)).toEqual({
      label: "Submissions closed",
      tone: "ended",
    });
  });

  it("counts hours under two days", () => {
    const endsAt = new Date(now + 12 * HOUR).toISOString();
    expect(describeDeadline(endsAt, now)).toEqual({ label: "Closes in 12h", tone: "soon" });
  });

  it("counts days under two weeks", () => {
    const endsAt = new Date(now + 5 * 24 * HOUR).toISOString();
    expect(describeDeadline(endsAt, now)).toEqual({
      label: "Closes in 5 days",
      tone: "upcoming",
    });
  });

  it("shows a date far out", () => {
    const endsAt = new Date(now + 30 * 24 * HOUR).toISOString();
    const result = describeDeadline(endsAt, now);
    expect(result.tone).toBe("none");
    expect(result.label).toMatch(/^Closes /);
  });
});

describe("formatRelative", () => {
  it("formats a past timestamp", () => {
    const now = new Date("2026-01-10T12:00:00Z").getTime();
    const iso = new Date(now - 2 * HOUR).toISOString();
    expect(formatRelative(iso, now)).toMatch(/2 hours ago/);
  });
});
