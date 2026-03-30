# ========== MAIN APP ==========
def main():
    if not st.session_state.logged_in:
        show_login_page()
    elif st.session_state.selected_mapel_id is None:
        show_dashboard()
    elif hasattr(st.session_state, 'show_generator') and st.session_state.show_generator:
        # Jika sudah di generator
        if tombol:
            if not api_key:
                st.error("❌ Masukkan API Key terlebih dahulu!")
            elif total_soal == 0:
                st.warning("⚠️ Pilih minimal satu tipe soal!")
            elif mode_pembuatan == "Ikuti Contoh Soal (Parafrase)" and not contoh_soal:
                st.error("❌ Masukkan contoh soal!")
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
                    save_hasil_soal(st.session_state.selected_mapel_id, kelas, topik, hasil)
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
                    
                    if st.session_state.hasil_soal:
                        st.markdown("---")
                        st.subheader("📥 Download Soal")
                        
                        col1, col2 = st.columns(2)
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
        
        # Tampilkan generator
        show_generator()
    else:
        show_manage_ki_kd()

if __name__ == "__main__":
    # Inisialisasi variabel untuk tombol (agar tidak error)
    api_key = deepseek_model = openai_model = maia_endpoint = maia_model = ""
    tipe_pg = tipe_pg_kompleks = tipe_benar_salah = tipe_teks = True
    jumlah_pg = jumlah_pg_kompleks = jumlah_benar_salah = jumlah_teks = total_soal = 0
    mode_pembuatan = "AI Bebas (Buat Sendiri)"
    contoh_soal = ""
    sumber_materi = "Sesuai KI/KD Saja"
    teks_bacaan = terjemahan = topik_khusus = topik = ""
    tampilan_bacaan = "Tidak menampilkan teks bacaan (hanya soal)"
    bloom_levels = ["C1 - Mengingat (Remembering)"]
    enable_edit = True
    tombol = False
    
    main()