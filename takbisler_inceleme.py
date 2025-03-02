import sqlite3
from collections import defaultdict
import json
from datetime import datetime
import logging

class CokluInceleme:
    def __init__(self, db_path='veritabani.db'):
        self.db_path = db_path
        self.json_data = None
        self.grouped_data = None
        # Özel başlıkları tanımla
        self.OZEL_BASLIKLAR = {
            'EKLENTİ BİLGİLERİ',
            'MUHDESAT BİLGİLERİ',
            'TEFERRUAT BİLGİLERİ'
        }

        self.risk_agirliklari = {
            'İPOTEK': 2,
            'HACİZ': 25,
            'TEDBİR': 25,
            'ŞERH': 0.6,
            'BEYAN': 0.5
        }

    def connect_db(self):
        """Veritabanı bağlantısını oluşturur"""
        return sqlite3.connect(self.db_path)

    def get_bb_no(self, prop):
        """Bağımsız bölüm numarasını güvenli şekilde alır"""
        bb_info = prop['Taşınmaz Bölümü']['blok_kat_girisi_bbno']
        if bb_info:
            return bb_info.split('/')[-1]
        return None

    def get_tasinmaz_count(self, conn):
        """Toplam taşınmaz sayısını döndürür"""
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasinmaz")
        return cursor.fetchone()[0]

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
            logging.error(f"Tarih format hatası: {str(e)}")
            return datetime_str, ""

    def get_takyidat_records(self, conn, tasinmaz_no):
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tv.*, tv.takyidat_1, tv.takyidat_2, tv.takyidat_3 
            FROM tapu_verileri tv
            JOIN tasinmaz t ON t.tasinmaz_no = tv.tasinmaz_kimlik
            WHERE tv.takyidat_baslik NOT IN ('TAPU KAYIT BİLGİSİ', 'MÜLKİYET BİLGİLERİ')
            AND tv.takyidat_baslik IS NOT NULL
            AND tv.takyidat_baslik != ''
            AND tv.baslikontrol != 'EVET'
            AND t.tasinmaz_no = ?
        """, (tasinmaz_no,))
        return cursor.fetchall()

    def get_ipotek_records(self, conn, tasinmaz_no):
        """İpotek kayıtlarını getirir"""
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.* 
            FROM ipotek_verileri i
            JOIN tasinmaz t ON t.tasinmaz_no = i.tasinmaz_kimlik
            WHERE t.tasinmaz_no = ?
        """, (tasinmaz_no,))
        result = cursor.fetchall()
        logging.debug(f"İpotek kayıtları: {result}")  # Debug log ekle
        return result

    def get_tasinmaz_info(self, conn, tasinmaz_no):
        """Taşınmaz bilgilerini getirir"""
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT t.tasinmaz_no, t.zemintipi, t.il_ilce, t.kurum_adi, 
                       t.mahalle, t.mevki, t.cilt_sayfa_no, t.kayitdurumu,
                       t.ada_parsel, t.at_yuzolcum, t.bb_nitelik, 
                       t.bb_brüt_yuzolcum, t.bb_net_yuzolcum,
                       t.blok_kat_girisi_bbno, t.arsa_pay_payda,
                       t.ana_tasinmaz_nitelik, tt.tapu_tarih
                FROM tasinmaz t
                LEFT JOIN takbis_tarih tt ON t.tasinmaz_no = tt.tasinmaz_kimlik
                WHERE t.tasinmaz_no = ?
            """, (tasinmaz_no,))
            result = cursor.fetchone()
            if result is None:
                logging.error(f"Taşınmaz bulunamadı: {tasinmaz_no}")
                return None
            return result
        except Exception as e:
            logging.error(f"Taşınmaz bilgisi getirme hatası: {str(e)}")
            raise

    def create_tasinmaz_data(self, tasinmaz_data, takyidat_records, ipotek_records):
        """Taşınmaz verilerini yapılandırır"""
        def extract_yevmiye(tesis_tarih):
            """tesis_tarih alanından yevmiye numarasını çıkarır"""
            if tesis_tarih and " - " in tesis_tarih:
                return tesis_tarih.split(" - ")[-1]
            return None

        if not tasinmaz_data:
            logging.error("Taşınmaz verisi boş")
            return None
        
        logging.debug(f"Taşınmaz verisi uzunluğu: {len(tasinmaz_data)}")  # Debug log
        logging.debug(f"Taşınmaz verisi içeriği: {tasinmaz_data}")  # Debug log

        try:
            return {
                "Taşınmaz Bölümü": {
                    "tapu_tarih": tasinmaz_data[16] if len(tasinmaz_data) > 16 else None,
                    "tasinmaz_no": tasinmaz_data[0] if len(tasinmaz_data) > 0 else None,
                    "zemintipi": tasinmaz_data[1] if len(tasinmaz_data) > 1 else None,
                    "il_ilce": tasinmaz_data[2] if len(tasinmaz_data) > 2 else None,
                    "mahalle": tasinmaz_data[4] if len(tasinmaz_data) > 4 else None,
                    "mevki": tasinmaz_data[5] if len(tasinmaz_data) > 5 else None,
                    "cilt_sayfa_no": tasinmaz_data[6] if len(tasinmaz_data) > 6 else None,
                    "ada_parsel": tasinmaz_data[8] if len(tasinmaz_data) > 8 else None,
                    "at_yuzolcum": tasinmaz_data[9] if len(tasinmaz_data) > 9 else None,
                    "bb_nitelik": tasinmaz_data[10] if len(tasinmaz_data) > 10 else None,
                    "blok_kat_girisi_bbno": tasinmaz_data[13] if len(tasinmaz_data) > 13 else None,
                    "arsa_pay_payda": tasinmaz_data[14] if len(tasinmaz_data) > 14 else None,
                    "ana_tasinmaz_nitelik": tasinmaz_data[15] if len(tasinmaz_data) > 15 else None        
                },
                "Şerh Beyan İrtifak Bölümü": [
                    {
                        "takyidat_baslik": record[15] if len(record) > 15 else None,
                        "takyidat_1": record[16] if len(record) > 16 else None,
                        "takyidat_2": record[17] if len(record) > 17 else None,  
                        "takyidat_3": record[18] if len(record) > 18 else None, 
                        "sayfano": record[0] if len(record) > 0 else None,
                        "satirno": record[1] if len(record) > 1 else None,
                        "hucreno_1": record[2] if len(record) > 2 else None,
                        "hucreno_2": record[3] if len(record) > 3 else None,
                        "hucreno_3": record[4] if len(record) > 4 else None,
                        "hucreno_4": record[5] if len(record) > 5 else None,
                        "hucreno_5": record[6] if len(record) > 6 else None,
                        "hucreno_6": record[7] if len(record) > 7 else None,
                        "hucreno_7": record[8] if len(record) > 8 else None,
                        "hucreno_8": record[9] if len(record) > 9 else None,
                        "hucreno_9": record[10] if len(record) > 10 else None,
                        "hucreno_10": record[11] if len(record) > 11 else None,
                        "hucreno_11": record[12] if len(record) > 12 else None
                    } for record in takyidat_records
                ],
                "İpotekler Bölümü": [
                    {
                        "yevmiye_no": extract_yevmiye(record[10]),  # tesis_tarih'ten yevmiye no çıkar
                        "id": record[0],
                        "tapu_tarih": record[1],
                        "tasinmaz_kimlik": record[2],
                        "sayfa_no": record[3],
                        "alacakli": record[4],
                        "musterek_mi": record[5],
                        "borc": record[6],
                        "faiz": record[7],
                        "derece_sira": record[8],
                        "sure": record[9],
                        "tesis_tarih": record[10],
                        "tasinmaz": record[11],
                        "hisse_pay_payda": record[12],
                        "borclu_malik": record[13],
                        "sn_bilgisi": record[14],
                        "malik_borc": record[15],
                        "tescil_tarih": record[16],
                        "terkin": record[17]
                    } for record in ipotek_records
                ]
            }
        except Exception as e:
            logging.error(f"create_tasinmaz_data hatası: {str(e)}")
            raise

    def debug_database(self):
        conn = self.connect_db()
        cursor = conn.cursor()
        try:
            # Taşınmaz tablosundaki tüm kolonları ve bir kayıt örneğini göster
            cursor.execute("PRAGMA table_info(tasinmaz)")
            columns = cursor.fetchall()
            logging.debug("Taşınmaz tablo yapısı:")
            for col in columns:
                logging.debug(f"Kolon: {col}")
            
            cursor.execute("SELECT * FROM tasinmaz LIMIT 1")
            sample = cursor.fetchone()
            logging.debug(f"Örnek kayıt: {sample}")
        
        except Exception as e:
            logging.error(f"Debug hatası: {str(e)}")
        finally:
            conn.close()

    def create_json_data(self):
        """Veritabanından JSON verisi oluşturur"""
        self.debug_database()  # Debug fonksiyonunu çağır
        conn = self.connect_db()
        try:
            tasinmaz_count = self.get_tasinmaz_count(conn)
        
            if tasinmaz_count == 0:
                logging.info("Veritabanında hiç taşınmaz kaydı bulunamadı.")
                return {
                    "status": "empty",
                    "message": "Veritabanında henüz hiç taşınmaz kaydı bulunmamaktadır. Lütfen önce taşınmaz verilerini içeri aktarın."
                }
        
            if tasinmaz_count < 1:
                logging.info(f"Veritabanında sadece {tasinmaz_count} adet taşınmaz kaydı bulundu.")
                return {
                    "status": "insufficient",
                    "message": f"Veritabanında şu anda {tasinmaz_count} adet taşınmaz kaydı bulunmaktadır. Karşılaştırmalı rapor için en az 2 taşınmaz kaydı gereklidir."
                }

            cursor = conn.cursor()
            cursor.execute("SELECT tasinmaz_no FROM tasinmaz")
            tasinmaz_numbers = cursor.fetchall()

            all_data = {}
            for tasinmaz_no in tasinmaz_numbers:
                tasinmaz_no = tasinmaz_no[0]
                tasinmaz_data = self.get_tasinmaz_info(conn, tasinmaz_no)
                takyidat_records = self.get_takyidat_records(conn, tasinmaz_no)
                ipotek_records = self.get_ipotek_records(conn, tasinmaz_no)

                all_data[f"Tasinmaz_{tasinmaz_no}"] = self.create_tasinmaz_data(
                    tasinmaz_data, 
                    takyidat_records, 
                    ipotek_records
                )

            # Hafızada tut
            self.json_data = all_data

            # JSON dosyası olarak da kaydet
            #timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"coklu_takbis.json"
        
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=4)
                logging.info(f"JSON dosyası oluşturuldu: {filename}")
            except Exception as e:
                logging.error(f"JSON dosyası oluşturma hatası: {str(e)}")

            return all_data

        except Exception as e:
            error_msg = f"Veri oluşturma hatası: {str(e)}"
            logging.error(error_msg)
            return {
                "status": "error",
                "message": "Veriler işlenirken bir hata oluştu. Lütfen tekrar deneyin."
            }
        finally:
            conn.close()

    def group_properties(self):
        """Taşınmazları ada/parsel bazında gruplar"""
        if not self.json_data:
            raise ValueError("Önce create_json_data() metodunu çalıştırın")
            
        grouped = {}
        for tasinmaz_id, data in self.json_data.items():
            ada_parsel = data['Taşınmaz Bölümü']['ada_parsel']
            if ada_parsel not in grouped:
                grouped[ada_parsel] = []
            grouped[ada_parsel].append(data)
        self.grouped_data = grouped
        return grouped

    def format_teferruat_line(self, teferruat):
        """Teferruat bilgisini formatlar"""
        return f"- {teferruat['hucreno_2']} - Değeri: {teferruat['hucreno_5']}"

    def format_teferruat(self, teferruat, bb_numbers):
        """Teferruat bilgilerini formatlar"""
        content = f"- {teferruat['hucreno_2']} - Değeri: {teferruat['hucreno_5']}"
    
        if bb_numbers:
            bb_list = ", ".join(sorted(bb_numbers))
            if len(bb_numbers) > 1:
                content += f" ({bb_list} nolu BB.ler müşterek olarak)"
            else:
                content += f" ({bb_list} nolu BB.)"
    
        return content

    def format_header(self, properties):
        """Rapor başlığını ve bağımsız bölüm bilgilerini formatlar"""
        bb_texts = []
        for prop in properties:
            tasim = prop['Taşınmaz Bölümü']
            bb_no = self.get_bb_no(prop)
            if bb_no and tasim['bb_nitelik']:
                # tapu_tarih varsa formatla ve ekle
                if tasim['tapu_tarih']:
                    tarih, saat = self.format_datetime(tasim['tapu_tarih'])
                    bb_texts.append(f"({tasim['ada_parsel']} parsel {bb_no} Nolu BB. {tasim['bb_nitelik']} Nitelikli Gayrimenkul {tarih} tarih ve saat {saat})")
                else:
                    bb_texts.append(f"({tasim['ada_parsel']} parsel {bb_no} Nolu BB. {tasim['bb_nitelik']} Nitelikli Gayrimenkul)")
            elif not bb_no and not tasim['bb_nitelik']:
                # Bağımsız bölüm olmayan gayrimenkuller için
                if tasim['tapu_tarih']:
                    tarih, saat = self.format_datetime(tasim['tapu_tarih'])
                    bb_texts.append(f"({tasim['ada_parsel']} parsel {tarih} tarih ve saat {saat})")
                else:
                    bb_texts.append(f"({tasim['ada_parsel']} parsel)")
    
        header = "<br>TKGM Web-Tapu portaldan elektronik ortamda " + " ".join(bb_texts)
        return header + " tarih ve saat itibarıyla alınan ve rapor ekinde yer alan Tapu Kayıt Belgesine göre taşınmaz üzerinde aşağıda yer alan bilgiler bulunmaktadır.<br>"

    def format_ipotek(self, ada_parsel, ipotek, bb_numbers=None, ada_parseller=None):
        """İpotek satırını formatlar"""
        if bb_numbers:
            bb_list = ", ".join(sorted(bb_numbers))
            if len(bb_numbers) > 1:
                bb_part = f"- {bb_list} nolu BB.ler üzerinde müşterek olarak"
            else:
                bb_part = f"- {bb_list} nolu BB. üzerinde"
            line = f"- {ada_parsel} parsel {bb_part}"
        elif ada_parseller and len(ada_parseller) > 1:
            parsel_list = " ve ".join(sorted(ada_parseller))
            line = f"- {parsel_list} parseller üzerinde müşterek olarak"
        else:
            line = f"- {ada_parsel} parsel üzerinde"

        if ipotek.get('alacakli'):  # Boş ipotek kontrolü
            line += f": Alacaklı {ipotek['alacakli']} lehine "
            if ipotek.get('borclu_malik'):
                line += f"{ipotek['borclu_malik']} "
            if ipotek.get('hisse_pay_payda'):
                line += f"{ipotek['hisse_pay_payda']} hissesi üzerinde "
            if ipotek.get('borc'):
                line += f"{ipotek['borc']} tutarında "
            if ipotek.get('faiz'):
                line += f"{ipotek['faiz']} oran ve "
            if ipotek.get('derece_sira'):
                line += f"{ipotek['derece_sira']} dereceli İpotek Bilgisi bulunmaktadır."

            if ipotek.get('yevmiye_no'):
                if ipotek.get('tesis_tarih'):
                    tarih_part = ipotek['tesis_tarih'].rsplit(" - ", 1)[0]
                    line += f" {tarih_part} tarih ve <b>{ipotek['yevmiye_no']}</b> yevmiye nolu."
                else:
                    line += f" <b>{ipotek['yevmiye_no']}</b> yevmiye nolu."
        else:
            line += " Herhangi bir ipotek bulunmamaktadır."

        return line

    def format_takyidat(self, takyidat, bb_numbers=None, ada_parseller=None, extra_yevmiye=None):
        """Takyidat satırını formatlar"""
    
        # Başlangıç kısmını oluştur
        if bb_numbers:
            bb_info = ", ".join(sorted(bb_numbers))
            content = f"{bb_info} nolu BB - "
        elif ada_parseller:
            parsel_info = " ve ".join(sorted(ada_parseller))
            content = f"{parsel_info} parsel - "
        else:
            content = "- "

        # Ana içeriği ekle
        content += f"{takyidat['hucreno_2']}"

        if takyidat['hucreno_3']:
            content += f" {takyidat['hucreno_3']}"

        # Lokasyon ve tarih bilgisini doğrudan takyidat_2 ve takyidat_3'ten al
        if takyidat.get('takyidat_3') and takyidat.get('takyidat_2'):
            content += f" {takyidat['takyidat_3']} - {takyidat['takyidat_2']}"
    
        # Yevmiye bilgisini ekle
        yevmiye_no = takyidat.get('takyidat_1', '')
        if yevmiye_no:
            content += f" tarih ve <b>{yevmiye_no}</b> yevmiye nolu."
        else:
            content += " bila yevmiye."

        return content
    
    def merge_takyidats(self, properties):
        """Takyidatları başlıklarına göre gruplar ve benzer içerikli olanları birleştirir"""
        merged = {}

        # Bağımsız bölüm kontrolü
        is_bagimsiz_bolum = properties[0]['Taşınmaz Bölümü'].get('bb_nitelik') and properties[0]['Taşınmaz Bölümü'].get('blok_kat_girisi_bbno')

        for prop in properties:
            bb_no = self.get_bb_no(prop) if is_bagimsiz_bolum else None
            ada_parsel = prop['Taşınmaz Bölümü']['ada_parsel']

            for takyidat in prop['Şerh Beyan İrtifak Bölümü']:
                # "MÜLKİYETE AİT REHİN BİLGİLERİ" başlıklı ve boş içerikli kayıtları atla
                if (takyidat['takyidat_baslik'] == 'MÜLKİYETE AİT REHİN BİLGİLERİ' and 
                    not takyidat['hucreno_2'].strip()):
                    continue
            
                takyidat_baslik = takyidat['takyidat_baslik']
                yevmiye = takyidat['takyidat_1']
                tarih = takyidat['takyidat_2']
                lokasyon = takyidat['takyidat_3']
                content = takyidat['hucreno_2']
            
                # Özel başlıklar için farklı bir işlem yap
                if takyidat_baslik in self.OZEL_BASLIKLAR:
                    # BB no veya ada/parsel ile birlikte benzersiz key oluştur
                    unique_key = f"{bb_no if bb_no else ada_parsel}_{content}"
                    if takyidat_baslik not in merged:
                        merged[takyidat_baslik] = {}
                
                    merged[takyidat_baslik][unique_key] = {
                        'content': takyidat,
                        'bb_numbers': {bb_no} if bb_no else None,
                        'ada_parseller': {ada_parsel} if not bb_no else None,
                        'yevmiye': yevmiye,
                        'tarih': tarih,
                        'lokasyon': lokasyon
                    }
                    continue

                # Normal başlıklar için işlem
                simplified_content = content.lower().replace(" ", "")[:100]
                key = f"{simplified_content}_{tarih}_{lokasyon}"

                if takyidat_baslik not in merged:
                    merged[takyidat_baslik] = {}

                matching_key = None
                for existing_key in merged[takyidat_baslik].keys():
                    existing_data = merged[takyidat_baslik][existing_key]
                    existing_content = existing_data['content']['hucreno_2']
                    existing_simplified = existing_content.lower().replace(" ", "")[:100]

                    try:
                        similarity = sum(a == b for a, b in zip(simplified_content, existing_simplified)) / max(len(simplified_content), len(existing_simplified))
                    except ZeroDivisionError:
                        similarity = 0

                    if similarity > 0.90 and tarih == existing_data['tarih'] and lokasyon == existing_data['lokasyon']:
                        matching_key = existing_key
                        break

                if matching_key:
                    key = matching_key
                else:
                    merged[takyidat_baslik][key] = {
                        'content': takyidat,
                        'bb_numbers': set() if is_bagimsiz_bolum else None,
                        'ada_parseller': set() if not is_bagimsiz_bolum else None,
                        'yevmiye': yevmiye,
                        'tarih': tarih,
                        'lokasyon': lokasyon
                    }

                if is_bagimsiz_bolum and bb_no:
                    merged[takyidat_baslik][key]['bb_numbers'].add(bb_no)
                elif not is_bagimsiz_bolum:
                    merged[takyidat_baslik][key]['ada_parseller'].add(ada_parsel)

        return merged

    def merge_ipoteks(self, properties):
        """Aynı yevmiye numaralı ipotekleri birleştirir"""
        merged = {}
    
        # Bağımsız bölüm kontrolü
        is_bagimsiz_bolum = properties[0]['Taşınmaz Bölümü'].get('bb_nitelik') and properties[0]['Taşınmaz Bölümü'].get('blok_kat_girisi_bbno')
    
        for prop in properties:
            bb_no = self.get_bb_no(prop) if is_bagimsiz_bolum else None
            ada_parsel = prop['Taşınmaz Bölümü']['ada_parsel']
        
            for ipotek in prop['İpotekler Bölümü']:
                yevmiye = ipotek['yevmiye_no']
                borc = ipotek['borc']
            
                # Yevmiye ve borç tutarı bazlı birleştirme anahtarı
                key = f"{yevmiye}_{borc}"
            
                if key not in merged:
                    merged[key] = {
                        'data': ipotek,
                        'bb_numbers': set() if is_bagimsiz_bolum else None,
                        'ada_parseller': set() if not is_bagimsiz_bolum else None
                    }
            
                if is_bagimsiz_bolum and bb_no:
                    merged[key]['bb_numbers'].add(bb_no)
                elif not is_bagimsiz_bolum:
                    merged[key]['ada_parseller'].add(ada_parsel)
    
        return merged

    def generate_report(self):
        if not self.json_data:
            return "Veri bulunamadı."

        report_lines = []
    
        # Tüm properties'i tek bir liste halinde al
        all_properties = [data for data in self.json_data.values()]

        # Bağımsız bölümleri ve olmayanları ayır
        bb_properties = []
        non_bb_properties = []

        for prop in all_properties:
            is_bb = prop['Taşınmaz Bölümü'].get('bb_nitelik') and prop['Taşınmaz Bölümü'].get('blok_kat_girisi_bbno')
            if is_bb:
                bb_properties.append(prop)
            else:
                non_bb_properties.append(prop)

        # Bağımsız bölüm olmayanlar için tek bir rapor oluştur
        if non_bb_properties:
            # Parsel listesini oluştur
            parsel_list = sorted([prop['Taşınmaz Bölümü']['ada_parsel'] for prop in non_bb_properties])
            parsel_str = " VE ".join(parsel_list)

            # Başlık oluştur
            title = f"{parsel_str} PARSEL NOLU TAŞINMAZLAR TAKYİDATLARI"

            # Header bilgilerini oluştur
            header_parts = []
            for prop in non_bb_properties:
                base_text = f"({prop['Taşınmaz Bölümü']['ada_parsel']} parsel"
                if prop['Taşınmaz Bölümü']['tapu_tarih']:  # tapu_tarih varsa ekle
                    base_text += f" {prop['Taşınmaz Bölümü']['tapu_tarih']}"
                base_text += ")"
                header_parts.append(base_text)

            report_lines.extend([
                "<br>",
                f"<b>{title}</b>",
                "<br>",
                f"TKGM Web-Tapu portaldan elektronik ortamda {' '.join(header_parts)}\n"
                f"tarih ve saat itibarıyla alınan ve rapor ekinde yer alan Tapu Kayıt Belgesine göre "
                f"taşınmaz üzerinde aşağıda yer alan bilgiler bulunmaktadır.<br>",
                "<br>"
            ])
            # Takyidatları yazdır
            merged_takyidats = self.merge_takyidats(non_bb_properties)
            if merged_takyidats:
                for baslik, takyidatlar in merged_takyidats.items():
                    report_lines.append(f"<b>{baslik} hanesinde;</b><br>")
                    for key, data in takyidatlar.items():
                        line = self.format_takyidat(
                            data['content'], 
                            None,  # bb_numbers
                            data['ada_parseller'],  # ada_parseller
                            data.get('extra_yevmiye')  # extra_yevmiye
                        )
                        report_lines.append(f"{line}<br>")
                    report_lines.append("<br>")

            # İpotekleri yazdır
            report_lines.append("<b>MÜLKİYETE AİT REHİN BİLGİLERİ hanesinde;</b><br>")
            merged_ipoteks = self.merge_ipoteks(non_bb_properties)
            if merged_ipoteks:
                for key, data in merged_ipoteks.items():
                    line = self.format_ipotek(parsel_list[0], data['data'], None, data['ada_parseller'])
                    report_lines.append(f"{line}<br>")
            else:
                report_lines.append("- Herhangi bir ipotek bulunmamaktadır.<br>")

            report_lines.extend([
                "<br>",
                "_" * 50,
                "<br>"
            ])

        # Bağımsız bölümler için
        if bb_properties:
            # Bağımsız bölümleri ada/parsel bazında grupla
            bb_grouped = {}
            for prop in bb_properties:
                ada_parsel = prop['Taşınmaz Bölümü']['ada_parsel']
                if ada_parsel not in bb_grouped:
                    bb_grouped[ada_parsel] = []
                bb_grouped[ada_parsel].append(prop)

            # Her ada/parsel grubu için rapor oluştur
            for ada_parsel, properties in bb_grouped.items():
                first_prop = properties[0]['Taşınmaz Bölümü']
            
                # Başlık oluşturma
                bb_list = []
                for prop in properties:
                    bb_no = self.get_bb_no(prop)
                    if bb_no:
                        bb_list.append(bb_no)

                # Sayısal sıralama yap ve string'e çevir
                sorted_numbers = sorted(bb_list)
                bb_list_str = [str(num) for num in sorted_numbers]

                if len(bb_list_str) == 0:
                    bb_str = ""  # Varsayılan değer veya hata yönetimi
                elif len(bb_list_str) == 1:
                    bb_str = bb_list_str[0]
                elif len(bb_list_str) == 2:
                    bb_str = " ve ".join(bb_list_str)
                else:
                    bb_str = ", ".join(bb_list_str[:-1]) + " ve " + bb_list_str[-1]

                title = f"{ada_parsel} PARSEL {bb_str} NOLU BAĞIMSIZ BÖLÜM TAKYİDATLARI"
            
                report_lines.extend([
                    "<br>",
                    f"<b>{title}</b>",
                    "<br>",
                    self.format_header(properties),
                    "<br>"
                ])

                # Takyidatları yazdır
                merged_takyidats = self.merge_takyidats(properties)
                if merged_takyidats:
                    for baslik, takyidatlar in merged_takyidats.items():
                        report_lines.append(f"<b>{baslik} hanesinde;</b><br>")
                        for key, data in takyidatlar.items():
                            line = self.format_takyidat(
                                data['content'], 
                                data['bb_numbers'],  # bb_numbers
                                None,  # ada_parseller
                                data.get('extra_yevmiye')  # extra_yevmiye
                            )
                            report_lines.append(f"{line}<br>")
                        report_lines.append("<br>")

                # İpotek bilgileri
                report_lines.append("<b>MÜLKİYETE AİT REHİN BİLGİLERİ hanesinde;</b><br>")
                merged_ipoteks = self.merge_ipoteks(properties)
                if merged_ipoteks:
                    for key, data in merged_ipoteks.items():
                        line = self.format_ipotek(ada_parsel, data['data'], data['bb_numbers'])
                        report_lines.append(f"{line}<br>")
                else:
                    report_lines.append("- Herhangi bir ipotek bulunmamaktadır.<br>")

                report_lines.extend([
                    "<br>",
                    "_" * 50,
                    "<br>"
                ])

        return "\n".join(report_lines)

    def save_report(self, filename=None):
        """Raporu dosyaya kaydeder"""
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'takbis_rapor_{timestamp}.txt'
    
        report_content = self.generate_report()
    
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            return f"Rapor başarıyla kaydedildi: {filename}"
        except Exception as e:
            return f"Rapor kaydedilirken hata oluştu: {str(e)}"

    def save_json(self, filename=None):
        """JSON verisini dosyaya kaydeder"""
        if not self.json_data:
            self.create_json_data()
            
        if filename is None:
            filename = "tum_tasinmazlar.json"
            
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.json_data, f, ensure_ascii=False, indent=4)
        
        return f"JSON dosyası oluşturuldu: {filename}"

    def takyidat_turu_belirle(self, takyidat):
        """
        Takyidat türünü hucreno_1 ve hucreno_2 içeriğine göre belirler
        Args:
            takyidat: Tüm takyidat verilerini içeren sözlük
        Returns:
            str: Takyidat türü
        """
        try:
            # Büyük/küçük harf duyarlılığını kaldır
            hucreno_1 = str(takyidat.get('hucreno_1', '')).upper()
            hucreno_2 = str(takyidat.get('hucreno_2', '')).upper()

            # HACİZ kontrolü
            haciz_terimleri = ['HACZİ', 'HACIZ', 'İCRAİ HACIZ', 'KAMUHACZİ', 'KAMU HACZİ', 'KAMU HACZ', 'İCRAİHACIZ']
            ipotek_haciz = 'İPOTEĞİN PARAYA ÇEVRİLMESİ'
        
            # Hucreno_2'de haciz terimleri kontrolü
            if any(terim in hucreno_2 for terim in haciz_terimleri):
                return 'HACİZ'
            
            # Hucreno_1'de ipotek haczi kontrolü
            if ipotek_haciz in hucreno_1:
                return 'HACİZ'

            # TEDBİR kontrolü
            tedbir_terimleri = ['İHTİYATİ TEDBİR', 'İHTİYATİ', 'TEDBİR']
            if any(terim in hucreno_1 for terim in tedbir_terimleri) or \
               any(terim in hucreno_2 for terim in tedbir_terimleri):
                return 'TEDBİR'

            # İPOTEK kontrolü - bu kısım yalnızca normal şerh/beyan bölümündeki ipotekler için
            if 'İPOTEK' in hucreno_2 or 'REHİN' in hucreno_2:
                return 'İPOTEK'

            # Diğer takyidatlar için basit kontrol
            if 'ŞERH' in takyidat.get('takyidat_baslik', '').upper():
                return 'ŞERH'
            if 'BEYAN' in takyidat.get('takyidat_baslik', '').upper():
                return 'BEYAN'

            return 'DİĞER'

        except Exception as e:
            logging.error(f"Takyidat türü belirleme hatası: {str(e)}")
            return 'DİĞER'

    def risk_skoru_hesapla(self, tasinmaz_data):
        """Taşınmaz için risk skoru hesaplar"""
        skor = 0
        takyidat_sayilari = defaultdict(int)

        # Şerh Beyan İrtifak bölümünü kontrol et
        for takyidat in tasinmaz_data['Şerh Beyan İrtifak Bölümü']:
            tur = self.takyidat_turu_belirle(takyidat)
            takyidat_sayilari[tur] += 1
            skor += self.risk_agirliklari.get(tur, 0)

        # İpotek bölümünü ayrıca kontrol et
        ipotek_sayisi = len(tasinmaz_data['İpotekler Bölümü'])
        if ipotek_sayisi > 0:
            takyidat_sayilari['İPOTEK'] += ipotek_sayisi
            # Her ipotek için risk skoru ekle
            skor += (self.risk_agirliklari['İPOTEK'] * ipotek_sayisi)
    
        # Skoru yuvarlayarak döndür
        yuvarlanmis_skor = round(skor)
        return yuvarlanmis_skor, dict(takyidat_sayilari)

    def takyidat_yasini_hesapla(self, tarih_str):
        """Takyidatın yaşını hesaplar"""
        try:
            if not tarih_str:
                return None
            
            # Tarih formatlarını temizle ve standartlaştır
            tarih_str = tarih_str.split()[0]  # Saat kısmını kaldır
        
            # Olası tarih formatları
            format_list = [
                '%d.%m.%Y',  # 01.12.2020
                '%d-%m-%Y',  # 01-12-2020
                '%Y-%m-%d',  # 2020-12-01
                '%Y.%m.%d',  # 2020.12.01
                '%d/%m/%Y'   # 01/12/2020
            ]
        
            # Tüm formatları dene
            for date_format in format_list:
                try:
                    tarih = datetime.strptime(tarih_str, date_format)
                    bugun = datetime.now()
                    yas = (bugun - tarih).days
                    return yas
                except ValueError:
                    continue
                
            # Hiçbir format uymadıysa
            logging.error(f"Desteklenmeyen tarih formatı: {tarih_str}")
            return None
        
        except Exception as e:
            logging.error(f"Tarih hesaplama hatası: {str(e)}")
            return None

    def takyidat_analiz_raporu(self):
        """Detaylı takyidat analiz raporu oluşturur"""
        if not self.json_data:
            self.create_json_data()

        analiz_sonuclari = {
            'genel_istatistikler': defaultdict(int),
            'risk_gruplari': defaultdict(list),
            'takyidat_yaslanma': defaultdict(list),
            'detayli_analiz': {}
        }

        for tasinmaz_id, data in self.json_data.items():
            risk_skoru, takyidat_sayilari = self.risk_skoru_hesapla(data)
            
            if risk_skoru == 0:
                risk_grubu = '✅ Temiz'
            elif risk_skoru < 5:
                risk_grubu = '🟢 Düşük Riskli'
            elif risk_skoru < 10:
                risk_grubu = '🟡 Orta Riskli'
            elif risk_skoru < 20:
                risk_grubu = '⚠️ Riskli'
            else:
                risk_grubu = '🔴 Yüksek Riskli'
                
            analiz_sonuclari['risk_gruplari'][risk_grubu].append(tasinmaz_id)

            for takyidat in data['Şerh Beyan İrtifak Bölümü']:
                yas = self.takyidat_yasini_hesapla(takyidat.get('takyidat_2'))
                if yas is not None:
                    analiz_sonuclari['takyidat_yaslanma'][takyidat['takyidat_baslik']].append(yas)

            analiz_sonuclari['detayli_analiz'][tasinmaz_id] = {
                'risk_skoru': risk_skoru,
                'risk_grubu': risk_grubu,
                'takyidat_sayilari': takyidat_sayilari,
                'tasinmaz_bilgisi': data['Taşınmaz Bölümü']
            }

            for tur, sayi in takyidat_sayilari.items():
                analiz_sonuclari['genel_istatistikler'][tur] += sayi

        return self.takyidat_raporu_formatla(analiz_sonuclari)

    def takyidat_raporu_formatla(self, analiz_sonuclari):
        """Analiz sonuçlarını okunabilir formatta düzenler"""
        rapor_metni = []
        
        rapor_metni.extend([
            "<br>",
            "<b>TAKYİDAT ANALİZ RAPORU</b>",
            "<br>",
            f"Rapor Tarihi: {datetime.now().strftime('%d-%m-%Y %H:%M')}",
            "<br>",
            "<br>"
        ])

        rapor_metni.extend([
            "<b>1. GENEL İSTATİSTİKLER</b>",
            "<br>"
        ])
        toplam_takyidat = sum(analiz_sonuclari['genel_istatistikler'].values())
        for tur, sayi in analiz_sonuclari['genel_istatistikler'].items():
            yuzde = (sayi / toplam_takyidat * 100) if toplam_takyidat > 0 else 0
            rapor_metni.append(f"- {tur}: {sayi} adet (%.2f%%)" % yuzde)
        rapor_metni.append("<br>")

        rapor_metni.extend([
            "<b>4. DETAYLI RİSK ANALİZİ</b>",
            "<br>"
        ])

        # Detaylı analizi risk skoruna göre sırala
        sorted_analysis = sorted(
            analiz_sonuclari['detayli_analiz'].items(),
            key=lambda x: x[1]['risk_skoru'],
            reverse=True  # Yüksek skordan düşüğe doğru sırala
        )

        for tasinmaz_id, detay in sorted_analysis:
            tasb = detay['tasinmaz_bilgisi']
            bb_no = self.get_bb_no({'Taşınmaz Bölümü': tasb})
        
            tasinmaz_tanim = f"{tasb['ada_parsel']}"
            if bb_no:
                tasinmaz_tanim += f" BB No: {bb_no}"
            
            rapor_metni.extend([
                f"<b>{tasinmaz_tanim}</b>",
                f"- Risk Skoru: {detay['risk_skoru']}",
                f"- Risk Grubu: {detay['risk_grubu']}",
                "- Takyidat Dağılımı:"
            ])
        
            for tur, sayi in detay['takyidat_sayilari'].items():
                rapor_metni.append(f"  * {tur}: {sayi} adet")
            rapor_metni.append("<br>")

        return "\n".join(rapor_metni)

    def incele(self):
        """Ana rapor fonksiyonu"""
        if not self.json_data:
            result = self.create_json_data()
            
            if isinstance(result, dict) and "status" in result:
                if result["status"] in ["empty", "insufficient", "error"]:
                    return f"""
                    ⚠️ Bilgilendirme:
                    {result["message"]}
                    ...
                    """
            
            self.json_data = result
            self.group_properties()
    
        normal_rapor = self.generate_report()
        takyidat_rapor = self.takyidat_analiz_raporu()
        
        return normal_rapor + "\n" + takyidat_rapor

