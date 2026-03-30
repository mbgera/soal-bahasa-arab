import streamlit as st
import google.generativeai as genai
import os
import json
import re
from datetime import datetime
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import requests
from supabase import create_client, Client

# ========== INISIALISASI ==========
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

# ========== KONEKSI SUPABASE ==========
# GANTI DENGAN DATA DARI SUPABASE ANDA!
SUPABASE_URL = "https://mzixdthfukblrhnifunl.supabase.co"  # ganti dengan URL Anda
SUPABASE_KEY = "sb_publishable_0yIRih0UtYcl47kPCaleCQ_bMZmEaFm"  # ganti dengan anon key Anda

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# ========== FUNGSI DATABASE ==========
def load_ki_kd():
    """Mengambil data KI/KD dari Supabase"""
    try:
        response = supabase.table("ki_kd").select("*").order("kelas", desc=False).order("id", desc=False).execute()
        return response.data
    except Exception as e:
        st.error(f"Gagal load data: {e}")
        return []

def save_ki_kd(kelas, ki, kd, keterangan):
    """Menyimpan KI/KD ke Supabase"""
    try:
        supabase.table("ki_kd").insert({
            "kelas": kelas,
            "ki": ki,
            "kd": kd,
            "keterangan": keterangan
        }).execute()
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan: {e}")
        return False

def delete_ki_kd(item_id):
    """Menghapus KI/KD dari Supabase"""
    try:
        supabase.table("ki_kd").delete().eq("id", item_id).execute()
        return True
    except Exception as e:
        st.error(f"Gagal menghapus: {e}")
        return False

def update_ki_kd(item_id, kelas, ki, kd, keterangan):
    """Update KI/KD"""
    try:
        supabase.table("ki_kd").update({
            "kelas": kelas,
            "ki": ki,
            "kd": kd,
            "keterangan": keterangan
        }).eq("id", item_id).execute()
        return True
    except Exception as e:
        st.error(f"Gagal update: {e}")
        return False

def save_hasil_soal(soal_data, kelas, topik):
    """Menyimpan hasil soal ke Supabase (opsional)"""
    try:
        supabase.table("hasil_soal").insert({
            "soal_data": soal_data,
            "kelas": kelas,
            "topik": topik
        }).execute()
    except Exception as e:
        pass

# ========== LOAD DATA DARI DATABASE ==========
if 'ki_kd_database' not in st.session_state:
    st.session_state.ki_kd_database = load_ki_kd()

# ========== SESSION STATE UNTUK EDIT ==========
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = None
if 'edit_data' not in st.session_state:
    st.session_state.edit_data = None

# Judul
st.title("📖 Generator Soal Bahasa Arab SMP/MTs")
st.markdown("Ditenagai **Multi AI** | Database **KI/KD Permanen** | **6 Tipe Soal**")

