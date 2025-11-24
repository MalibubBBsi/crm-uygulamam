import streamlit as st
import pandas as pd
import sqlite3
import urllib.parse # Link oluşturmak için gerekli kütüphane
from datetime import datetime, date

# --- 1. VERİTABANI KURULUMU ---
def init_db():
    conn = sqlite3.connect('ticaret_veritabani.db')
    c = conn.cursor()
    
    c.execute('CREATE TABLE IF NOT EXISTS musteriler (id INTEGER PRIMARY KEY AUTOINCREMENT, ad_soyad TEXT, telefon TEXT)')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yayinevi TEXT,
            seri_ozelligi TEXT,
            sinav_sayisi TEXT,
            sinav_turu TEXT,
            sinif TEXT,
            uygulama_tarihi TEXT,
            aciklama TEXT,
            son_siparis_tarihi TEXT,
            tam_ad TEXT
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS siparisler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            musteri_id INTEGER,
            urun_id INTEGER,
            adet INTEGER,
            alis_fiyati REAL,
            satis_fiyati REAL,
            toplam_ciro REAL,
            toplam_kar REAL,
            teslimat_tarihi TEXT,
            durum TEXT,
            FOREIGN KEY(musteri_id) REFERENCES musteriler(id),
            FOREIGN KEY(urun_id) REFERENCES urunler(id)
        )
    ''')
    conn.commit()
    conn.close()

# --- 2. YARDIMCI FONKSİYONLAR ---

def musteri_ekle(ad, tel):
    conn = sqlite3.connect('ticaret_veritabani.db')
    c = conn.cursor()
    c.execute('INSERT INTO musteriler (ad_soyad, telefon) VALUES (?,?)', (ad, tel))
    conn.commit()
    conn.close()

def urun_ekle_excelden(row):
    conn = sqlite3.connect('ticaret_veritabani.db')
    c = conn.cursor()
    
    y = str(row.get('YAYINEVİ', '')).replace('nan', '').strip()
    seri = str(row.get('SERİ', '')).replace('nan', '').strip()
    if not seri:
        seri = str(row.get('SERİ-ÖZELLİĞİ', '')).replace('nan', '').strip()
        
    s_sayi = str(row.get('SINAV SAYISI', '')).replace('nan', '').strip()
    s_tur = str(row.get('SINAV TÜRÜ', '')).replace('nan', '').strip()
    sinif = str(row.get('SINIF', '')).replace('nan', '').strip()
    u_tarih = str(row.get('UYGULAMA TARİHİ', '')).replace('nan', '').strip()
    aciklama = str(row.get('AÇIKLAMA', '')).replace('nan', '').strip()
    son_sip_tarih = str(row.get('SON SİPARİŞ TARİHİ', '')).replace('nan', '').strip()

    tam_isim = f"{y}"
    if seri: tam_isim += f" - {seri}"
    tam_isim += f" - {sinif} - {s_sayi}"
    
    c.execute('''
        INSERT INTO urunler (yayinevi, seri_ozelligi, sinav_sayisi, sinav_turu, sinif, uygulama_tarihi, aciklama, son_siparis_tarihi, tam_ad)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (y, seri, s_sayi, s_tur, sinif, u_tarih, aciklama, son_sip_tarih, tam_isim))
    conn.commit()
    conn.close()

def siparis_olustur(musteri_id, urun_id, adet, alis, satis, tarih, durum):
    conn = sqlite3.connect('ticaret_veritabani.db')
    c = conn.cursor()
    
    toplam_ciro = satis * adet
    toplam_maliyet = alis * adet
    toplam_kar = toplam_ciro - toplam_maliyet
    
    c.execute('''INSERT INTO siparisler 
                 (musteri_id, urun_id, adet, alis_fiyati, satis_fiyati, toplam_ciro, toplam_kar, teslimat_tarihi, durum) 
                 VALUES (?,?,?,?,?,?,?,?,?)''', 
              (musteri_id, urun_id, adet, alis, satis, toplam_ciro, toplam_kar, tarih, durum))
    conn.commit()
    conn.close()

def siparis_durum_guncelle(siparis_id, yeni_durum):
    conn = sqlite3.connect('ticaret_veritabani.db')
    c = conn.cursor()
    c.execute('UPDATE siparisler SET durum = ? WHERE id = ?', (yeni_durum, siparis_id))
    conn.commit()
    conn.close()

def veri_getir(tablo):
    conn = sqlite3.connect('ticaret_veritabani.db')
    df = pd.read_sql_query(f"SELECT * FROM {tablo}", conn)
    conn.close()
    return df

