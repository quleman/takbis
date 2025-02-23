import sqlite3
import logging
from datetime import datetime


class TakbisInceleme:
    def __init__(self, db_path="veritabani.db"):
        self.db_path = db_path
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def validate_database(self):
        """Veritabanı doğrulama işlemlerini gerçekleştirir"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Taşınmaz verilerinin kontrolü
            cursor.execute("SELECT COUNT(*) FROM tasinmaz")
            tasinmaz_count = cursor.fetchone()[0]
            
            if tasinmaz_count == 0:
                self.logger.error("Taşınmaz veritabanında kayıt bulunamadı")
                return False, "⚠️ Bilgilendirme: Önce Takbisleri içeri aktarın. ..."

            # Taşınmaz ve takbis verilerinin eşleşme kontrolü
            cursor.execute("SELECT COUNT(DISTINCT tasinmaz_no) FROM tasinmaz")
            distinct_tasinmaz = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT tasinmaz_kimlik) FROM takbis_tarih")
            distinct_takbis = cursor.fetchone()[0]
            
            if distinct_tasinmaz != distinct_takbis:
                self.logger.error(f"Veri uyuşmazlığı: Taşınmaz sayısı: {distinct_tasinmaz}, Takbis kayıt sayısı: {distinct_takbis}")
                return False, "⚠️ Bilgilendirme: taşınmaz verilerini yükleyin. ... "

            return True, "Veritabanı doğrulama başarılı"

        except Exception as e:
            self.logger.error(f"Veritabanı doğrulama hatası: {str(e)}")
            return False, f"Doğrulama sırasında hata: {str(e)}"
        finally:
            if conn:
                conn.close()

    def get_tasinmaz_detay(self, cursor, tasinmaz_no):
        """Ada/Parsel ve bağımsız bölüm bilgilerini alır"""
        # Önce ada/parsel bilgisini alalım
        ada, parsel = self.get_ada_parsel(cursor, tasinmaz_no)
    
        # Zemin tipi ve bağımsız bölüm bilgilerini alalım
        cursor.execute("""
            SELECT zemintipi, blok_kat_girisi_bbno 
            FROM tasinmaz 
            WHERE tasinmaz_no = ?
        """, (tasinmaz_no,))
        result = cursor.fetchone()
    
        if not result:
            return ada, parsel, "", ""
    
        zemin_tipi, blok_bilgisi = result
    
        # Eğer KatIrtifaki veya KatMulkiyeti ise bağımsız bölüm detaylarını işleyelim
        if zemin_tipi in ["KatIrtifaki", "KatMulkiyeti"] and blok_bilgisi:
            try:
                parcalar = blok_bilgisi.split("/")
                detay = []
            
                # Blok bilgisi
                if parcalar[0]:
                    detay.append(f"{parcalar[0]} Blok")
            
                # Kat bilgisi
                if len(parcalar) > 1 and parcalar[1]:
                    detay.append(f"{parcalar[1]}. Kat")
            
                # Giriş bilgisi
                if len(parcalar) > 2 and parcalar[2]:
                    detay.append(f"{parcalar[2]} Giriş")
            
                # Bağımsız bölüm no
                if len(parcalar) > 3:
                    bb_no = parcalar[3] if parcalar[3] else "? BB"
                    detay.append(f"{bb_no} Nolu BB")
            
                bb_detay = " ".join(detay)
                return ada, parsel, zemin_tipi, bb_detay
            
            except Exception as e:
                self.logger.error(f"Bağımsız bölüm bilgisi işleme hatası: {str(e)}")
                return ada, parsel, zemin_tipi, ""
    
        return ada, parsel, zemin_tipi, ""

    def format_datetime(self, datetime_str):
        """Tarih ve saat formatını ayırır ve düzenler"""
        try:
            parts = datetime_str.split('-')
            if len(parts) >= 4:
                day = parts[0].zfill(2)
                month = parts[1].zfill(2)
                year = parts[2]
                date_str = f"{day}-{month}-{year}"
                time_str = parts[3]
                return date_str, time_str
            return datetime_str, ""
        except Exception as e:
            self.logger.error(f"Tarih format hatası: {str(e)}")
            return datetime_str, ""

    def get_ada_parsel(self, cursor, tasinmaz_no):
        """Ada/Parsel bilgisini alır"""
        cursor.execute("""
            SELECT hucreno_2 
            FROM tapu_verileri 
            WHERE tasinmaz_kimlik = ? 
            AND takyidat_baslik = 'TAPU KAYIT BİLGİSİ'
            AND hucreno_1 = 'Ada/Parsel:'
        """, (tasinmaz_no,))
        result = cursor.fetchone()
        
        if not result:
            cursor.execute("""
                SELECT hucreno_2 
                FROM tapu_verileri 
                WHERE tasinmaz_kimlik = ? 
                AND takyidat_baslik = 'TAPU KAYIT BİLGİSİ'
                AND sayfano = '1' 
                AND satirno = '10'
            """, (tasinmaz_no,))
            result = cursor.fetchone()
            
        if result:
            ada_parsel = result[0]
            if "/" in ada_parsel:
                ada, parsel = ada_parsel.split("/")
                return ada.strip(), parsel.strip()
        return None, None
        
    # Taşınmaza Ait Şerh Beyan Bilgileri veri seçimi
    def get_serh_beyan_bilgileri(self, cursor, tasinmaz_no):
        """Şerh beyan bilgilerini alır"""
        cursor.execute("""
            SELECT hucreno_1, hucreno_2, hucreno_3, hucreno_4
            FROM tapu_verileri 
            WHERE tasinmaz_kimlik = ? 
            AND takyidat_baslik = 'TAŞINMAZA AİT ŞERH BEYAN İRTİFAK BİLGİLERİ'
            AND baslikontrol = 'HAYIR'
            ORDER BY satirno
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def format_line(self, line_data):
        """Şerh beyan satırını formatlar"""
        hucreno_1, hucreno_2, hucreno_3, hucreno_4 = line_data

        # Özel kelime düzeltmeleri
        replacements = {
            'konusu:': 'Konusu:',
            'şablon:': 'Şablon:',
            'sn:': 'SN:',
            'Sn:': 'SN:',
            'vkn:': 'VKN:',
            'Vkn:': 'VKN:',
            'Müdürlüğü nün': 'Müdürlüğünün',
            '; )': ';)',
            ' :' : ':',
            'Serh' : 'Şerh',
            'Dairesi nin' : 'Dairesinin',
            'MÜDÜRLÜĞÜ nin' : 'MÜDÜRLÜĞÜNÜN',
            'DAİRESİ nin'  : 'DAİRESİNİN'
        }

        # Yevmiye formatı düzeltmesi
        if hucreno_4 and "-" in hucreno_4:
            main_part, yevmiye = hucreno_4.rsplit("-", 1)
            hucreno_4 = f"{main_part.strip()} tarih ve <b>{yevmiye.strip()}</b> yevmiye"

        # Beyan satırını oluştur
        text = f"- {hucreno_2} - {hucreno_3} {hucreno_4}"

        # Özel kelime düzeltmelerini uygula
        for old, new in replacements.items():
            text = text.replace(old, new)
            text = text.replace(old.upper(), new)

        # Parantez ve boşluk düzeltmeleri
        text = text.replace(" )", ")")
        text = text.replace("( ", "(")
        text = text.replace("  ", " ")

        return f"{text}."

    # Mülkiyete Ait Şerh Beyan Bilgileri veri seçimi
    def get_mulkiyet_serh_beyan_bilgileri(self, cursor, tasinmaz_no):
        """Mülkiyete ait şerh beyan bilgilerini alır"""
        cursor.execute("""
            SELECT hucreno_1, hucreno_2, hucreno_3, hucreno_4, hucreno_5
            FROM tapu_verileri 
            WHERE tasinmaz_kimlik = ? 
            AND takyidat_baslik = 'MÜLKİYETE AİT ŞERH BEYAN İRTİFAK BİLGİLERİ'
            AND baslikontrol = 'HAYIR'
            ORDER BY satirno
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def format_mulkiyet_line(self, line_data):
        """Mülkiyet şerh beyan satırını formatlar"""
        hucreno_1, hucreno_2, hucreno_3, hucreno_4, hucreno_5 = line_data
    
        text = f"- {hucreno_1}: {hucreno_2} {hucreno_3} {hucreno_4}"
    
        # hucreno_5'teki tarih ve yevmiye bilgisini ekle
        if hucreno_5 and "-" in hucreno_5:
            main_part, yevmiye = hucreno_5.rsplit("-", 1)
            text += f" {main_part.strip()} tarih ve <b>{yevmiye.strip()}</b> yevmiye"
    
        return f"{text}."

    def process_all_records(self):
        """Tüm taşınmaz kayıtlarını işler ve rapor metnini oluşturur"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        
            # Tüm taşınmaz ve tarih bilgilerini alalım
            cursor.execute("""
                SELECT t.tasinmaz_no, tt.tapu_tarih 
                FROM tasinmaz t 
                JOIN takbis_tarih tt ON t.tasinmaz_no = tt.tasinmaz_kimlik 
                ORDER BY t.id ASC
            """)
            kayitlar = cursor.fetchall()
        
            if not kayitlar:
                return "Kayıt bulunamadı"
            
            tam_rapor = ""
        
            for index, (tasinmaz_no, tapu_tarih) in enumerate(kayitlar, 1):
                ada, parsel, zemin_tipi, bb_detay = self.get_tasinmaz_detay(cursor, tasinmaz_no)
            
                if not ada or not parsel:
                    continue
                
                tarih, saat = self.format_datetime(tapu_tarih)
            
                # Her kayıt için başlık ekleme
                baslik = f"<br><b>{index}. TAŞINMAZ ({ada} ADA / {parsel} PARSEL)"
                if bb_detay:
                    baslik += f" - {bb_detay}"
                baslik += " TAKYİDATLARI</b><br>"
                tam_rapor += baslik

                # Rapor oluşturma
                rapor = (f"TKGM Web-Tapu portaldan elektronik ortamda {tarih} tarih ve saat {saat} itibarıyla alınan ve"
                        f" rapor ekinde yer alan Tapu Kayıt Belgesine göre <b>{ada}</b> Ada <b>{parsel}</b> Parsel"
                        f" nolu taşınmaz üzerinde aşağıda yer alan takyidat bulunmaktadır. <br>")                      

                # Önce veritabanında bu başlıkların olup olmadığını kontrol edelim
                cursor.execute("""
                    SELECT DISTINCT takyidat_baslik 
                    FROM tapu_verileri 
                    WHERE tasinmaz_kimlik = ? 
                    AND takyidat_baslik IN ('MUHDESAT BİLGİLERİ', 'EKLENTİ BİLGİLERİ')
                    AND baslikontrol = 'HAYIR'
                """, (tasinmaz_no,))
                mevcut_basliklar = [row[0] for row in cursor.fetchall()]

                # Eğer Muhdesat bilgileri varsa raporla
                if 'MUHDESAT BİLGİLERİ' in mevcut_basliklar:
                    muhdesat_kayitlar = self.get_muhdesat_bilgileri(cursor, tasinmaz_no)
                    if muhdesat_kayitlar:
                        rapor += "<br><b>Muhdesat Bilgileri Hanesinde;</b><br>"
                        for kayit in muhdesat_kayitlar:
                            formatted_line = self.format_muhdesat_line(kayit)
                            rapor += formatted_line + "<br>"

                # Eğer Eklenti bilgileri varsa raporla
                if 'EKLENTİ BİLGİLERİ' in mevcut_basliklar:
                    eklenti_kayitlar = self.get_eklenti_bilgileri(cursor, tasinmaz_no)
                    if eklenti_kayitlar:
                        rapor += "<br><b>Eklenti Bilgileri Hanesinde;</b><br>"
                        for kayit in eklenti_kayitlar:
                            formatted_line = self.format_muhdesat_line(kayit)  # Aynı format metodunu kullanabiliriz
                            rapor += formatted_line + "<br>"
                                                                                               
                kayitlar = self.get_serh_beyan_bilgileri(cursor, tasinmaz_no)
                rapor += "<br><b>Taşınmaza Ait Şerh Beyan İrtifak Bilgileri hanesinde;</b><br>"
                if kayitlar:                    
                    for kayit in kayitlar:
                        formatted_line = self.format_line(kayit)
                        rapor += formatted_line + "<br>"
                else:
                    rapor += "- Herhangi bir takyidat bulunmamaktadır.<br>"
                
                # Teferruat bilgileri
                teferruat_kayitlar = self.get_teferruat_bilgileri(cursor, tasinmaz_no)
                if teferruat_kayitlar:
                    rapor += "<br><b>Teferruat Bilgileri hanesinde;</b><br>"
                    for kayit in teferruat_kayitlar:
                        formatted_line = self.format_teferruat_line(kayit)
                        rapor += formatted_line + "<br>"

                # Mülkiyete ait şerh beyan kayıtları                
                mulkiyet_kayitlar = self.get_mulkiyet_serh_beyan_bilgileri(cursor, tasinmaz_no)                
                rapor += "<br><b>Mülkiyete Ait Şerh Beyan İrtifak Bilgileri hanesinde;</b><br>"
                if mulkiyet_kayitlar:                    
                    for kayit in mulkiyet_kayitlar:
                        formatted_line = self.format_mulkiyet_line(kayit)
                        rapor += formatted_line + "<br>"
                else:
                    rapor += "- Herhangi bir takyidat bulunmamaktadır.<br>"
                
                # İpotek bilgileri                
                ipotek_kayitlar = self.get_ipotek_bilgileri(cursor, tasinmaz_no)
                rapor += "<br><b>Mülkiyete Ait Rehin Bilgileri Hanesinde;</b><br>"
                if ipotek_kayitlar:                                                                   
                    for kayit in ipotek_kayitlar:
                        formatted_line = self.format_ipotek_line(kayit)
                        rapor += formatted_line + "<br>"
                else:
                    rapor += "- Herhangi bir takyidat bulunmamaktadır.<br>"
                
                tam_rapor += rapor + "<br>" + "_" * 50 + "<br>"
            
            return tam_rapor
        
        except Exception as e:
            self.logger.error(f"Kayıt işleme hatası: {str(e)}")
            return f"İşlem sırasında hata: {str(e)}"
        finally:
            if conn:
                conn.close()

    def get_teferruat_bilgileri(self, cursor, tasinmaz_no):
        """Teferruat bilgilerini alır"""
        cursor.execute("""
            SELECT hucreno_1, hucreno_2, hucreno_3, hucreno_4, hucreno_5, hucreno_6
            FROM tapu_verileri 
            WHERE tasinmaz_kimlik = ? 
            AND takyidat_baslik = 'TEFERRUAT BİLGİLERİ'
            AND baslikontrol = 'HAYIR'
            ORDER BY satirno
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def get_muhdesat_bilgileri(self, cursor, tasinmaz_no):
        """Muhdesat bilgilerini alır"""
        cursor.execute("""
            SELECT hucreno_1, hucreno_2, hucreno_3, takyidat_1, takyidat_2, takyidat_3
            FROM tapu_verileri 
            WHERE tasinmaz_kimlik = ? 
            AND takyidat_baslik = 'MUHDESAT BİLGİLERİ'
            AND baslikontrol = 'HAYIR'
            ORDER BY satirno
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def get_eklenti_bilgileri(self, cursor, tasinmaz_no):
        """Eklenti bilgilerini alır"""
        cursor.execute("""
            SELECT hucreno_1, hucreno_2, hucreno_3, takyidat_1, takyidat_2, takyidat_3
            FROM tapu_verileri 
            WHERE tasinmaz_kimlik = ? 
            AND takyidat_baslik = 'EKLENTİ BİLGİLERİ'
            AND baslikontrol = 'HAYIR'
            ORDER BY satirno
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def format_teferruat_line(self, line_data):
        """Teferruat satırını formatlar"""
        hucreno_1, hucreno_2, hucreno_3, hucreno_4, hucreno_5, hucreno_6 = line_data
    
        # Format monetary values
        if hucreno_5:
            # Remove spaces in decimal part and standardize format
            hucreno_5 = hucreno_5.replace(".00 000", ".00000")
        
        # Add separator between hucreno_4 and hucreno_5
        separator = " -- " if hucreno_4 and hucreno_5 else ""
    
        # Combine the text
        text = f"- {hucreno_2} {hucreno_3} {hucreno_4}{separator}{hucreno_5}{hucreno_6}"
    
        # Fix parentheses formatting
        # First ensure space before parentheses
        text = text.replace("(", " (")
    
        # Remove multiple spaces
        while "  " in text:
            text = text.replace("  ", " ")
    
        # Remove space after opening parenthesis and before closing parenthesis
        import re
        text = re.sub(r'\( +', '(', text)  # Remove spaces after opening parenthesis
        text = re.sub(r' +\)', ')', text)  # Remove spaces before closing parenthesis
        
        return f"{text}."

    def format_muhdesat_line(self, line_data):
        """Muhdesat ve Eklenti satırlarını formatlar"""
        hucreno_1, hucreno_2, hucreno_3, takyidat_1, takyidat_2, takyidat_3 = line_data

        # Ana metin oluşturma
        text = f"- {hucreno_2}, {hucreno_3},"

        # Lokasyon ve tarih bilgisi ekleme
        if takyidat_3 and takyidat_2 and takyidat_1:
            text += f" {takyidat_3} - {takyidat_2} tarih ve <b>{takyidat_1}</b> yevmiye"
        else:
            text += f" bila yevmiye"

        # Fazla boşlukları temizle
        while "  " in text:
            text = text.replace("  ", " ")
    
        return f"{text}."

    def get_ipotek_bilgileri(self, cursor, tasinmaz_no):
        """İpotek bilgilerini alır"""
        cursor.execute("""
            SELECT alacakli, borclu_malik, hisse_pay_payda, borc, faiz, 
                   derece_sira, tesis_tarih
            FROM ipotek_verileri 
            WHERE tasinmaz_kimlik = ?
            ORDER BY derece_sira
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def format_ipotek_line(self, ipotek_data):
        """İpotek satırını formatlar"""
        alacakli, borclu_malik, hisse_pay_payda, borc, faiz, derece_sira, tesis_tarih = ipotek_data
    
        # Tesis tarihi formatlaması
        if tesis_tarih and "-" in tesis_tarih:
            main_part, yevmiye = tesis_tarih.rsplit("-", 1)
            tarih_yevmiye = f"{main_part.strip()} tarih ve <b>{yevmiye.strip()}</b> yevmiye"
        else:
            tarih_yevmiye = tesis_tarih

        # Faiz formatlaması
        faiz = faiz.replace("değişk en", "değişken")
    
        # Hisse formatlaması - "hissesi" kelimesini pay/payda'dan önceye al
        if hisse_pay_payda:
            hisse_bilgisi = f"{hisse_pay_payda} hissesi"
        else:
            hisse_bilgisi = ""
    
        text = (f"- {alacakli} lehine {borclu_malik} {hisse_bilgisi} üzerinde "
                f"{borc} tutarında {faiz} oran ve {derece_sira} dereceli "
                f"İpotek Bilgisi bulunmaktadır. {tarih_yevmiye}")
    
        # Fazla boşlukları temizle
        while "  " in text:
            text = text.replace("  ", " ")
    
        return f"{text}."

    def incele(self):
        """Ana inceleme fonksiyonu"""
        is_valid, message = self.validate_database()
        if not is_valid:
            return message
        
        return self.process_all_records()

