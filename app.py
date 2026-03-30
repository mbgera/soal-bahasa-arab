import streamlit as st
import google.generativeai as genai
import os
import json
import re
from datetime import datetime
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import requests

# ========== INISIALISASI UNTUK MULTIPLE PROVIDER ==========
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Konfigurasi halaman
st.set_page_config(
    page_title="Soal Bahasa Arab SMP/MTs",
    page_icon="📖",
    layout="wide"
)

# ========== INISIALISASI SESSION STATE UNTUK DATABASE KI/KD ==========
if 'ki_kd_database' not in st.session_state:
    st.session_state.ki_kd_database = [
        {
            "id": 1,
            "kelas": "7",
            "ki": "KI-1: Menghargai dan menghayati ajaran agama yang dianutnya",
            "kd": "3.1 Memahami fungsi sosial, struktur teks, dan unsur kebahasaan pada teks tentang التعارف (perkenalan)",
            "keterangan": "Perkenalan Diri"
        },
        {
            "id": 2,
            "kelas": "7",
            "ki": "KI-3: Memahami pengetahuan faktual, konseptual, dan prosedural",
            "kd": "3.2 Memahami fungsi sosial, struktur teks, dan unsur kebahasaan pada teks tentang المدرسة (sekolah)",
            "keterangan": "Lingkungan Sekolah"
        },
        {
            "id": 3,
            "kelas": "8",
            "ki": "KI-3: Memahami pengetahuan faktual, konseptual, dan prosedural",
            "kd": "3.1 Memahami fungsi sosial, struktur teks, dan unsur kebahasaan pada teks tentang الحي (lingkungan rumah)",
            "keterangan": "Lingkungan Rumah"
        },
        {
            "id": 4,
            "kelas": "9",
            "ki": "KI-3: Memahami pengetahuan faktual, konseptual, dan prosedural",
            "kd": "3.1 Memahami fungsi sosial, struktur teks, dan unsur kebahasaan pada teks tentang التكنولوجيا (teknologi)",
            "keterangan": "Teknologi Informasi"
        }
    ]

