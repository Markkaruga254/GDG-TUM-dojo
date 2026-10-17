import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { Switch } from "./checkbox";

describe("Switch", () => {
  it("exposes its label as the accessible name without an explicit id", () => {
    render(<Switch checked={false} onCheckedChange={() => {}} label="Replace" />);
    expect(screen.getByRole("switch", { name: "Replace" })).toBeInTheDocument();
  });

  it("reports toggles to the handler", async () => {
    const onCheckedChange = vi.fn();
    render(<Switch checked={false} onCheckedChange={onCheckedChange} label="Active" />);

    await userEvent.click(screen.getByRole("switch", { name: "Active" }));

    expect(onCheckedChange).toHaveBeenCalledWith(true);
  });

  it("reflects the checked state", () => {
    render(<Switch checked onCheckedChange={() => {}} label="Active" />);
    expect(screen.getByRole("switch", { name: "Active" })).toHaveAttribute("aria-checked", "true");
  });
});
