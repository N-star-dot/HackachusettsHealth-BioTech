// Display names for labware load names (BRIEF 5.7).
const NAMES: Record<string, string> = {
  flex_1channel_1000: "Flex 1-Channel 1000 µL",
  flex_1channel_50: "Flex 1-Channel 50 µL",
  flex_8channel_1000: "Flex 8-Channel 1000 µL",
  opentrons_flex_96_tiprack_200ul: "Flex 96 tip rack, 200 µL",
  corning_96_wellplate_360ul_flat: "Corning 96-well plate, 360 µL, flat",
  nest_12_reservoir_15ml: "NEST 12-well reservoir, 15 mL",
};

export function labwareName(loadName: string): string {
  return NAMES[loadName] ?? loadName;
}

// Known compound/target display names (BRIEF 5.7 fallback map).
const COMPOUND_TARGET: Record<string, string> = {
  CHEMBL554: "lapatinib",
  CHEMBL1824: "HER2",
  CHEMBL10: "SB-203580",
  CHEMBL260: "p38alpha (MAPK14)",
  CHEMBL221959: "tofacitinib",
  CHEMBL2971: "JAK2",
};

export function chemblName(id: string): string {
  return COMPOUND_TARGET[id] ?? id;
}
