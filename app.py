# app.py
import streamlit as st
import pyttsx3
import pandas as pd
from datetime import datetime
import random
import json
from pathlib import Path

# Config

st.set_page_config(page_title="AI Quran Chatbot (Full Offline)", layout="wide")
st.title("🕌 AI Quran Chatbot")

DATA_FILE = Path("quran_data_full.json")

if not DATA_FILE.exists():
    st.error("quran_data_full.json not found. Please run 'python build_quran_json.py' first to generate the dataset.")
    st.stop()

with open(DATA_FILE, "r", encoding="utf-8") as f:
    quran = json.load(f)  

# Normalize keys to int
quran_by_number = {int(k): v for k,v in quran.items()}

# Voice engine
engine = pyttsx3.init()
voices = engine.getProperty("voices")
arabic_voice_id = None
for v in voices:
    if "arabic" in v.name.lower() or "hussain" in v.name.lower() or "middle east" in v.name.lower():
        arabic_voice_id = v.id
        break
if arabic_voice_id:
    engine.setProperty("voice", arabic_voice_id)
else:
    engine.setProperty("rate", 140)
engine.setProperty("volume", 1.0)

# UI
st.markdown("**Assalamu Alaikum!** — This app uses a local JSON file with the full Qur'an (Arabic + translations).")

col1, col2 = st.columns([2,1])
with col1:
    q_text = st.text_area("Ask your question (English/Urdu) or search by Surah/Ayah:",
                          placeholder="Example: What does the Quran say about patience?  OR  Surah:2 Ayah:255")
with col2:
    sel_surah = st.selectbox("Browse Surah", options=[f"{n} - {quran_by_number[n]['name_en'] or quran_by_number[n]['name_ar']}" for n in sorted(quran_by_number.keys())])
    btn_go = st.button("Load Surah")

# Helper to parse surah selection
def parse_surah_string(s):
    return int(s.split(" - ", 1)[0])

# Load surah display
if btn_go:
    surah_num = parse_surah_string(sel_surah)
    s = quran_by_number[surah_num]
    st.header(f"Surah {s['number']}: {s.get('name_en') or s.get('name_ar')}")
    ayahs = s['ayahs']
    for ay in ayahs:
        st.markdown(f"**Ayah {ay['numberInSurah']}:**")
        st.markdown(f"*Arabic:* {ay.get('text_ar')}")
        if ay.get('text_en'):
            st.markdown(f"*English:* {ay.get('text_en')}")
        if ay.get('text_ur'):
            st.markdown(f"*Urdu:* {ay.get('text_ur')}")
        st.markdown("---")

# Chat / question handling
if st.button("Get Insight / Verse"):
    if not q_text.strip():
        st.warning("Type a question or 'Surah:2 Ayah:255' style lookup.")
    else:
        # Try simple surah:ayah pattern
        import re
        m = re.search(r"surah[:\s]*([0-9]{1,3})\s*ayah[:\s]*([0-9]{1,3})", q_text.lower())
        if m:
            sn = int(m.group(1)); an = int(m.group(2))
            if sn in quran_by_number and 1 <= an <= len(quran_by_number[sn]['ayahs']):
                ay = quran_by_number[sn]['ayahs'][an-1]
                st.subheader(f"Surah {sn} Ayah {an}")
                st.markdown(f"**Arabic:** {ay.get('text_ar')}")
                if ay.get('text_en'): st.markdown(f"**English:** {ay.get('text_en')}")
                if ay.get('text_ur'): st.markdown(f"**Urdu:** {ay.get('text_ur')}")
                # Save history
                _hist = {"time": datetime.utcnow().isoformat(), "query": q_text, "result": f"Surah {sn} Ayah {an}"}
                st.session_state.setdefault("history", []).append(_hist)
            else:
                st.error("Surah or Ayah number out of range.")
        else:
            # Simple keyword search (best-effort)
            q_lower = q_text.lower()
            found = []
            for sn, s in quran_by_number.items():
                for ay in s['ayahs']:
                    # Check in any of the texts
                    if (ay.get('text_en') and q_lower in ay['text_en'].lower()) or \
                       (ay.get('text_ur') and q_lower in ay['text_ur'].lower()) or \
                       (ay.get('text_ar') and q_lower in ay['text_ar'].lower()):
                        found.append((sn, ay))
                    if len(found) >= 6:
                        break
                if len(found) >= 6:
                    break
            if found:
                st.subheader("Found related verses (best-effort):")
                for sn, ay in found[:6]:
                    st.markdown(f"**Surah {sn} Ayah {ay['numberInSurah']}**")
                    st.markdown(f"*Arabic:* {ay.get('text_ar')}")
                    if ay.get('text_en'): st.markdown(f"*English:* {ay.get('text_en')}")
                    if ay.get('text_ur'): st.markdown(f"*Urdu:* {ay.get('text_ur')}")
                    st.markdown("---")
                st.session_state.setdefault("history", []).append({"time": datetime.utcnow().isoformat(), "query": q_text, "result": "found_related"})
            else:
                st.info("No exact matches found. You can try simpler keywords like 'patience', 'charity', or do Surah:2 Ayah:255 style lookup.")
# Play last found Arabic Ayah
if st.button("Recite Last Found Arabic"):
    # fetch last found ayah from history
    h = st.session_state.get("history", [])
    if not h:
        st.warning("No history found. Perform a lookup first.")
    else:
        
        last = h[-1]
        import re
        m = re.search(r"surah\s+([0-9]{1,3})\s+ayah\s+([0-9]{1,3})", last.get("result",""), re.I)
        if m:
            sn = int(m.group(1)); an = int(m.group(2))
            ay = quran_by_number[sn]['ayahs'][an-1]
            text_ar = ay.get('text_ar')
            if text_ar:
                engine.say(text_ar)
                engine.runAndWait()
                st.info(f"Recited Surah {sn} Ayah {an}")
            else:
                st.warning("Arabic text not found for that Ayah.")
        else:
            st.warning("Last result was not a direct Surah:Ayah lookup. Use 'Surah:x Ayah:y' lookup first.")

# History display
if "history" in st.session_state and st.session_state["history"]:
    st.divider()
    st.subheader("History")
    df = pd.DataFrame(st.session_state["history"])
    st.dataframe(df)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download History CSV", csv, "quran_history.csv", "text/csv")

st.markdown("---")
st.caption("Developed by Asma — offline Quran data loaded from quran_data_full.json")