# ========== SIDEBAR ==========
with st.sidebar:
    st.header("⚙️ Pengaturan")
    
    # ========== PILIH AI PROVIDER ==========
    st.header("🤖 Pilih AI Provider")
    
    ai_provider = st.selectbox(
        "Model AI",
        ["Gemini (Google)", "DeepSeek", "OpenAI GPT", "Maia Router"]
    )
    
    # Input API Key sesuai provider
    if ai_provider == "Gemini (Google)":
        api_key = st.text_input("🔑 API Key Gemini", type="password", placeholder="AIzaSy...")
        deepseek_model = ""
        openai_model = ""
        maia_endpoint = ""
        maia_model = ""
        st.caption("💡 Dapatkan di aistudio.google.com")
    
    elif ai_provider == "DeepSeek":
        api_key = st.text_input("🔑 API Key DeepSeek", type="password", placeholder="sk-...")
        deepseek_model = st.selectbox("Model", ["deepseek-chat", "deepseek-reasoner"])
        openai_model = ""
        maia_endpoint = ""
        maia_model = ""
        st.caption("💡 Dapatkan di platform.deepseek.com")
    
    elif ai_provider == "OpenAI GPT":
        api_key = st.text_input("🔑 API Key OpenAI", type="password", placeholder="sk-...")
        openai_model = st.selectbox("Model", ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"])
        deepseek_model = ""
        maia_endpoint = ""
        maia_model = ""
        st.caption("💡 Dapatkan di platform.openai.com")
    
    elif ai_provider == "Maia Router":
        api_key = st.text_input("🔑 API Key Maia Router", type="password")
        maia_endpoint = st.text_input("Endpoint", placeholder="https://api.maiarouter.com/v1/chat/completions")
        maia_model = st.selectbox("Model", ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro", "auto"])
        deepseek_model = ""
        openai_model = ""
        st.caption("💡 Router AI multi-model")
    
    st.markdown("---")
    
    # ========== KELOLA KI/KD (DENGAN DATABASE PERMANEN) ==========
    with st.expander("📚 Kelola Database KI/KD", expanded=False):
        st.markdown("**Tambah KI/KD Baru**")
        
        col_kelas, col_keterangan = st.columns(2)
        with col_kelas:
            kelas_baru = st.selectbox("Kelas", ["7", "8", "9"], key="kelas_baru")
        with col_keterangan:
            keterangan_baru = st.text_input("Keterangan", placeholder="Contoh: Bab 1 Perkenalan")
        
        ki_baru = st.text_area("Kompetensi Inti (KI)", height=80, placeholder="Contoh: KI-3: Memahami pengetahuan faktual, konseptual, dan prosedural...")
        kd_baru = st.text_area("Kompetensi Dasar (KD)", height=80, placeholder="Contoh: 3.1 Memahami fungsi sosial, struktur teks, dan unsur kebahasaan pada teks tentang التعارف")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("➕ Tambah KI/KD", use_container_width=True):
                if ki_baru and kd_baru:
                    if save_ki_kd(kelas_baru, ki_baru, kd_baru, keterangan_baru):
                        st.session_state.ki_kd_database = load_ki_kd()
                        st.success("✅ KI/KD berhasil disimpan permanen!")
                        st.rerun()
                    else:
                        st.error("❌ Gagal menyimpan!")
                else:
                    st.error("❌ KI dan KD harus diisi!")
        
        st.markdown("---")
        st.markdown("**📋 Daftar KI/KD Tersimpan**")
        
        filter_kelas = st.selectbox("Filter Kelas", ["Semua", "7", "8", "9"], key="filter_kelas_db")
        
        filtered_data = st.session_state.ki_kd_database
        if filter_kelas != "Semua":
            filtered_data = [item for item in filtered_data if item["kelas"] == filter_kelas]
        
        for item in filtered_data:
            with st.container():
                col_btn, col_info = st.columns([1, 5])
                with col_info:
                    st.markdown(f"**Kelas {item['kelas']}** {f'- {item.get("keterangan", "")}' if item.get("keterangan") else ''}")
                    st.caption(f"KI: {item['ki'][:100]}..." if len(item['ki']) > 100 else f"KI: {item['ki']}")
                    st.caption(f"KD: {item['kd'][:100]}..." if len(item['kd']) > 100 else f"KD: {item['kd']}")
                with col_btn:
                    if st.button("🗑️", key=f"del_{item['id']}"):
                        if delete_ki_kd(item['id']):
                            st.session_state.ki_kd_database = load_ki_kd()
                            st.success("✅ Berhasil dihapus!")
                            st.rerun()
            st.divider()
    
    st.markdown("---")
    
    # ========== PILIH KI/KD ==========
    st.header("📖 Pilih KI/KD")
    
    ki_kd_options = []
    for item in st.session_state.ki_kd_database:
        label = f"Kelas {item['kelas']}: {item.get('keterangan', item['kd'][:50])}..."
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
        
        selected = ki_kd_options[selected_index]
        kelas = selected["kelas"]
        ki = selected["ki"]
        kd = selected["kd"]
        
        st.info(f"**KI:** {ki[:120]}..." if len(ki) > 120 else f"**KI:** {ki}")
        st.info(f"**KD:** {kd[:120]}..." if len(kd) > 120 else f"**KD:** {kd}")
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
        ["AI Bebas (Buat Sendiri)", "Ikuti Contoh Soal (Parafrase)"],
        help="Pilih 'Ikuti Contoh Soal' jika ingin AI meniru format contoh yang diberikan"
    )
    
    contoh_soal = ""
    if mode_pembuatan == "Ikuti Contoh Soal (Parafrase)":
        st.markdown("---")
        st.header("📋 Contoh Soal")
        contoh_soal = st.text_area(
            "**Contoh Soal (Wajib Diisi)**",
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
    
    # ========== MATERI KHUSUS ==========
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
    
    topik = topik_khusus if topik_khusus else st.text_input("Topik Umum", placeholder="Contoh: التعارف, المدرسة, الأسرة")
    
    st.markdown("---")
    
    # ========== TIPE SOAL ==========
    st.header("📝 Pilih Tipe Soal")
    
    col1, col2 = st.columns(2)
    with col1:
        tipe_pg = st.checkbox("PG Biasa (1 jawaban)", value=True)
        tipe_pg_kompleks = st.checkbox("PG Kompleks (>1 jawaban)", value=True)
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
        st.info("📌 Dalam mode ini, AI akan meniru format contoh yang Anda berikan.")
        total_soal = st.number_input("Jumlah Soal yang Diinginkan", min_value=1, max_value=20, value=5)
        jumlah_pg = total_soal if tipe_pg else 0
        jumlah_pg_kompleks = total_soal if tipe_pg_kompleks else 0
        jumlah_benar_salah = total_soal if tipe_benar_salah else 0
        jumlah_teks = total_soal if tipe_teks else 0
        jumlah_menjodohkan = 0
    else:
        jumlah_pg = st.number_input("PG Biasa", min_value=0, max_value=10, value=2) if tipe_pg else 0
        jumlah_pg_kompleks = st.number_input("PG Kompleks", min_value=0, max_value=10, value=1) if tipe_pg_kompleks else 0
        jumlah_benar_salah = st.number_input("Benar/Salah", min_value=0, max_value=10, value=2) if tipe_benar_salah else 0
        jumlah_teks = st.number_input("PG Berbasis Teks", min_value=0, max_value=10, value=1) if tipe_teks else 0
        jumlah_menjodohkan = 0
        total_soal = jumlah_pg + jumlah_pg_kompleks + jumlah_benar_salah + jumlah_teks
    
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
                    {"role": "system", "content": "Anda adalah guru Bahasa Arab ahli untuk tingkat SMP/MTs. Anda membuat soal dengan format JSON yang rapi."},
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
                    {"role": "system", "content": "Anda adalah guru Bahasa Arab ahli untuk tingkat SMP/MTs. Anda membuat soal dengan format JSON yang rapi."},
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
                    {"role": "system", "content": "Anda adalah guru Bahasa Arab ahli untuk tingkat SMP/MTs. Anda membuat soal dengan format JSON yang rapi."},
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
                return None, f"Maia Router API error: {response.status_code}"
        
        else:
            return None, f"Provider {ai_provider} tidak dikenal"
        
        # Parse JSON dari response
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return data, None
        else:
            return None, "Tidak bisa membaca hasil dari AI. Response tidak mengandung JSON."
            
    except requests.exceptions.Timeout:
        return None, "Timeout: API tidak merespons dalam 60 detik"
    except Exception as e:
        return None, str(e)

# ========== FUNGSI MEMBANGUN PROMPT ==========
def build_prompt(ki, kd, kelas, topik, bloom_levels, tipe_config, sumber_materi, teks_bacaan, terjemahan, mode_pembuatan, contoh_soal, tampilan_bacaan, total_soal):
    materi_khusus = ""
    if sumber_materi == "Dengan Materi Khusus (Teks/Topik)" and teks_bacaan:
        instruksi = ""
        if tampilan_bacaan == "Teks bacaan ditampilkan di atas semua soal":
            instruksi = "Teks bacaan WAJIB ditampilkan di AWAL sebelum semua soal."
        elif tampilan_bacaan == "Teks bacaan hanya ditampilkan pada soal berbasis teks saja":
            instruksi = "Teks bacaan HANYA ditampilkan pada soal tipe PG Berbasis Teks."
        else:
            instruksi = "Teks bacaan TIDAK perlu ditampilkan dalam soal."
        
        materi_khusus = f"""
=== MATERI KHUSUS ===
Teks Bacaan (Arab): {teks_bacaan}
Terjemahan: {terjemahan if terjemahan else 'Tidak ada'}
{instruksi}
"""
    
    bagian_contoh = ""
    if mode_pembuatan == "Ikuti Contoh Soal (Parafrase)" and contoh_soal:
        bagian_contoh = f"""
=== MODE: IKUTI CONTOH SOAL ===
Anda HARUS membuat soal dengan format yang SAMA PERSIS seperti contoh di bawah ini.

CONTOH SOAL:
{contoh_soal}

PENTING:
1. Buat {total_soal} soal dengan format yang SAMA dengan contoh di atas
2. Perhatikan pola penulisan contoh
3. Hanya ganti konten soal sesuai materi yang diberikan
4. Jangan mengubah struktur format contoh
"""
    
    tipe_soal_list = []
    if tipe_config.get('pg_biasa'):
        tipe_soal_list.append("- Pilihan Ganda Biasa: 4 pilihan, 1 jawaban benar")
    if tipe_config.get('pg_kompleks'):
        tipe_soal_list.append("- Pilihan Ganda Kompleks: 4 pilihan, lebih dari 1 jawaban benar")
    if tipe_config.get('benar_salah'):
        tipe_soal_list.append("- Benar/Salah: Tabel pernyataan")
    if tipe_config.get('pg_teks'):
        tipe_soal_list.append("- PG Berbasis Teks: Diawali teks bacaan")
    
    prompt = f"""
Anda adalah guru Bahasa Arab ahli untuk tingkat SMP/MTs.

=== KOMPETENSI ===
KI: {ki if ki else 'Sesuai kurikulum'}
KD: {kd if kd else 'Sesuai materi'}
Kelas: {kelas}
{materi_khusus}
{bagian_contoh}

=== TAKSONOMI BLOOM ===
Gunakan level: {', '.join(bloom_levels)}

=== TIPE SOAL ===
{chr(10).join(tipe_soal_list) if tipe_soal_list else "Buat variasi tipe soal"}

=== JUMLAH SOAL ===
- PG Biasa: {tipe_config.get('jumlah_pg', 0)}
- PG Kompleks: {tipe_config.get('jumlah_pg_kompleks', 0)}
- Benar/Salah: {tipe_config.get('jumlah_benar_salah', 0)}
- PG Berbasis Teks: {tipe_config.get('jumlah_teks', 0)}

=== FORMAT OUTPUT ===
Buat soal dalam format JSON dengan struktur berikut:

{{
  "metadata": {{
    "kelas": "{kelas}",
    "topik": "{topik if topik else 'Sesuai KI/KD'}",
    "bloom_levels": {bloom_levels}
  }},
  "soal": [
    {{
      "nomor": 1,
      "tipe": "Pilihan Ganda Biasa",
      "bloom_level": "C1 - Mengingat (Remembering)",
      "teks_arab": "...",
      "teks_indonesia": "...",
      "pilihan": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "jawaban": "A",
      "pembahasan": "..."
    }}
  ]
}}

PENTING:
1. Gunakan tulisan Arab yang benar dengan harakat
2. Sertakan terjemahan Indonesia untuk teks Arab
3. Untuk PG Kompleks, jawaban berupa array ["A","B"]
4. Untuk Benar/Salah, gunakan format pernyataan array
"""
    return prompt

# ========== FUNGSI TAMPILAN SOAL ==========
def display_question(soal, nomor, tampilan_bacaan=None, teks_bacaan_global=None, terjemahan_global=None, sudah_tampil_bacaan=None):
    # Tampilkan bacaan di awal jika mode "di atas semua soal"
    if tampilan_bacaan == "Teks bacaan ditampilkan di atas semua soal" and nomor == 1 and not sudah_tampil_bacaan:
        if teks_bacaan_global:
            st.markdown("### 📖 Teks Bacaan")
            st.markdown(f"<div dir='rtl' style='font-size: 16px; background: #e9ecef; padding: 15px; border-radius: 10px; margin: 10px 0;'>{teks_bacaan_global}</div>", unsafe_allow_html=True)
            if terjemahan_global:
                st.markdown(f"**Terjemahan:** {terjemahan_global}")
            st.markdown("---")
            return True
    
    tipe = soal.get('tipe', '')
    
    if tipe in ['Pilihan Ganda Biasa', 'PG Biasa']:
        st.markdown(f"**{nomor}. {soal.get('teks_indonesia', '')}**")
        if soal.get('teks_arab'):
            st.markdown(f"<div dir='rtl' style='font-size: 18px; background: #f0f2f6; padding: 10px; border-radius: 10px; margin: 10px 0;'>{soal['teks_arab']}</div>", unsafe_allow_html=True)
        
        cols = st.columns(2)
        for idx, (key, value) in enumerate(soal.get('pilihan', {}).items()):
            cols[idx % 2].write(f"**{key}.** {value}")
        
        with st.expander("🔑 Kunci Jawaban"):
            st.info(f"Jawaban: **{soal['jawaban']}**")
            if soal.get('pembahasan'):
                st.success(f"📖 {soal['pembahasan']}")
    
    elif tipe in ['Pilihan Ganda Kompleks', 'PG Kompleks']:
        st.markdown(f"**{nomor}. {soal.get('teks_indonesia', '')}**")
        st.caption("*(Pilihlah SEMUA jawaban yang benar)*")
        if soal.get('teks_arab'):
            st.markdown(f"<div dir='rtl' style='font-size: 18px; background: #f0f2f6; padding: 10px; border-radius: 10px; margin: 10px 0;'>{soal['teks_arab']}</div>", unsafe_allow_html=True)
        
        for key, value in soal.get('pilihan', {}).items():
            st.write(f"**{key}.** {value}")
        
        with st.expander("🔑 Kunci Jawaban"):
            jawaban = soal.get('jawaban', [])
            st.info(f"Jawaban yang benar: **{', '.join(jawaban)}**")
            if soal.get('pembahasan'):
                st.success(f"📖 {soal['pembahasan']}")
    
    elif tipe == 'Benar/Salah':
        st.markdown(f"**{nomor}. Berilah tanda ✓ (Benar) atau ✗ (Salah)!**")
        for p in soal.get('pernyataan', []):
            st.write(f"{p.get('no', '')}. {p.get('teks', '')}")
        with st.expander("🔑 Kunci Jawaban"):
            for p in soal.get('pernyataan', []):
                st.markdown(f"{p.get('no', '')}. {p.get('teks', '')} -> **{p.get('jawaban', '')}**")
    
    elif tipe in ['Pilihan Ganda Berbasis Teks', 'PG Berbasis Teks']:
        st.markdown(f"**{nomor}.**")
        st.markdown(f"<div dir='rtl' style='background: #e9ecef; padding: 15px; border-radius: 10px;'><b>Teks:</b><br>{soal.get('teks_bacaan', '')}</div>", unsafe_allow_html=True)
        if soal.get('terjemahan_bacaan'):
            st.caption(f"Terjemahan: {soal['terjemahan_bacaan']}")
        st.markdown(f"**Soal:** {soal.get('teks_soal', '')}")
        for key, value in soal.get('pilihan', {}).items():
            st.write(f"**{key}.** {value}")
        with st.expander("🔑 Kunci Jawaban"):
            st.info(f"Jawaban: **{soal['jawaban']}**")
    
    else:
        if 'teks_soal' in soal:
            st.markdown(f"**{nomor}. {soal.get('teks_soal', '')}**")
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
    doc.add_paragraph(f"Topik: {topik if topik else 'Sesuai KI/KD'}")
    doc.add_paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}")
    doc.add_paragraph()
    if ki:
        doc.add_heading('Kompetensi Inti', level=2)
        doc.add_paragraph(ki)
    if kd:
        doc.add_heading('Kompetensi Dasar', level=2)
        doc.add_paragraph(kd)
    doc.add_paragraph("=" * 50)
    doc.add_heading('SOAL', level=1)
    
    for i, soal in enumerate(soal_data.get('soal', []), 1):
        p = doc.add_paragraph()
        p.add_run(f"{i}. ").bold = True
        if soal.get('teks_indonesia'):
            p.add_run(soal['teks_indonesia'])
        elif soal.get('teks'):
            p.add_run(soal['teks'])
        doc.add_paragraph()
    
    return doc

def buat_kunci_jawaban_json(soal_data):
    kunci_data = {
        "metadata": {
            "kelas": soal_data.get('metadata', {}).get('kelas', ''),
            "topik": soal_data.get('metadata', {}).get('topik', ''),
            "tanggal": datetime.now().strftime('%Y-%m-%d')
        },
        "kunci_jawaban": []
    }
    for soal in soal_data.get('soal', []):
        kunci = {
            "nomor": soal.get('nomor', 0),
            "tipe": soal.get('tipe', ''),
            "jawaban": soal.get('jawaban', ''),
            "pembahasan": soal.get('pembahasan', '')
        }
        kunci_data["kunci_jawaban"].append(kunci)
    return json.dumps(kunci_data, indent=2, ensure_ascii=False)

def buat_kunci_jawaban_word(soal_data):
    doc = Document()
    title = doc.add_heading('KUNCI JAWABAN', 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Kelas: {soal_data.get('metadata', {}).get('kelas', '')} SMP/MTs")
    doc.add_paragraph(f"Topik: {soal_data.get('metadata', {}).get('topik', '')}")
    doc.add_paragraph(f"Tanggal: {datetime.now().strftime('%d %B %Y')}")
    doc.add_paragraph()
    
    doc.add_heading('Daftar Kunci Jawaban', level=1)
    table = doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    header_cells = table.rows[0].cells
    header_cells[0].text = 'No'
    header_cells[1].text = 'Tipe Soal'
    header_cells[2].text = 'Jawaban'
    header_cells[3].text = 'Pembahasan'
    
    for soal in soal_data.get('soal', []):
        row_cells = table.add_row().cells
        row_cells[0].text = str(soal.get('nomor', ''))
        row_cells[1].text = soal.get('tipe', '')
        jawaban = soal.get('jawaban', '')
        if isinstance(jawaban, list):
            jawaban = ', '.join(jawaban)
        row_cells[2].text = str(jawaban)
        row_cells[3].text = soal.get('pembahasan', '')
    
    doc.add_page_break()
    doc.add_heading('Pembahasan Lengkap', level=1)
    for soal in soal_data.get('soal', []):
        if soal.get('pembahasan'):
            p = doc.add_paragraph()
            p.add_run(f"{soal.get('nomor')}. ").bold = True
            p.add_run(soal['pembahasan'])
            doc.add_paragraph()
    return doc

# ========== MAIN APP ==========
if 'hasil_soal' not in st.session_state:
    st.session_state.hasil_soal = None

if tombol:
    if not api_key:
        st.error("❌ Masukkan API Key terlebih dahulu!")
    elif total_soal == 0:
        st.warning("⚠️ Pilih minimal satu tipe soal!")
    elif mode_pembuatan == "Ikuti Contoh Soal (Parafrase)" and not contoh_soal:
        st.error("❌ Dalam mode ini, Anda harus memberikan contoh soal!")
    elif not ki or not kd:
        st.error("❌ Silakan pilih KI/KD terlebih dahulu!")
    else:
        tipe_config = {
            'pg_biasa': tipe_pg,
            'pg_kompleks': tipe_pg_kompleks,
            'benar_salah': tipe_benar_salah,
            'pg_teks': tipe_teks,
            'jumlah_pg': jumlah_pg,
            'jumlah_pg_kompleks': jumlah_pg_kompleks,
            'jumlah_benar_salah': jumlah_benar_salah,
            'jumlah_teks': jumlah_teks
        }
        
        prompt = build_prompt(
            ki, kd, kelas, topik, bloom_levels, tipe_config,
            sumber_materi, teks_bacaan, terjemahan,
            mode_pembuatan, contoh_soal,
            tampilan_bacaan, total_soal
        )
        
        with st.spinner(f"✨ AI ({ai_provider}) sedang membuat {total_soal} soal... Mohon tunggu 20-40 detik"):
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
            
            # Simpan hasil soal ke database (opsional)
            save_hasil_soal(hasil, kelas, topik)
            
            st.success(f"✅ Berhasil membuat {total_soal} soal menggunakan {ai_provider}!")
            
            if sumber_materi == "Dengan Materi Khusus (Teks/Topik)" and teks_bacaan:
                with st.expander("📖 Materi yang Digunakan", expanded=False):
                    st.markdown("**Teks Bacaan:**")
                    st.markdown(f"<div dir='rtl' style='font-size: 16px; background: #e9ecef; padding: 10px; border-radius: 10px;'>{teks_bacaan}</div>", unsafe_allow_html=True)
                    if terjemahan:
                        st.markdown(f"**Terjemahan:** {terjemahan}")
            
            if mode_pembuatan == "Ikuti Contoh Soal (Parafrase)":
                st.info("📋 Mode: Mengikuti format contoh soal yang diberikan")
            
            sudah_tampil_bacaan = False
            for i, soal in enumerate(hasil.get('soal', []), 1):
                sudah_tampil_bacaan = display_question(
                    soal, i, 
                    tampilan_bacaan,
                    teks_bacaan, terjemahan, sudah_tampil_bacaan
                )
            
            # ========== FITUR EDIT SOAL ==========
            if enable_edit:
                st.markdown("---")
                st.header("✏️ Edit Soal Sebelum Export")
                st.caption("Anda dapat mengedit soal di tabel di bawah ini. Perubahan akan langsung diterapkan sebelum download.")
                
                soal_list = hasil.get('soal', [])
                edit_data = []
                
                for idx, soal in enumerate(soal_list):
                    row = {
                        "No": idx + 1,
                        "Tipe": soal.get('tipe', 'Teks Biasa'),
                        "Pertanyaan": soal.get('teks_indonesia', soal.get('teks', soal.get('teks_soal', ''))),
                        "Pilihan A": soal.get('pilihan', {}).get('A', ''),
                        "Pilihan B": soal.get('pilihan', {}).get('B', ''),
                        "Pilihan C": soal.get('pilihan', {}).get('C', ''),
                        "Pilihan D": soal.get('pilihan', {}).get('D', ''),
                        "Jawaban": soal.get('jawaban', ''),
                        "Pembahasan": soal.get('pembahasan', '')
                    }
                    edit_data.append(row)
                
                edited_df = st.data_editor(
                    edit_data,
                    use_container_width=True,
                    column_config={
                        "No": st.column_config.NumberColumn("No", disabled=True),
                        "Tipe": st.column_config.TextColumn("Tipe", disabled=True),
                        "Pertanyaan": st.column_config.TextColumn("Pertanyaan", width="large"),
                        "Pilihan A": st.column_config.TextColumn("A"),
                        "Pilihan B": st.column_config.TextColumn("B"),
                        "Pilihan C": st.column_config.TextColumn("C"),
                        "Pilihan D": st.column_config.TextColumn("D"),
                        "Jawaban": st.column_config.TextColumn("Jawaban"),
                        "Pembahasan": st.column_config.TextColumn("Pembahasan", width="large")
                    },
                    hide_index=True,
                    key="soal_editor"
                )
                
                col_edit1, col_edit2, col_edit3 = st.columns(3)
                with col_edit2:
                    if st.button("✅ Terapkan Perubahan", use_container_width=True):
                        for idx, row in enumerate(edited_df):
                            if idx < len(soal_list):
                                if soal_list[idx].get('teks_indonesia'):
                                    soal_list[idx]['teks_indonesia'] = row['Pertanyaan']
                                elif soal_list[idx].get('teks'):
                                    soal_list[idx]['teks'] = row['Pertanyaan']
                                elif soal_list[idx].get('teks_soal'):
                                    soal_list[idx]['teks_soal'] = row['Pertanyaan']
                                
                                if 'pilihan' in soal_list[idx]:
                                    soal_list[idx]['pilihan']['A'] = row['Pilihan A']
                                    soal_list[idx]['pilihan']['B'] = row['Pilihan B']
                                    soal_list[idx]['pilihan']['C'] = row['Pilihan C']
                                    soal_list[idx]['pilihan']['D'] = row['Pilihan D']
                                
                                soal_list[idx]['jawaban'] = row['Jawaban']
                                if row['Pembahasan']:
                                    soal_list[idx]['pembahasan'] = row['Pembahasan']
                        
                        st.session_state.hasil_soal['soal'] = soal_list
                        st.success("✅ Perubahan telah diterapkan!")
                        st.rerun()

# ========== TOMBOL EXPORT ==========
if st.session_state.hasil_soal:
    st.markdown("---")
    st.subheader("📥 Download Soal")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**📚 Soal Lengkap**")
        try:
            json_str = json.dumps(st.session_state.hasil_soal, indent=2, ensure_ascii=False)
            st.download_button("📥 Download JSON (Soal)", json_str, 
                f"soal_arab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 
                "application/json", use_container_width=True)
        except:
            st.download_button("📥 Download Teks", str(st.session_state.hasil_soal), 
                f"soal_arab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", 
                "text/plain", use_container_width=True)
        
        doc = export_to_word(st.session_state.hasil_soal, ki, kd, kelas, topik, 
            sumber_materi, teks_bacaan if sumber_materi == "Dengan Materi Khusus (Teks/Topik)" else None)
        doc_bytes = BytesIO()
        doc.save(doc_bytes)
        doc_bytes.seek(0)
        st.download_button("📄 Download Word (Soal)", doc_bytes, 
            f"soal_arab_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            use_container_width=True)
    
    with col2:
        st.markdown("**🔑 Kunci Jawaban (Terpisah)**")
        kunci_json = buat_kunci_jawaban_json(st.session_state.hasil_soal)
        st.download_button("📥 Download JSON (Kunci)", kunci_json, 
            f"kunci_jawaban_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 
            "application/json", use_container_width=True)
        
        kunci_doc = buat_kunci_jawaban_word(st.session_state.hasil_soal)
        kunci_bytes = BytesIO()
        kunci_doc.save(kunci_bytes)
        kunci_bytes.seek(0)
        st.download_button("📄 Download Word (Kunci)", kunci_bytes, 
            f"kunci_jawaban_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
            use_container_width=True)
    
    with col3:
        st.markdown("**⚙️ Informasi**")
        st.info(f"🤖 AI: {ai_provider}\n📊 Total: {total_soal} soal")

# ========== PANDUAN ==========
with st.expander("📖 Panduan Penggunaan", expanded=False):
    st.markdown("""
    ### 🤖 Pilih AI Provider
    | Provider | Kelebihan | API Key |
    |----------|-----------|---------|
    | **Gemini** | Gratis, stabil | Dapatkan di aistudio.google.com |
    | **DeepSeek** | Murah, kualitas bagus | Dapatkan di platform.deepseek.com |
    | **OpenAI GPT** | Populer, kualitas terbaik | Dapatkan di platform.openai.com |
    | **Maia Router** | Router AI, akses multi-model | Dapatkan di platform Maia Router |
    
    ### 📚 Kelola KI/KD (Database Permanen)
    1. Buka bagian **Kelola Database KI/KD** di sidebar
    2. Klik **Tambah KI/KD Baru**
    3. Isi Kelas, KI, KD, dan keterangan
    4. Data akan tersimpan **permanen** di Supabase
    5. Saat buat soal, tinggal pilih dari dropdown
    
    ### 🎯 Mode Pembuatan Soal
    | Mode | Keterangan |
    |------|------------|
    | **AI Bebas** | AI membuat soal kreatif berdasarkan KI/KD dan materi |
    | **Ikuti Contoh** | Anda memberikan contoh soal, AI akan membuat soal dengan format yang sama |
    
    ### 📌 Fitur Lainnya
    - **Edit Soal**: Ubah soal langsung di aplikasi sebelum download
    - **Kunci Jawaban Terpisah**: Download kunci jawaban dalam file terpisah
    - **Export Word**: Format siap cetak
    """)