import streamlit as st
import pandas as pd
from dataclasses import replace

from climate_model import ModelInputs, estimate, default_config


st.set_page_config(
    page_title="Klimatmodell – flerbostadshus (A1-A5)",
    page_icon="🏢",
    layout="wide",
)

st.title("🏢 Screeningmodell: Klimatpåverkan för flerbostadshus (A1–A5)")
st.caption(
    "En förenklad, transparent modell för tidiga skeden. "
    "Resultaten ska ses som en indikation och behöver kalibreras mot projektspecifik mängdning/LCA."
)

cfg = default_config()

with st.sidebar:
    st.header("Indata")

    system_boundary = st.selectbox(
        "Systemgräns för byggdelar",
        options=["2022", "2027"],
        format_func=lambda x: (
            "2022 (klimatdeklaration: klimatskärm + bärande + innerväggar)"
            if x == "2022"
            else "2027 (utökad: + ytskikt/inredning + installationer)"
        ),
    )

    st.subheader("Geometri")
    form_factor = st.slider(
        "Formfaktor (Aom/BTA)",
        min_value=0.25,
        max_value=1.20,
        value=float(cfg.ref_form_factor),
        step=0.01,
        help="Aom ≈ omslutningsarea. Högre formfaktor betyder mer klimatskärm per m² BTA.",
    )

    window_ratio = st.slider(
        "Fönsterandel av fasad (%)",
        min_value=5,
        max_value=70,
        value=int(cfg.ref_window_ratio * 100),
        step=1,
    ) / 100.0

    r_win = st.slider(
        "Relativ klimatintensitet: fönster vs vägg (r)",
        min_value=1.5,
        max_value=8.0,
        value=float(cfg.window_to_wall_intensity_ratio),
        step=0.1,
        help="r=4 betyder att 1 m² fönster antas ge ~4× klimatpåverkan jämfört med 1 m² vägg. Justera vid kalibrering.",
    )
    cfg = replace(cfg, window_to_wall_intensity_ratio=r_win)

    st.subheader("Byggnad")
    floors = st.slider("Antal våningar ovan mark", 1, 16, 6, 1)
    building_height_m = st.number_input(
        "Byggnadshöjd (m) (valfritt)", min_value=0.0, value=0.0, step=0.5
    )
    if building_height_m <= 0:
        building_height_m = None

    st.subheader("Stomme & konstruktionsmetod")
    structural_system = st.selectbox("Stomsystem", options=["Betong", "Trä", "Stål"], index=0)

    if structural_system == "Betong":
        method = st.selectbox(
            "Konstruktionsmetod (stomme)",
            options=[
                "Prefabricerad betong",
                "Platsgjuten betong (lätta utfackningsväggar)",
                "Platsgjuten betong (kvarsittande form)",
            ],
        )
    elif structural_system == "Trä":
        method = st.selectbox(
            "Konstruktionsmetod (stomme)",
            options=[
                "Volymelement i trä",
                "KL-trä (massiv stomme)",
            ],
        )
    else:
        method = st.selectbox(
            "Konstruktionsmetod (stomme)",
            options=[
                "Prefabricerad betong",
                "Platsgjuten betong (lätta utfackningsväggar)",
            ],
        )

    heavy_concrete_design = st.checkbox(
        "Tung betongdimensionering (t.ex. massiva skalväggar)",
        value=False,
        help="Ger ett schablonpåslag på stomme/grund/innerväggar.",
    )

    st.subheader("Materialval")
    climate_improved = st.checkbox(
        "Klimatförbättrade material (betong/stål/aluminium)",
        value=False,
        help="Minskar betong/metal-dominerade delar. Kalibrerat mot KTH:s scenario för klimatförbättrade produktval.",
    )
    climate_improved_applicability = st.slider(
        "Applicability (0–100%)",
        min_value=0,
        max_value=100,
        value=100 if structural_system != "Trä" else 60,
        step=5,
        help="Hur stor del av klimatförbättringen som antas vara relevant. Trästomme får ofta lägre effekt eftersom mindre betong/stål används.",
    ) / 100.0

    st.subheader("Under mark")
    basement = st.checkbox("Källare (utan garage)", value=False)
    underground_garage = st.checkbox("Underliggande garage", value=False)
    parking_ratio = st.slider("Garagefaktor (parkeringstal rel. 0,5)", 0.0, 1.5, 0.5, 0.05)
    atemp_to_bta = st.slider("Antaget Atemp/BTA", 0.75, 0.98, 0.90, 0.01)

    st.subheader("Virkesandel")
    timber_override = st.number_input(
        "Override: ton virke/m² BTA (valfritt)",
        min_value=0.0,
        value=0.0,
        step=0.005,
        help="Lämna 0 för default-schablon.",
    )
    if timber_override <= 0:
        timber_override = None

    st.markdown("---")
    st.caption("Tips: Justera antaganden i climate_model.py om du vill kalibrera modellen mot egen LCA.")


