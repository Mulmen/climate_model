"""klimatmodell_streamlit.climate_model

En enkel, transparent screeningmodell för att uppskatta klimatpåverkan i byggskedet (modul A1-A5)
i enheten kg CO2e/m² BTA och ton CO2e/m² BTA, med fokus på flerbostadshus.

Viktigt:
- Detta är *inte* ett officiellt klimatdeklarationsverktyg och ersätter inte projektets faktiska LCA.
- Modellen är byggd för att vara pedagogisk och snabb och använder schabloner/koefficienter som kan
  justeras i koden eller via Streamlit-gränssnittet.

Modellidé (på hög nivå):
1) Utgå från en referensnivå (median) för flerbostadshus (kg CO2e/m² BTA) för vald systemgräns.
2) Dela upp referensnivån i grova byggdelskategorier (stomme, klimatskärm, grund, innerväggar,
   samt ev. ytskikt/installationer vid utökad systemgräns).
3) Skala relevanta delar med:
   - formfaktor (Aom/BTA) -> påverkar klimatskärm/isolering
   - fönsterandel -> påverkar klimatskärm (fönster har ofta högre klimatintensitet per m² än vägg)
   - konstruktionsmetod/stomsystem -> påverkar främst stomme+grund
   - källare/garage -> additivt tillskott (schablon)
   - klimatförbättrade material -> reducerar betong/metalldominerade delar

Alla parametrar är justerbara för kalibrering mot egen data.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Literal, Optional, Tuple


SystemBoundary = Literal["2022", "2027"]
StructuralSystem = Literal["Betong", "Trä", "Stål"]


@dataclass(frozen=True)
class ModelConfig:
    # Referensnivåer (kg CO2e/m² BTA) – flerbostadshus, modul A1-A5.
    # (Defaultvärden baserade på KTH:s referensvärdesrapport, Tabell 9, samt Boverkets avrundning.)
    median_kg_per_m2: Dict[SystemBoundary, float]
    median_kg_per_m2_climate_improved: Dict[SystemBoundary, float]

    # Bas-fördelning (andel av total) per grov byggdelskategori.
    # Summan ska vara 1.0 för varje systemgräns.
    shares_2022: Dict[str, float]
    shares_2027: Dict[str, float]

    # Referensgeometri
    ref_form_factor: float  # Aom/BTA
    ref_window_ratio: float  # andel fönsterarea av fasad (0-1)

    # Relativ klimatintensitet (fönster vs. ogenomskinlig vägg).
    window_to_wall_intensity_ratio: float

    # Stomsystems-/metodmultiplikatorer (≈ påverkar främst stomme+grund)
    # Nycklarna matchar val i Streamlit.
    method_multiplier: Dict[str, float]

    # Hur stor del av totalen som påverkas av "stomme+grund"-val.
    # (Resten antas vara mer oberoende av stomval i denna screeningmodell.)
    structure_affected_share_2022: float
    structure_affected_share_2027: float

    # Schablon för undermarks-/garagepåslag (kg CO2e per m² Atemp vid parkeringstal 0,5)
    garage_add_kg_per_m2_atemp_parking05: float

    # Basvirkesandel (ton virke/m² BTA) – screeningvärden som kan justeras.
    timber_t_per_m2_default_by_system: Dict[StructuralSystem, float]

    # Baspåslag för "källare utan garage" (kg CO2e/m² BTA) – osäkert, görs justerbart.
    basement_add_kg_per_m2_bta: float


@dataclass(frozen=True)
class ModelInputs:
    system_boundary: SystemBoundary

    # Geometri
    form_factor: float
    window_ratio: float

    # Byggnad
    floors: int
    building_height_m: Optional[float] = None  # frivilligt

    # Konstruktion
    structural_system: StructuralSystem = "Betong"
    method: str = "Prefabricerad betong"
    heavy_concrete_design: bool = False  # t.ex. massiva skalväggar

    # Materialval
    climate_improved_materials: bool = False
    climate_improved_applicability: float = 1.0  # 0..1, hur mycket "klimatförbättrat" biter

    # Under mark
    basement: bool = False
    underground_garage: bool = False
    parking_ratio: float = 0.5  # 0..1, relaterat till schablonen
    atemp_to_bta: float = 0.90  # används för konvertering av garage-schablon

    # Virke
    timber_t_per_m2_override: Optional[float] = None


@dataclass(frozen=True)
class ModelResult:
    total_kg_per_m2_bta: float
    total_t_per_m2_bta: float
    reference_kg_per_m2_bta: float
    delta_vs_reference_kg: float
    delta_vs_reference_percent: float
    breakdown_kg_per_m2_bta: Dict[str, float]
    timber_t_per_m2_bta: float

    # Extra diagnos
    notes: Tuple[str, ...] = ()


def default_config() -> ModelConfig:
    # Medianvärden för flerbostadshus från KTH Tabell 9 (2022/2027 systemgräns).
    # Boverket har i vissa sammanhang avrundat 373 -> 375 för gränsvärde.
    median = {"2022": 318.0, "2027": 373.0}
    median_improved = {"2022": 271.0, "2027": 325.0}

    # Byggdelsandelar (heuristik).
    shares_2022 = {
        "Stomme": 0.50,
        "Grund": 0.15,
        "Klimatskärm": 0.25,
        "Innerväggar": 0.10,
    }
    shares_2027 = {
        "Stomme": 0.45,
        "Grund": 0.15,
        "Klimatskärm": 0.20,
        "Innerväggar": 0.10,
        "Invändiga ytskikt & installationer": 0.10,
    }

    # Konstruktionsmetodmultiplikatorer (relativa).
    # Baserat på SBUF/IVL (Erlandsson m.fl. 2018) A1-A5 för ett typhus (kg CO2e/m² Atemp):
    #   Prefab betong (plattform 3): 272 (referens = 1.0)
    #   Platsgjuten betong + utfackning (plattform 2): 290  => 1.066
    #   Platsgjuten betong + kvarsittande form (plattform 1): 331 => 1.217
    #   Volymelement trä (plattform 4): 223 => 0.820
    #   KL-trä (plattform 5): 223 => 0.820
    # Konstruktionsmetodmultiplikatorer (relativa) – används i denna modell främst för att variera inom betongsystem.
    # Baserat på SBUF/IVL/Byggföretagen (Erlandsson m.fl. 2018) A1–A5 för ett typhus (kg CO2e/m² Atemp):
    #   Prefab betong (plattform 3): 272 (referens = 1.0)
    #   Platsgjuten betong + utfackning (plattform 2): 290  => 1.066
    #   Platsgjuten betong + kvarsittande form (plattform 1): 331 => 1.217
    # För trä-alternativen sätts multiplikator = 1.0 här (skillnaden trä/betong hanteras separat via stomsystemfaktor).
    method_multiplier = {
        "Prefabricerad betong": 1.000,
        "Platsgjuten betong (lätta utfackningsväggar)": 290.0 / 272.0,
        "Platsgjuten betong (kvarsittande form)": 331.0 / 272.0,
        "Volymelement i trä": 1.000,
        "KL-trä (massiv stomme)": 1.000,
    }

    return ModelConfig(
        median_kg_per_m2=median,
        median_kg_per_m2_climate_improved=median_improved,
        shares_2022=shares_2022,
        shares_2027=shares_2027,
        ref_form_factor=0.45,
        ref_window_ratio=0.20,
        window_to_wall_intensity_ratio=4.0,
        method_multiplier=method_multiplier,
        structure_affected_share_2022=0.70,
        structure_affected_share_2027=0.65,
        garage_add_kg_per_m2_atemp_parking05=48.0,
        timber_t_per_m2_default_by_system={"Betong": 0.005, "Trä": 0.060, "Stål": 0.002},
        basement_add_kg_per_m2_bta=25.0,
    )


def _validate_inputs(inp: ModelInputs) -> Tuple[str, ...]:
    notes = []
    if not (0.2 <= inp.form_factor <= 1.5):
        notes.append("Formfaktor verkar ligga utanför normalt intervall (0,2–1,5).")
    if not (0.0 <= inp.window_ratio <= 0.9):
        notes.append("Fönsterandel bör ligga mellan 0 och 0,9.")
    if inp.floors < 1:
        notes.append("Antal våningar måste vara minst 1.")
    if not (0.0 <= inp.parking_ratio <= 2.0):
        notes.append("Parkeringstal/garagefaktor bör normalt ligga mellan 0 och 2.")
    if not (0.7 <= inp.atemp_to_bta <= 1.0):
        notes.append("Atemp/BTA bör normalt ligga mellan 0,7 och 1,0.")
    if inp.climate_improved_applicability < 0 or inp.climate_improved_applicability > 1:
        notes.append("Applicability för klimatförbättring måste ligga 0..1.")
    return tuple(notes)


def estimate(inp: ModelInputs, cfg: Optional[ModelConfig] = None) -> ModelResult:
    cfg = cfg or default_config()
    notes = list(_validate_inputs(inp))

    boundary = inp.system_boundary
    baseline = cfg.median_kg_per_m2[boundary]

    shares = cfg.shares_2022 if boundary == "2022" else cfg.shares_2027

    # 1) Basbidrag per byggdel (kg CO2e/m² BTA)
    breakdown = {k: baseline * v for k, v in shares.items()}

    # 2) Geometri: formfaktor påverkar främst klimatskärm (inkl. isolering)
    if "Klimatskärm" in breakdown:
        form_factor_scale = inp.form_factor / cfg.ref_form_factor

        # Om byggnadshöjd finns: justera klimatskärmen svagt via "våningshöjdfaktor".
        # (En grov proxy: högre våningshöjd -> mer fasadarea per BTA.)
        if inp.building_height_m and inp.floors > 0:
            ref_floor_height = 2.8  # m (heuristik)
            floor_height = inp.building_height_m / float(inp.floors)
            height_factor = max(0.8, min(1.3, floor_height / ref_floor_height))
        else:
            height_factor = 1.0

        # Fönsterandel: antag att fönster är r gånger mer klimatintensivt per m² än vägg.
        r = cfg.window_to_wall_intensity_ratio
        w = inp.window_ratio
        w0 = cfg.ref_window_ratio

        window_mix_factor = (w * r + (1 - w) * 1.0) / (w0 * r + (1 - w0) * 1.0)

        breakdown["Klimatskärm"] *= form_factor_scale * height_factor * window_mix_factor

    # 3) Antal våningar: låg byggnad tenderar att ge högre klimatpåverkan per m² (grund+klimatskärm).
    # I denna screeningmodell lägger vi en mild korrigering för våningar < 4.
    if inp.floors < 4:
        lowrise_factor = 1.0 + 0.05 * (4 - inp.floors)
        # lägg på grund + klimatskärm (de är oftast mer area-beroende)
        if "Grund" in breakdown:
            breakdown["Grund"] *= lowrise_factor
        if "Klimatskärm" in breakdown:
            breakdown["Klimatskärm"] *= lowrise_factor

    # 4) Stom- och metodval: påverkar "stomme+grund" dominerande.
    method_mult = cfg.method_multiplier.get(inp.method, 1.0)

    # Extra påslag för "tung betongdimensionering" (t.ex. massiva skalväggar)
    heavy_mult = 1.10 if inp.heavy_concrete_design else 1.0

    # Stomsystemfaktor: trä sänker ofta stomme/grund-relaterad klimatpåverkan.
    # Här modelleras det som en reduktion på de stomrelaterade delarna, inte på allt.
    if inp.structural_system == "Trä":
        # Trästomme: i KTH:s referensvärdesstudie är träbyggnader (exkl. småhus) tydligt lägre än betong/stål.
        # Vi applicerar därför en reduktion på de stomrelaterade byggdelarna. Storleken är kalibrerbar och
        # sätts lite olika för 2022/2027-systemgräns.
        system_struct_mult = 0.47 if boundary == "2022" else 0.51
    elif inp.structural_system == "Stål":
        system_struct_mult = 1.05
    else:
        system_struct_mult = 1.00

    # Applicera på relevanta byggdelar
    for key in ("Stomme", "Grund", "Innerväggar"):
        if key in breakdown:
            breakdown[key] *= method_mult * heavy_mult * system_struct_mult

    # 5) Under mark: källare och garage
    if inp.basement:
        breakdown["Grund"] = breakdown.get("Grund", 0.0) + cfg.basement_add_kg_per_m2_bta

    if inp.underground_garage:
        # Schablon från SBUF/IVL: +48 kg CO2e/m² Atemp vid parkeringstal ~0,5.
        add_kg_bta = (
            cfg.garage_add_kg_per_m2_atemp_parking05
            * inp.atemp_to_bta
            * (inp.parking_ratio / 0.5)
        )
        breakdown["Grund"] = breakdown.get("Grund", 0.0) + add_kg_bta

    # 6) Klimatförbättrade material (betong/stål/aluminium)
    if inp.climate_improved_materials:
        baseline_improved = cfg.median_kg_per_m2_climate_improved[boundary]
        baseline_generic = cfg.median_kg_per_m2[boundary]
        diff = max(0.0, baseline_generic - baseline_improved)

        # Reducera främst stomme+grund+klimatskärm (där betong/metal oftast dominerar)
        # proportionalt mot totalen, men med "applicability" (träbyggnader får ofta mindre effekt).
        affected_keys = ["Stomme", "Grund", "Klimatskärm"]
        affected_sum = sum(breakdown.get(k, 0.0) for k in affected_keys)
        total_pre = sum(breakdown.values())

        if total_pre > 0 and affected_sum > 0:
            # Skala reduktionen med hur mycket totalen har ändrats från baseline
            scale = total_pre / baseline_generic
            target_reduction = diff * scale * inp.climate_improved_applicability

            # Fördela reduktionen proportionellt över påverkade nycklar
            for k in affected_keys:
                if k in breakdown:
                    breakdown[k] -= target_reduction * (breakdown[k] / affected_sum)
                    breakdown[k] = max(0.0, breakdown[k])
        else:
            notes.append("Kunde inte applicera klimatförbättring (noll/negativt delbidrag).")

    total = sum(breakdown.values())

    # Virkeandel
    if inp.timber_t_per_m2_override is not None:
        timber_t = max(0.0, float(inp.timber_t_per_m2_override))
    else:
        timber_t = cfg.timber_t_per_m2_default_by_system[inp.structural_system]

    ref = 375.0  # Boverkets föreslagna (avrundade) median/gränsvärde för flerbostadshus (kg/m² BTA)
    delta = total - ref
    delta_pct = (delta / ref) * 100.0

    return ModelResult(
        total_kg_per_m2_bta=total,
        total_t_per_m2_bta=total / 1000.0,
        reference_kg_per_m2_bta=ref,
        delta_vs_reference_kg=delta,
        delta_vs_reference_percent=delta_pct,
        breakdown_kg_per_m2_bta=breakdown,
        timber_t_per_m2_bta=timber_t,
        notes=tuple(notes),
    )
