import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BarChart, { riskColor } from "./BarChart";

describe("BarChart", () => {
  const items = [
    { label: "Wait and monitor", value: 14, sub: "14 d" },
    { label: "Reroute shipment", value: 5, sub: "5 d", color: "#fbbf24" },
  ];

  it("renders a label and a bar per item", () => {
    const { container } = render(<BarChart items={items} />);

    expect(screen.getByText("Wait and monitor")).toBeInTheDocument();
    expect(screen.getByText("Reroute shipment")).toBeInTheDocument();
    expect(container.querySelectorAll("rect")).toHaveLength(2);
  });

  it("renders nothing when there are no items", () => {
    const { container } = render(<BarChart items={[]} />);
    expect(container.querySelector("svg")).toBeNull();
  });

  it("maps risk levels to colours", () => {
    expect(riskColor("critical")).toBe("#f87171");
    expect(riskColor("low")).toBe("#34d399");
    expect(riskColor(undefined)).toBe("#38bdf8");
  });
});
