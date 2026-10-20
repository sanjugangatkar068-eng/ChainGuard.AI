import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DisruptionForm from "./DisruptionForm";

function setup(overrides = {}) {
  const props = {
    busy: false,
    disruption: { id: 1 },
    canAnalyze: true,
    onCreate: vi.fn(),
    onAnalyze: vi.fn(),
    ...overrides,
  };
  render(<DisruptionForm {...props} />);
  return props;
}

describe("DisruptionForm", () => {
  it("submits numeric fields as numbers", () => {
    const { onCreate } = setup();

    fireEvent.click(screen.getByText("Create disruption"));

    expect(onCreate).toHaveBeenCalledTimes(1);
    const payload = onCreate.mock.calls[0][0];
    expect(payload.delay_days).toBe(14);
    expect(typeof payload.delay_days).toBe("number");
    expect(payload.severity).toBe("critical");
  });

  it("passes parsed suppliers to onAnalyze", () => {
    const { onAnalyze } = setup();

    fireEvent.click(screen.getByText("Run agent analysis"));

    expect(onAnalyze).toHaveBeenCalledTimes(1);
    const suppliers = onAnalyze.mock.calls[0][0];
    expect(Array.isArray(suppliers)).toBe(true);
    expect(suppliers[0].name).toBe("Apex Components");
  });

  it("blocks analysis and shows an error for invalid suppliers JSON", () => {
    const { onAnalyze } = setup();

    fireEvent.change(screen.getByLabelText(/Suppliers/i), {
      target: { value: "{ not valid json" },
    });
    fireEvent.click(screen.getByText("Run agent analysis"));

    expect(onAnalyze).not.toHaveBeenCalled();
    expect(document.querySelector(".error.inline")).not.toBeNull();
  });

  it("disables analysis until a disruption exists", () => {
    setup({ disruption: null, canAnalyze: false });
    expect(screen.getByText("Run agent analysis")).toBeDisabled();
  });
});
