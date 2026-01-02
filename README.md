# Klimatmodell (Streamlit) – flerbostadshus (A1–A5)

Detta är en **screeningmodell** (tidigt skede) som uppskattar klimatpåverkan i byggskedet enligt
modul **A1–A5** i enheten **kg CO₂e/m² BTA** och **ton CO₂e/m² BTA**.

> ⚠️ Modellen ersätter inte en riktig klimatdeklaration/LCA och är inte ett officiellt verktyg.
> Den är byggd för att vara **transparent, snabb och justerbar**.

## Vad modellen gör
- Utgår från medianvärden för flerbostadshus (A1–A5) för två systemgränser:
  - **2022**: klimatskärm + bärande konstruktionsdelar + innerväggar (i linje med klimatdeklarationens systemgräns)
  - **2027**: utökad systemgräns (+ invändiga ytskikt/fast inredning samt tekniska installationer)
- Skalar resultatet med parametrar:
  - formfaktor (Aom/BTA)
  - fönsterandel
  - stomsystem & konstruktionsmetod
  - källare / underliggande garage
  - klimatförbättrade material (betong/stål/aluminium – kalibrerat mot KTH-scenario)
- Ger även en **screening** av virkesandel (ton virke/m² BTA).

## Kör lokalt
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy på Streamlit Community Cloud (via GitHub)
1. Skapa ett nytt GitHub-repo och lägg in filerna i detta projekt.
2. Säkerställ att repo innehåller:
   - `app.py`
   - `climate_model.py`
   - `requirements.txt`
3. Gå till Streamlit Community Cloud och välj:
   - **Repository**: ditt repo
   - **Branch**: main
   - **Main file path**: `app.py`

## Kalibrering / justering
De viktigaste antagandena och schablonerna ligger i `climate_model.py`:
- byggdelsandelar (`shares_2022`, `shares_2027`)
- metodmultiplikatorer (`method_multiplier`)
- fönster/vägg-intensitetskvot (`window_to_wall_intensity_ratio`)
- schablon för garagepåslag (`garage_add_kg_per_m2_atemp_parking05`)

För bästa träffsäkerhet:
- justera andelar och multiplikatorer mot er egen mängdning/LCA
- byt ut referensnivåer mot egna (t.ex. egna medianer eller portföljdata)

## Referenser (urval)
- KTH/WSP/IVL: *Referensvärden för klimatpåverkan vid uppförande av byggnader. Version 2, 2023.*
  (Tabell 9: medianer för flerbostadshus, samt scenario med klimatförbättrade produktval)
  https://kth.diva-portal.org/smash/get/diva2:1744370/FULLTEXT01.pdf

- Boverket: *Gränsvärde för byggnaders klimatpåverkan och en utökad klimatdeklaration* (Rapport 2023:20)
  https://www.boverket.se/sv/om-boverket/publicerat-av-boverket/publikationer/2023/gransvarde-for-byggnaders-klimatpaverkan-och-en-utokad-klimatdeklaration/

- Boverket: PM (2023-11-28) om komplettering/översyn av gränsvärden och referensvärden
  https://www.regeringen.se/contentassets/85f6dddd3ea4429e999ca1b2a7cae405/boverket-pm-komplettering-gransvarden-for-byggnaders-klimatpaverkan.pdf

- Byggföretagen/SBUF/IVL/KTH: *Minskad klimatpåverkan från nybyggda flerbostadshus* (jämförande LCA av fem byggsystem)
  (Tabell med A1–A5 samt schablon för garagepåslag)
  https://byggforetagen.se/app/uploads/2020/02/Minskad-klimatp%C3%A5verkan-fr%C3%A5n-nybyggda-flerbostadshus.pdf