inp = ModelInputs(
    system_boundary=system_boundary,
    form_factor=float(form_factor),
    window_ratio=float(window_ratio),
    floors=int(floors),
    building_height_m=building_height_m,
    structural_system=structural_system,
    method=method,
    heavy_concrete_design=heavy_concrete_design,
    climate_improved_materials=climate_improved,
    climate_improved_applicability=float(climate_improved_applicability),
    basement=basement,
    underground_garage=underground_garage,
    parking_ratio=float(parking_ratio),
    atemp_to_bta=float(atemp_to_bta),
    timber_t_per_m2_override=timber_override,
)

res = estimate(inp, cfg)

col1, col2, col3 = st.columns([1.2, 1, 1])
with col1:
    st.metric(
        "Estimerad klimatpåverkan",
        f"{res.total_t_per_m2_bta:.3f} ton CO₂e/m² BTA",
        help="Beräknat som kg CO2e/m² BTA / 1000.",
    )
    st.caption(f"({res.total_kg_per_m2_bta:.0f} kg CO₂e/m² BTA)")

with col2:
    st.metric(
        "Jämfört med 0,375 ton CO₂e/m² BTA",
        f"{res.delta_vs_reference_kg:+.0f} kg",
        f"{res.delta_vs_reference_percent:+.1f} %",
        help="Referensen 0,375 ton (=375 kg) används som jämförelse (Boverkets förslag).",
    )

with col3:
    st.metric(
        "Virkesandel (screening)",
        f"{res.timber_t_per_m2_bta:.3f} ton/m² BTA",
    )

st.subheader("Nedbrytning (kg CO₂e/m² BTA)")
df = pd.DataFrame(
    {
        "Byggdel": list(res.breakdown_kg_per_m2_bta.keys()),
        "kg CO2e/m² BTA": list(res.breakdown_kg_per_m2_bta.values()),
    }
).sort_values("kg CO2e/m² BTA", ascending=False)

st.dataframe(df, use_container_width=True, hide_index=True)
st.bar_chart(df.set_index("Byggdel"))

with st.expander("🔎 Antaganden & begränsningar"):
    st.markdown(
        """
- Modellen utgår från en median-referensnivå för flerbostadshus och skalar denna med enkla multiplikatorer.
- Effekten av formfaktor och fönsterandel modelleras via klimatskärmsbidraget (Aom/BTA och fönster/vägg-mix).
- Garagepåslag bygger på en schablon (+48 kg CO₂e/m² Atemp vid parkeringstal 0,5) och konverteras via Atemp/BTA.
- Klimatförbättring bygger på skillnaden mellan median med 'svenskt medelvärde' och 'klimatförbättrade produktval'
  i KTH:s referensvärdesrapport, för vald systemgräns.
- För riktiga klimatdeklarationer krävs projektspecifik resurssammanställning och klimatdata (EPD/generiska data).
"""
    )
    if res.notes:
        st.warning("Notiser:\n- " + "\n- ".join(res.notes))
    else:
        st.info("Inga notiser för dessa indata.")

with st.expander("📚 Källor (översikt)"):
    st.markdown(
        """
Modellen är kalibrerad mot och inspirerad av bl.a.:
- KTH/WSP/IVL: *Referensvärden för klimatpåverkan vid uppförande av byggnader* (Tabell 9 m.fl.)
- Boverket: rapporter/PM om gränsvärden och referensvärden för byggnaders klimatpåverkan
- SBUF/IVL/Byggföretagen: jämförande LCA för fem byggsystem (typhus) samt schablon för garagepåslag
"""
    )
