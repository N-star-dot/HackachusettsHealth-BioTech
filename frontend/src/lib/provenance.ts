// Provenance kinds + link builder (BRIEF 5.15). Uses source.url when present, else builds
// the canonical link from kind + id. Mirrors the backend's common.source_url table.
import type { Source, SourceType } from "../api/types";

export const KIND_LABEL: Record<string, string> = {
  openalex: "OpenAlex",
  pubmed: "PubMed",
  chembl_activity: "ChEMBL activity",
  semantic_scholar: "Semantic Scholar",
  paper: "Paper",
  spec: "Opentrons spec",
  simulator: "Opentrons simulator",
  simulated: "Simulated",
  assumed: "Assumed value",
  derived: "Computed here from",
};

export function buildUrl(type: SourceType | string, id: string): string | null {
  switch (type) {
    case "openalex":
      // the openalex.org website page, not the api.openalex.org JSON
      if (id.startsWith("T")) return `https://openalex.org/${id}`;
      return null;
    case "chembl_activity": {
      const first = id.split(",")[0].trim();
      if (!first || first.toLowerCase() === "none" || first === "placeholder") return null;
      // compound report cards link straight; a bare activity id uses the explore page
      if (first.toUpperCase().startsWith("CHEMBL")) return `https://www.ebi.ac.uk/chembl/explore/compound/${first}`;
      return `https://www.ebi.ac.uk/chembl/explore/activities/${first}`;
    }
    case "pubmed":
      return `https://pubmed.ncbi.nlm.nih.gov/${id}/`;
    case "paper": {
      const doi = id.startsWith("doi:") ? id.slice(4) : id;
      return `https://doi.org/${doi}`;
    }
    case "spec":
      return "https://docs.opentrons.com/flex/system-description/pipettes/";
    default:
      return null; // simulator, simulated, assumed
  }
}

export function sourceUrl(source: Source | undefined): string | null {
  if (!source) return null;
  return source.url ?? buildUrl(source.type, source.id);
}
