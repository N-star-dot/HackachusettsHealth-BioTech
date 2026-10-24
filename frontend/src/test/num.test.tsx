import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { Num } from "../components/Num/Num";
import { assumed, derived, simulated, src } from "../components/Num/provenance";
import { fold, nM, pct, prob, uL } from "../lib/format";
import { buildUrl } from "../lib/provenance";

describe("format", () => {
  it("formats concentrations", () => {
    expect(nM(2399)).toBe("2,399 nM");
    expect(nM(24)).toBe("24 nM");
    expect(nM(0.12)).toBe("0.12 nM");
  });
  it("formats fold, pct, prob, uL", () => {
    expect(fold(1.31)).toBe("1.31x");
    expect(pct(0.03)).toBe("3%");
    expect(pct(0.005)).toBe("0.5%");
    expect(prob(0.71)).toBe("71%");
    expect(uL(50)).toBe("50 µL");
  });
});

describe("buildUrl", () => {
  it("builds canonical links", () => {
    expect(buildUrl("openalex", "T10966")).toBe("https://openalex.org/T10966");
    expect(buildUrl("chembl_activity", "190222,1")).toBe(
      "https://www.ebi.ac.uk/chembl/explore/activities/190222",
    );
    expect(buildUrl("chembl_activity", "CHEMBL554")).toBe(
      "https://www.ebi.ac.uk/chembl/explore/compound/CHEMBL554",
    );
    expect(buildUrl("pubmed", "14684309")).toBe("https://pubmed.ncbi.nlm.nih.gov/14684309/");
    expect(buildUrl("simulator", "x")).toBeNull();
  });
});

describe("Num dev guard", () => {
  it("every rendered number carries a non-empty data-provenance", () => {
    const { container } = render(
      <div>
        <Num value="71%" provenance={src({ type: "openalex", id: "T1" })} />
        <Num value="1.31x" provenance={simulated(42, 1000)} />
        <Num value="0.55" provenance={assumed("fixed prior")} />
        <Num value="0.64" provenance={derived("a*b", [{ label: "a" }])} />
      </div>,
    );
    const nums = container.querySelectorAll("[data-num]");
    expect(nums.length).toBe(4);
    nums.forEach((el: Element) => {
      expect(el.getAttribute("data-provenance")).toBeTruthy();
    });
  });
});