# Judul
st.title("📖 Generator Soal Bahasa Arab SMP/MTs")
st.markdown("Ditenagai **Multi AI** | Berbasis **Taksonomi Bloom** | **6 Tipe Soal** | **Kontrol Penuh**")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    # ========== PILIH AI PROVIDER ==========
    st.header("🤖 Pilih AI Provider")
    
    ai_provider = st.selectbox(
        "Model AI",
        ["Gemini (Google)", "DeepSeek", "OpenAI GPT", "Maia Router"],
        help="Pilih AI yang akan digunakan untuk membuat soal"
    )
    
    # Input API Key sesuai provider
    if ai_provider == "Gemini (Google)":
        api_key = st.text_input(
            "🔑 Masukkan API Key Gemini",
            type="password",
            placeholder="AIzaSy...",
            help="Dapatkan gratis di https://aistudio.google.com/"
        )
        st.caption("💡 Free tier: 15 request/menit")
        deepseek_model = ""
        openai_model = ""
        maia_endpoint = ""
        maia_model = ""
    
    elif ai_provider == "DeepSeek":
        api_key = st.text_input(
            "🔑 Masukkan API Key DeepSeek",
            type="password",
            placeholder="sk-...",
            help="Dapatkan di https://platform.deepseek.com/"
        )
        st.caption("💡 Harga sangat murah: ~$0.14/1M token")
        deepseek_model = st.selectbox(
            "Model DeepSeek",
            ["deepseek-chat", "deepseek-reasoner"]
        )
        openai_model = ""
        maia_endpoint = ""
        maia_model = ""
    
    elif ai_provider == "OpenAI GPT":
        api_key = st.text_input(
            "🔑 Masukkan API Key OpenAI",
            type="password",
            placeholder="sk-...",
            help="Dapatkan di https://platform.openai.com/"
        )
        st.caption("💡 Perlu kartu kredit")
        openai_model = st.selectbox(
            "Model OpenAI",
            ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
        )
        deepseek_model = ""
        maia_endpoint = ""
        maia_model = ""
    
    elif ai_provider == "Maia Router":
        api_key = st.text_input(
            "🔑 Masukkan API Key Maia Router",
            type="password",
            placeholder="your-api-key-here"
        )
        st.caption("💡 Router AI dengan akses ke berbagai model")
        maia_endpoint = st.text_input(
            "🌐 Endpoint API Maia Router",
            placeholder="https://api.maiarouter.com/v1/chat/completions"
        )
        maia_model = st.selectbox(
            "Model yang Dirutekan",
            ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro", "auto"]
        )
        deepseek_model = ""
        openai_model = ""
    
    st.markdown("---")
    
    # ========== KELOLA KI/KD ==========
    with st.expander("📚 Kelola Database KI/KD", expanded=False):
        st.markdown("**Tambah KI/KD Baru**")
        
        col_kelas, col_keterangan = st.columns(2)
        with col_kelas:
            kelas_baru = st.selectbox("Kelas", ["7", "8", "9"], key="kelas_baru")
        with col_keterangan:
            keterangan_baru = st.text_input("Keterangan (opsional)", placeholder="Contoh: Bab 1 Perkenalan")
        
        ki_baru = st.text_area(
            "Kompetensi Inti (KI)",
            placeholder="Contoh: KI-3: Memahami pengetahuan faktual, konseptual, dan prosedural",
            height=60
        )
        
        kd_baru = st.text_area(
            "Kompetensi Dasar (KD)",
            placeholder="Contoh: 3.1 Memahami fungsi sosial, struktur teks, dan unsur kebahasaan pada teks tentang التعارف",
            height=80
        )
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ Tambah KI/KD", use_container_width=True):
                if ki_baru and kd_baru:
                    new_id = max([item["id"] for item in st.session_state.ki_kd_database]) + 1 if st.session_state.ki_kd_database else 1
                    st.session_state.ki_kd_database.append({
                        "id": new_id,
                        "kelas": kelas_baru,
                        "ki": ki_baru,
                        "kd": kd_baru,
                        "keterangan": keterangan_baru
                    })
                    st.success(f"✅ KI/KD untuk kelas {kelas_baru} berhasil ditambahkan!")
                    st.rerun()
                else:
                    st.error("❌ KI dan KD harus diisi!")
        
        st.markdown("---")
        st.markdown("**📋 Daftar KI/KD Tersimpan**")
        
        filter_kelas = st.selectbox("Filter Kelas", ["Semua", "7", "8", "9"], key="filter_kelas")
        
        filtered_data = st.session_state.ki_kd_database
        if filter_kelas != "Semua":
            filtered_data = [item for item in filtered_data if item["kelas"] == filter_kelas]
        
        for item in filtered_data:
            with st.container():
                col_del, col_edit = st.columns([5, 1])
                with col_del:
                    st.markdown(f"**Kelas {item['kelas']}** {f'- {item['keterangan']}' if item['keterangan'] else ''}")
                    st.caption(f"KI: {item['ki'][:80]}...")
                    st.caption(f"KD: {item['kd'][:80]}...")
                with col_edit:
                    if st.button("🗑️", key=f"del_{item['id']}"):
                        st.session_state.ki_kd_database = [i for i in st.session_state.ki_kd_database if i["id"] != item["id"]]
                        st.rerun()
            st.divider()
    
    st.markdown("---")
    
    # ========== PILIH KI/KD YANG AKAN DIGUNAKAN ==========
    st.header("📖 Pilih KI/KD")
    
    ki_kd_options = []
    for item in st.session_state.ki_kd_database:
        label = f"Kelas {item['kelas']}: {item['keterangan'] if item['keterangan'] else item['kd'][:50]}..."
        ki_kd_options.append({
            "label": label,
            "id": item["id"],
            "kelas": item["kelas"],
            "ki": item["ki"],
            "kd": item["kd"]
        })
    
    if ki_kd_options:
        selected_index = st.selectbox(
            "Pilih KI/KD yang akan digunakan",
            options=range(len(ki_kd_options)),
            format_func=lambda x: ki_kd_options[x]["label"]
        )
        
        selected_ki_kd = ki_kd_options[selected_index]
        
        st.info(f"**KI:** {selected_ki_kd['ki']}")
        st.info(f"**KD:** {selected_ki_kd['kd']}")
        
        kelas = selected_ki_kd["kelas"]
        ki = selected_ki_kd["ki"]
        kd = selected_ki_kd["kd"]
    else:
        st.warning("⚠️ Belum ada data KI/KD. Silakan tambahkan terlebih dahulu!")
        kelas = "7"
        ki = ""
        kd = ""
    
    st.markdown("---")
    
    # ========== MODE PEMBUATAN SOAL ==========
    st.header("🎯 Mode Pembuatan Soal")
    
    mode_pembuatan = st.radio(
        "Pilih Mode",
        ["AI Bebas (Buat Sendiri)", "Ikuti Contoh Soal (Parafrase)"]
    )
    
    contoh_soal = ""
    if mode_pembuatan == "Ikuti Contoh Soal (Parafrase)":
        st.markdown("---")
        st.header("📋 Contoh Soal (Wajib Diisi)")
        contoh_soal = st.text_area(
            "**Contoh Soal**",
            placeholder="""1. أَهْلًا وَسَهْلًا
   Arti dari ungkapan di atas adalah...
   A. Selamat pagi
   B. Selamat datang
   C. Selamat malam
   D. Selamat tinggal
   Jawaban: B""",
            height=150
        )
    
    st.markdown("---")
    
    # ========== INPUT MATERI KHUSUS ==========
    st.header("📚 Materi & Kompetensi")
    
    sumber_materi = st.radio(
        "Sumber Materi",
        ["Sesuai KI/KD Saja", "Dengan Materi Khusus (Teks/Topik)"]
    )
    
    teks_bacaan = ""
    terjemahan = ""
    topik_khusus = ""
    tampilan_bacaan = "Tidak menampilkan teks bacaan (hanya soal)"
    
    if sumber_materi == "Dengan Materi Khusus (Teks/Topik)":
        st.markdown("**📖 Materi Khusus**")
        teks_bacaan = st.text_area("Teks Bacaan (Arab)", height=120)
        terjemahan = st.text_area("Terjemahan (opsional)", height=80)
        topik_khusus = st.text_input("Topik Khusus (opsional)")
        tampilan_bacaan = st.radio(
            "Tampilan Teks Bacaan",
            ["Teks bacaan ditampilkan di atas semua soal", 
             "Teks bacaan hanya ditampilkan pada soal berbasis teks saja",
             "Tidak menampilkan teks bacaan (hanya soal)"]
        )
    
    topik = topik_khusus if topik_khusus else st.text_input("Topik Umum", placeholder="Contoh: التعارف")
    
    st.markdown("---")
    st.header("📝 Pilih Tipe Soal")
    
    col1, col2 = st.columns(2)
    with col1:
        tipe_pg = st.checkbox("PG Biasa (1 jawaban)", value=True)
        tipe_pg_kompleks = st.checkbox("PG Kompleks (>1 jawaban)", value=True)
        tipe_menjodohkan = st.checkbox("Menjodohkan (2 kolom)", value=True)
    with col2:
        tipe_benar_salah = st.checkbox("Benar/Salah", value=True)
        tipe_teks = st.checkbox("PG Berbasis Teks", value=True)
    
    st.markdown("---")
    st.header("🎯 Level Taksonomi Bloom")
    
    bloom_options = [
        "C1 - Mengingat (Remembering)",
        "C2 - Memahami (Understanding)",
        "C3 - Menerapkan (Applying)",
        "C4 - Menganalisis (Analyzing)",
        "C5 - Mengevaluasi (Evaluating)",
        "C6 - Menciptakan (Creating)"
    ]
    
    bloom_levels = st.multiselect(
        "Pilih Level Kognitif",
        bloom_options,
        default=["C1 - Mengingat (Remembering)", "C2 - Memahami (Understanding)"]
    )
    
    st.markdown("---")
    st.header("📊 Jumlah Soal per Tipe")
    
    if mode_pembuatan == "Ikuti Contoh Soal (Parafrase)":
        st.info("📌 Mode 'Ikuti Contoh'")
        jumlah_soal_input = st.number_input("Jumlah Soal", min_value=1, max_value=20, value=5)
        jumlah_pg = jumlah_soal_input if tipe_pg else 0
        jumlah_pg_kompleks = jumlah_soal_input if tipe_pg_kompleks else 0
        jumlah_menjodohkan = jumlah_soal_input if tipe_menjodohkan else 0
        jumlah_benar_salah = jumlah_soal_input if tipe_benar_salah else 0
        jumlah_teks = jumlah_soal_input if tipe_teks else 0
    else:
        jumlah_pg = st.number_input("PG Biasa", min_value=0, max_value=10, value=2) if tipe_pg else 0
        jumlah_pg_kompleks = st.number_input("PG Kompleks", min_value=0, max_value=10, value=1) if tipe_pg_kompleks else 0
        jumlah_menjodohkan = st.number_input("Menjodohkan", min_value=0, max_value=5, value=1) if tipe_menjodohkan else 0
        jumlah_benar_salah = st.number_input("Benar/Salah", min_value=0, max_value=10, value=2) if tipe_benar_salah else 0
        jumlah_teks = st.number_input("PG Berbasis Teks", min_value=0, max_value=10, value=1) if tipe_teks else 0
    
    total_soal = jumlah_pg + jumlah_pg_kompleks + jumlah_menjodohkan + jumlah_benar_salah + jumlah_teks
    st.info(f"📊 Total soal: **{total_soal}**")
    
    st.markdown("---")
    st.header("✏️ Opsi Edit")
    enable_edit = st.checkbox("Tampilkan editor soal setelah generate", value=True)
    
    st.markdown("---")
    tombol = st.button("🚀 Buat Soal!", type="primary", use_container_width=True)