def rapor_getir():
    conn = sqlite3.connect('ticaret_veritabani.db')
    query = '''
        SELECT 
            s.id as Siparis_No,
            m.ad_soyad as Kurum,
            u.tam_ad as Urun,
            u.uygulama_tarihi as Sinav_Tarihi,
            s.adet as Adet,
            s.satis_fiyati as Birim_Satis,
            s.toplam_ciro as Ciro,
            s.toplam_kar as Kar,
            s.durum as Durum
        FROM siparisler s
        JOIN musteriler m ON s.musteri_id = m.id
        JOIN urunler u ON s.urun_id = u.id
        ORDER BY s.id DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- WHATSAPP İÇİN TELEFON FORMATLAYICI ---
def telefon_temizle(tel):
    # Boşlukları, parantezleri ve tireleri temizle
    if not tel: return ""
    temiz = str(tel).replace(" ", "").replace("(", "").replace(")", "").replace("-", "")
    
    # Başında 0 varsa 90 yap, yoksa ve 5 ile başlıyorsa başına 90 ekle
    if temiz.startswith("0"):
        temiz = "9" + temiz
    elif temiz.startswith("5"):
        temiz = "90" + temiz
        
    return temiz

# --- 3. ARAYÜZ TASARIMI ---
st.set_page_config(page_title="CRM & Finans", layout="wide")
st.title("🚀 Kurumsal Satış & Finans Yönetimi")

if 'secilen_urun_id' not in st.session_state:
    st.session_state.secilen_urun_id = None

init_db()

tab_finans, tab_takip, tab_siparis, tab_urun, tab_musteri = st.tabs(
    ["📊 1. Ciro & Karlılık", "📦 2. Sipariş Takip", "🛒 3. Ürün Seç & Sipariş", "📂 4. Ürün Yükle (Excel)", "👥 5. Müşteri Ekle"]
)

# --- TAB 1: CİRO VE KARLILIK ---
with tab_finans:
    st.header("Finansal Genel Bakış")
    df = rapor_getir()
    if not df.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Ciro", f"{df['Ciro'].sum():,.2f} ₺")
        c2.metric("Toplam Kar", f"{df['Kar'].sum():,.2f} ₺")
        c3.metric("Toplam Adet", f"{df['Adet'].sum()}")
        st.divider()
        st.bar_chart(df, x="Kurum", y="Ciro")
    else:
        st.info("Henüz sipariş verisi yok.")

# --- TAB 2: SİPARİŞ TAKİP ---
with tab_takip:
    st.subheader("Sipariş Listesi")
    df_siparis = rapor_getir()
    if not df_siparis.empty:
        durum_filtresi = st.multiselect("Durum Filtrele", df_siparis['Durum'].unique())
        if durum_filtresi:
             st.dataframe(df_siparis[df_siparis['Durum'].isin(durum_filtresi)], use_container_width=True)
        else:
             st.dataframe(df_siparis, use_container_width=True)
        
        st.divider()
        c1, c2 = st.columns(2)
        with c1: sip_no = st.number_input("Sipariş No", min_value=1)
        with c2: 
            y_durum = st.selectbox("Durum", ["Onaylandı", "Teslim Edildi", "İptal"])
            if st.button("Güncelle"):
                siparis_durum_guncelle(sip_no, y_durum)
                st.success("Durum güncellendi")
                st.rerun()
    else:
        st.info("Listelenecek sipariş yok.")

# --- TAB 3: KARTLI ÜRÜN SEÇİMİ VE WHATSAPP ENTEGRASYONU ---
with tab_siparis:
    st.header("Ürün Kataloğu ve Sipariş")
    
    musteriler = veri_getir("musteriler")
    urunler = veri_getir("urunler")
    
    if musteriler.empty or urunler.empty:
        st.warning("⚠️ Önce Müşteri ve Ürün ekleyin!")
    else:
        # FİLTRELEME
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1: filtre_yayinevi = st.multiselect("Yayınevi", urunler['yayinevi'].unique())
        with col_f2: filtre_sinif = st.multiselect("Sınıf", urunler['sinif'].unique())
        with col_f3: arama_metni = st.text_input("İsimden Ara", placeholder="Örn: Rehber")

        df_filtered = urunler.copy()
        if filtre_yayinevi: df_filtered = df_filtered[df_filtered['yayinevi'].isin(filtre_yayinevi)]
        if filtre_sinif: df_filtered = df_filtered[df_filtered['sinif'].isin(filtre_sinif)]
        if arama_metni: df_filtered = df_filtered[df_filtered['tam_ad'].str.contains(arama_metni, case=False)]

        st.divider()

        # SİPARİŞ FORMU
        if st.session_state.secilen_urun_id:
            secilen_urun = urunler[urunler['id'] == st.session_state.secilen_urun_id].iloc[0]
            with st.container(border=True):
                st.info(f"✅ **SEÇİLEN:** {secilen_urun['tam_ad']}")
                col_m, col_iptal = st.columns([4, 1])
                with col_m:
                    m_dict = dict(zip(musteriler['ad_soyad'], musteriler['id']))
                    secilen_musteri_ad = st.selectbox("Müşteri Seçiniz", list(m_dict.keys()))
                with col_iptal:
                    st.write("")
                    st.write("")
                    if st.button("❌ İptal"):
                        st.session_state.secilen_urun_id = None
                        st.rerun()

                c1, c2, c3 = st.columns(3)
                adet = c1.number_input("Adet", min_value=1, value=50)
                alis = c2.number_input("Birim ALIŞ (TL)", value=0.0, step=0.5)
                satis = c3.number_input("Birim SATIŞ (TL)", value=0.0, step=0.5)

                # --- SİPARİŞ ONAY VE WHATSAPP BUTONU ---
                if st.button("SİPARİŞİ ONAYLA"):
                    # 1. Siparişi Kaydet
                    siparis_olustur(m_dict[secilen_musteri_ad], int(secilen_urun['id']), adet, alis, satis, secilen_urun['uygulama_tarihi'], "Sipariş Alındı")
                    
                    st.balloons() # Biraz kutlama
                    st.success("✅ Sipariş başarıyla sisteme kaydedildi!")
                    
                    # 2. WhatsApp Mesajını Hazırla
                    # Müşteri Telefonunu bul
                    secilen_musteri_row = musteriler[musteriler['ad_soyad'] == secilen_musteri_ad].iloc[0]
                    ham_tel = secilen_musteri_row['telefon']
                    wp_tel = telefon_temizle(ham_tel)
                    
                    # Mesaj İçeriği
                    mesaj = f"Sayın *{secilen_musteri_ad}*,\n\n" \
                            f"📦 *{secilen_urun['tam_ad']}* siparişiniz ({adet} Adet) alınmıştır.\n" \
                            f"📅 Sınav Tarihi: {secilen_urun['uygulama_tarihi']}\n\n" \
                            f"Bizi tercih ettiğiniz için teşekkür ederiz.\n" \
                            f"- MUSTAFA ÇAVUŞ"
                    
                    # Mesajı URL formatına çevir
                    encoded_msg = urllib.parse.quote(mesaj)
                    wp_link = f"https://wa.me/{wp_tel}?text={encoded_msg}"
                    
                    # 3. Butonu Göster
                    st.markdown(f"""
                        <a href="{wp_link}" target="_blank">
                            <button style="background-color:#25D366; color:white; padding:10px 20px; border:none; border-radius:5px; font-size:16px; cursor:pointer;">
                                📲 WhatsApp Bildirimi Gönder
                            </button>
                        </a>
                        <br><br>
                    """, unsafe_allow_html=True)
                    
                    st.info("💡 Not: WhatsApp butonuna bastıktan sonra yeni işlem yapmak için 'İptal' diyerek formu kapatabilirsiniz.")

            st.divider()

        # KARTLAR
        st.subheader(f"Bulunan Ürünler ({len(df_filtered)})")
        cols = st.columns(2)
        for index, row in df_filtered.iterrows():
            with cols[index % 2]:
                with st.container(border=True):
                    c_sol, c_sag = st.columns([3, 1])
                    with c_sol:
                        st.markdown(f"**{row['yayinevi']}** - {row['seri_ozelligi']}")
                        st.text(f"{row['sinif']} | {row['sinav_sayisi']}")
                        st.caption(f"📅 Tarih: {row['uygulama_tarihi']}")
                    with c_sag:
                        st.write("")
                        if st.button("SEÇ", key=f"btn_{row['id']}"):
                            st.session_state.secilen_urun_id = row['id']
                            st.rerun()

# --- TAB 4: EXCEL YÜKLEME ---
with tab_urun:
    st.header("Excel Dosyası Yükle")
    st.markdown("Başlıklar: `YAYINEVİ`, `SERİ`, `SINAV SAYISI`, `SINIF`, `UYGULAMA TARİHİ`")
    uploaded_file = st.file_uploader("Dosya Seç", type=["xlsx"])
    if uploaded_file:
        try:
            df_excel = pd.read_excel(uploaded_file).fillna('').astype(str)
            if st.button("✅ LİSTEYİ VERİTABANINA KAYDET"):
                for _, row in df_excel.iterrows(): urun_ekle_excelden(row)
                st.success("Başarılı! Ürünler eklendi.")
        except Exception as e: st.error(f"Hata: {e}")
    st.divider()
    st.dataframe(veri_getir("urunler"), use_container_width=True)

# --- TAB 5: MÜŞTERİ EKLE ---
with tab_musteri:
    st.header("Yeni Müşteri Ekle")
    with st.form("musteri_formu", clear_on_submit=True):
        ad = st.text_input("Kurum Adı / Ad Soyad")
        tel = st.text_input("Telefon Numarası (Örn: 545 273 2651)")
        if st.form_submit_button("Müşteriyi Kaydet"):
            musteri_ekle(ad, tel)
            st.success(f"✅ {ad} başarıyla eklendi!")
    st.dataframe(veri_getir("musteriler"), use_container_width=True)