# ========== FUNGSI GENERATE SOAL ==========
def buat_soal(api_key, prompt, ai_provider, deepseek_model="", openai_model="", maia_endpoint="", maia_model=""):
    try:
        if ai_provider == "Gemini (Google)":
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            response_text = response.text
        
        elif ai_provider == "DeepSeek":
            if not OPENAI_AVAILABLE:
                return None, "Library openai belum terinstall"
            client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
            response = client.chat.completions.create(
                model=deepseek_model,
                messages=[
                    {"role": "system", "content": "Anda adalah guru Bahasa Arab ahli. Buat soal dalam format JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            response_text = response.choices[0].message.content
        
        elif ai_provider == "OpenAI GPT":
            if not OPENAI_AVAILABLE:
                return None, "Library openai belum terinstall"
            client = OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
            response = client.chat.completions.create(
                model=openai_model,
                messages=[
                    {"role": "system", "content": "Anda adalah guru Bahasa Arab ahli. Buat soal dalam format JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            response_text = response.choices[0].message.content
        
        elif ai_provider == "Maia Router":
            if not maia_endpoint:
                maia_endpoint = "https://api.maiarouter.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            payload = {
                "model": maia_model,
                "messages": [
                    {"role": "system", "content": "Anda adalah guru Bahasa Arab ahli. Buat soal dalam format JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 4000
            }
            response = requests.post(maia_endpoint, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                response_data = response.json()
                response_text = response_data['choices'][0]['message']['content']
            else:
                return None, f"Error: {response.status_code}"
        
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data, None
        else:
            return None, "Tidak ada format JSON"
            
    except Exception as e:
        return None, str(e)

# ========== FUNGSI MEMBANGUN PROMPT ==========
def build_prompt(ki, kd, kelas, topik, bloom_levels, tipe_config, sumber_materi, teks_bacaan, terjemahan, mode_pembuatan, contoh_soal, tampilan_bacaan, total_soal):
    materi_khusus = ""
    if sumber_materi == "Dengan Materi Khusus (Teks/Topik)" and teks_bacaan:
        instruksi = "Teks bacaan WAJIB ditampilkan di AWAL" if tampilan_bacaan == "Teks bacaan ditampilkan di atas semua soal" else "Teks bacaan HANYA untuk soal berbasis teks" if tampilan_bacaan == "Teks bacaan hanya ditampilkan pada soal berbasis teks saja" else "Teks bacaan TIDAK ditampilkan"
        materi_khusus = f"Teks Bacaan: {teks_bacaan}\nTerjemahan: {terjemahan}\n{instruksi}"
    
    bagian_contoh = ""
    if mode_pembuatan == "Ikuti Contoh Soal (Parafrase)" and contoh_soal:
        bagian_contoh = f"IKUTI FORMAT CONTOH INI:\n{contoh_soal}\nBuat {total_soal} soal dengan format SAMA persis."
    
    prompt = f"""Anda guru Bahasa Arab SMP/MTs.

KI: {ki}
KD: {kd}
Kelas: {kelas}
Topik: {topik}
{materi_khusus}
{bagian_contoh}

Level Bloom: {', '.join(bloom_levels)}

Tipe Soal dan Jumlah:
- PG Biasa: {tipe_config.get('jumlah_pg', 0)}
- PG Kompleks: {tipe_config.get('jumlah_pg_kompleks', 0)}
- Menjodohkan: {tipe_config.get('jumlah_menjodohkan', 0)}
- Benar/Salah: {tipe_config.get('jumlah_benar_salah', 0)}
- PG Berbasis Teks: {tipe_config.get('jumlah_teks', 0)}

Output JSON:
{{
  "metadata": {{"kelas": "{kelas}", "topik": "{topik}"}},
  "soal": [
    {{
      "nomor": 1,
      "tipe": "Pilihan Ganda Biasa",
      "bloom_level": "C1 - Mengingat",
      "teks_arab": "...",
      "teks_indonesia": "...",
      "pilihan": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "jawaban": "A",
      "pembahasan": "..."
    }}
  ]
}}"""
    return prompt

# ========== FUNGSI TAMPILAN SOAL ==========
def display_question(soal, nomor, tampilan_bacaan, teks_bacaan_global, terjemahan_global, sudah_tampil):
    if tampilan_bacaan == "Teks bacaan ditampilkan di atas semua soal" and nomor == 1 and not sudah_tampil and teks_bacaan_global:
        st.markdown("### 📖 Teks Bacaan")
        st.markdown(f"<div dir='rtl' style='background:#e9ecef;padding:15px;border-radius:10px'>{teks_bacaan_global}</div>", unsafe_allow_html=True)
        if terjemahan_global:
            st.markdown(f"**Terjemahan:** {terjemahan_global}")
        st.markdown("---")
        return True
    
    tipe = soal.get('tipe', '')
    if tipe in ['Pilihan Ganda Biasa', 'PG Biasa']:
        st.markdown(f"**{nomor}. {soal.get('teks_indonesia', '')}**")
        if soal.get('teks_arab'):
            st.markdown(f"<div dir='rtl' style='background:#f0f2f6;padding:10px;border-radius:10px'>{soal['teks_arab']}</div>", unsafe_allow_html=True)
        for key, value in soal.get('pilihan', {}).items():
            st.write(f"**{key}.** {value}")
        with st.expander("🔑 Kunci Jawaban"):
            st.info(f"Jawaban: **{soal['jawaban']}**")
    
    elif tipe in ['Pilihan Ganda Kompleks', 'PG Kompleks']:
        st.markdown(f"**{nomor}. {soal.get('teks_indonesia', '')}** *(Pilih SEMUA)*")
        if soal.get('teks_arab'):
            st.markdown(f"<div dir='rtl' style='background:#f0f2f6;padding:10px;border-radius:10px'>{soal['teks_arab']}</div>", unsafe_allow_html=True)
        for key, value in soal.get('pilihan', {}).items():
            st.write(f"**{key}.** {value}")
        with st.expander("🔑 Kunci Jawaban"):
            st.info(f"Jawaban: **{', '.join(soal.get('jawaban', []))}**")
    
    elif tipe == 'Benar/Salah':
        st.markdown(f"**{nomor}. Berilah tanda ✓ atau ✗!**")
        for p in soal.get('pernyataan', []):
            st.write(f"{p['no']}. {p['teks']}")
        with st.expander("🔑 Kunci Jawaban"):
            for p in soal.get('pernyataan', []):
                st.markdown(f"{p['no']}. **{p['jawaban']}**")
    
    else:
        st.markdown(f"**{nomor}. {soal}**")
    
    if soal.get('bloom_level'):
        st.caption(f"Level Bloom: {soal['bloom_level']}")
    st.divider()
    return False

# ========== FUNGSI EKSPOR ==========
def export_to_word(soal_data, ki, kd, kelas, topik, sumber_materi, teks_bacaan=None):
    doc = Document()
    title = doc.add_heading('SOAL BAHASA ARAB', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Kelas: {kelas} SMP/MTs")
    doc.add_paragraph(f"Topik: {topik}")
    doc.add_paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}")
    if ki:
        doc.add_heading('Kompetensi Inti', level=2)
        doc.add_paragraph(ki)
    if kd:
        doc.add_heading('Kompetensi Dasar', level=2)
        doc.add_paragraph(kd)
    doc.add_heading('SOAL', level=1)
    for i, soal in enumerate(soal_data.get('soal', []), 1):
        p = doc.add_paragraph()
        p.add_run(f"{i}. ").bold = True
        p.add_run(soal.get('teks_indonesia', soal.get('teks', '')))
    return doc

def buat_kunci_jawaban_word(soal_data):
    doc = Document()
    doc.add_heading('KUNCI JAWABAN', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}")
    doc.add_heading('Daftar Kunci Jawaban', level=1)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    header_cells = table.rows[0].cells
    header_cells[0].text = 'No'
    header_cells[1].text = 'Jawaban'
    header_cells[2].text = 'Pembahasan'
    for soal in soal_data.get('soal', []):
        row = table.add_row().cells
        row[0].text = str(soal.get('nomor', ''))
        jawaban = soal.get('jawaban', '')
        if isinstance(jawaban, list):
            jawaban = ', '.join(jawaban)
        row[1].text = str(jawaban)
        row[2].text = soal.get('pembahasan', '')
    return doc

# ========== MAIN APP ==========
if 'hasil_soal' not in st.session_state:
    st.session_state.hasil_soal = None

if tombol:
    if not api_key:
        st.error("❌ Masukkan API Key!")
    elif total_soal == 0:
        st.warning("⚠️ Pilih minimal satu tipe soal!")
    elif mode_pembuatan == "Ikuti Contoh Soal (Parafrase)" and not contoh_soal:
        st.error("❌ Masukkan contoh soal!")
    elif not ki or not kd:
        st.error("❌ Pilih KI/KD terlebih dahulu!")
    else:
        tipe_config = {
            'pg_biasa': tipe_pg,
            'pg_kompleks': tipe_pg_kompleks,
            'menjodohkan': tipe_menjodohkan,
            'benar_salah': tipe_benar_salah,
            'pg_teks': tipe_teks,
            'jumlah_pg': jumlah_pg,
            'jumlah_pg_kompleks': jumlah_pg_kompleks,
            'jumlah_menjodohkan': jumlah_menjodohkan,
            'jumlah_benar_salah': jumlah_benar_salah,
            'jumlah_teks': jumlah_teks
        }
        
        prompt = build_prompt(
            ki, kd, kelas, topik, bloom_levels, tipe_config,
            sumber_materi, teks_bacaan, terjemahan,
            mode_pembuatan, contoh_soal,
            tampilan_bacaan, total_soal
        )
        
        with st.spinner(f"✨ AI ({ai_provider}) sedang membuat {total_soal} soal..."):
            if ai_provider == "DeepSeek":
                hasil, error = buat_soal(api_key, prompt, ai_provider, deepseek_model, "", "", "")
            elif ai_provider == "OpenAI GPT":
                hasil, error = buat_soal(api_key, prompt, ai_provider, "", openai_model, "", "")
            elif ai_provider == "Maia Router":
                hasil, error = buat_soal(api_key, prompt, ai_provider, "", "", maia_endpoint, maia_model)
            else:
                hasil, error = buat_soal(api_key, prompt, ai_provider, "", "", "", "")
        
        if error:
            st.error(f"❌ Gagal: {error}")
        else:
            st.session_state.hasil_soal = hasil
            st.success(f"✅ Berhasil membuat {total_soal} soal!")
            
            sudah_tampil = False
            for i, soal in enumerate(hasil.get('soal', []), 1):
                sudah_tampil = display_question(
                    soal, i, tampilan_bacaan, teks_bacaan, terjemahan, sudah_tampil
                )
            
            if enable_edit:
                st.markdown("---")
                st.header("✏️ Edit Soal")
                soal_list = hasil.get('soal', [])
                edit_data = []
                for idx, soal in enumerate(soal_list):
                    edit_data.append({
                        "No": idx + 1,
                        "Tipe": soal.get('tipe', ''),
                        "Pertanyaan": soal.get('teks_indonesia', soal.get('teks', '')),
                        "Jawaban": soal.get('jawaban', ''),
                        "Pembahasan": soal.get('pembahasan', '')
                    })
                
                edited_df = st.data_editor(edit_data, use_container_width=True, hide_index=True)
                if st.button("✅ Terapkan Perubahan"):
                    for idx, row in enumerate(edited_df):
                        if idx < len(soal_list):
                            if soal_list[idx].get('teks_indonesia'):
                                soal_list[idx]['teks_indonesia'] = row['Pertanyaan']
                            soal_list[idx]['jawaban'] = row['Jawaban']
                            soal_list[idx]['pembahasan'] = row['Pembahasan']
                    st.session_state.hasil_soal['soal'] = soal_list
                    st.success("✅ Perubahan diterapkan!")
                    st.rerun()

# ========== TOMBOL EXPORT ==========
if st.session_state.hasil_soal:
    st.markdown("---")
    st.subheader("📥 Download Soal")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        json_str = json.dumps(st.session_state.hasil_soal, indent=2, ensure_ascii=False)
        st.download_button("📥 Download JSON", json_str, f"soal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", use_container_width=True)
        
        doc = export_to_word(st.session_state.hasil_soal, ki, kd, kelas, topik, sumber_materi, teks_bacaan)
        doc_bytes = BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        st.download_button("📄 Download Word", doc_bytes, f"soal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx", use_container_width=True)
    
    with col2:
        kunci_doc = buat_kunci_jawaban_word(st.session_state.hasil_soal)
        kunci_bytes = BytesIO()
        kunci_doc.save(kunci_bytes)
        kunci_bytes.seek(0)
        st.download_button("🔑 Download Kunci Jawaban", kunci_bytes, f"kunci_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx", use_container_width=True)
    
    with col3:
        st.info(f"🤖 {ai_provider}\n📊 {total_soal} soal")

# ========== PANDUAN ==========
with st.expander("📖 Panduan Penggunaan"):
    st.markdown("""
    **Provider AI:**
    - Gemini: Gratis, API dari aistudio.google.com
    - DeepSeek: Murah, API dari platform.deepseek.com
    - OpenAI: Kualitas terbaik, API dari platform.openai.com
    - Maia Router: Router AI multi-model
    
    **Kelola KI/KD:**
    1. Buka "Kelola Database KI/KD" di sidebar
    2. Tambahkan KI/KD baru
    3. Pilih dari dropdown saat buat soal
    """)