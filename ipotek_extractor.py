import os
import pdfplumber
import json
import logging
import re
import sqlite3
from difflib import SequenceMatcher


class IpotekKoordinatExtractor:
    def __init__(self, db_path=None, banks_json_path=None):
        # Veritabanı yolunu parametre olarak al
        self.db_path = db_path or 'veritabani.db'
        self.banks_json_path = banks_json_path or 'banks.json'

        # Düzeltilecek kısaltmalar sözlüğü
        self.format_fixes = {
            '.ş.': 'A.Ş.',
            '.a.ş.': 'A.Ş.',
            'A.ş.': 'A.Ş.',
            'a.ş.': 'A.Ş.',
            'A.s.': 'A.Ş.',
            'a.s.': 'A.Ş.',
            'Ltd.ş.': 'Ltd.Şti.',
            'ltd.ş.': 'Ltd.Şti.',
            'LTD.Ş.': 'Ltd.Şti.',
            't.a.o.': 'T.A.O.',
            '.t.a.o.': 'T.A.O.',
            'T.a.o.': 'T.A.O.'
        }

        # Varsayılan banka listesi
        self.default_banks = {
            '4810058590': 'Türkiye İş Bankası A.Ş.',
            '9980069675': 'Türkiye Cumhuriyeti Ziraat Bankası A.Ş.',
            '8790017566': 'Türkiye Garanti Bankası A.Ş.',
            '9370014354': 'Yapı ve Kredi Bankası A.Ş.',
            '9370020892': 'Yapı ve Kredi Bankası A.Ş.',
            '0150015264': 'Akbank T.A.Ş.',
            '9220039789': 'Türkiye Vakıflar Bankası T.A.O.',
            '9220034970': 'Türkiye Vakıflar Bankası T.A.O.',
            '4290049462': 'Türkiye Halk Bankası A.Ş.',
            '4560004685': 'Türkiye Halk Bankası A.Ş.',
            '7840068284': 'QNB Finansbank A.Ş.',
            '3880023334': 'QNB Finansbank A.Ş.',
            '7590039478': 'Denizbank A.Ş.',
            '2920084496': 'Denizbank A.Ş.',
            '0680015990': 'HSBC Bank A.Ş.',
            '3250060039': 'ING Bank A.Ş.',
            '2920084764': 'Türk Ekonomi Bankası A.Ş.',
            '8760043420': 'Türk Ekonomi Bankası A.Ş.',
            '0750056946': 'Anadolubank A.Ş.',
            '2860013350': 'Şekerbank T.A.Ş.',
            '8010048575': 'Şekerbank T.A.Ş.',
            '2040042843': 'Alternatifbank A.Ş.',
            '4580037181': 'Fibabanka A.Ş.',
            '2090007808': 'Fibabanka A.Ş.',
            '5730014306': 'Koçbank A.Ş.',
            '9490003459': 'Turkish Bank A.Ş.',
            '9510014062': 'Turkland Bank A.Ş.',
            '8610061308': 'ICBC Turkey Bank A.Ş.',
            '2010431938': 'Bank of China Turkey A.Ş.',
            '2010483226': 'Rabobank A.Ş.',
            '6030067400': 'Nurol Yatırım Bankası A.Ş.',
            '6290024726': 'Aktif Yatırım Bankası A.Ş.',
            '1400032310': 'Burgan Bank A.Ş.',
            '3890022831': 'İstanbul Takas ve Saklama Bankası A.Ş.',
            '3010006447': 'İller Bankası A.Ş.',
            '2020445914': 'Bank Mellat',
            '4780154385': 'Habib Bank Limited',
            '2090014155': 'Arap Türk Bankası A.Ş.',
            '8750068235': 'Société Générale (SA)',
            '3460039122': 'JPMorgan Chase Bank N.A.',
            '6490408527': 'Citibank A.Ş.',
            '8010015359': 'Deutsche Bank A.Ş.',
            '2010442750': 'Bank of America Yatırım Bank A.Ş.',
            '2010335291': 'Merrill Lynch Yatırım Bank A.Ş.',
            '7350068295': 'Pasha Yatırım Bankası A.Ş.',
            '8490068160': 'Goldman Sachs TK Yatırım Bankacılığı A.Ş.',
            '2010358734': 'Standard Chartered Yatırım Bankası Türk A.Ş.',
            '6290068498': 'Emlak Katılım Bankası A.Ş.',
            '8790015277': 'Türkiye Emlak Bankası A.Ş.',
            '3580065777': 'Kuveyt Türk Katılım Bankası A.Ş.',
            '6000026814': 'Kuveyt Türk Katılım Bankası A.Ş.',
            '9800148343': 'Ziraat Katılım Bankası A.Ş.',
            '9980793117': 'Ziraat Katılım Bankası A.Ş.', 
            '0630201483': 'Albaraka Türk Katılım Bankası A.Ş.',
            '9860233352': 'Vakıf Katılım Bankası A.Ş.',
            '6110312806': 'Maliye Hazinesi',
            '7960069236': 'Türkiye Finans Katılım Bankası A.Ş.'
        }

        # JSON dosyasından banka bilgilerini yükle
        self.banks = self.load_banks()


        # Banka isimlerinin normalize edilmiş hallerini hazırla
        self.bank_names = {}
        for vkn, name in self.banks.items():
            normalized_name = self.normalize_text(name)
            if normalized_name not in self.bank_names:
                self.bank_names[normalized_name] = name

        # Filigran karakterleri
        self.filigran_karakterler = {
            "B", "İ", "L", "G", "İ", "A", "M", "A", "Ç", "L", "I", "D", "R"
        }
        
        # İpotek alanları için koordinat bölgeleri
        self.ipotek_alanlari = {
            'alacakli': {'x0': 40, 'x1': 250, 'y0': 70, 'y1': 220},       # ilk değer 160 idi yaptım
            'musterek_mi': {'x0': 260, 'x1': 320, 'y0': 70, 'y1': 140},
            'borc': {'x0': 330, 'x1': 430, 'y0': 70, 'y1': 140},
            'faiz': {'x0': 440, 'x1': 500, 'y0': 70, 'y1': 140},
            'derece_sira': {'x0': 510, 'x1': 560, 'y0': 70, 'y1': 140},
            'sure': {'x0': 560, 'x1': 600, 'y0': 70, 'y1': 140},
            'tesis_tarih': {'x0': 610, 'x1': 800, 'y0': 60, 'y1': 160}
        }
    
        self.hisse_alanlari = {
            'tasinmaz': {'x0': 40, 'x1': 240, 'y0': 200, 'y1': 290},
            'hisse_pay_payda': {'x0': 240, 'x1': 320, 'y0': 200, 'y1': 260},
            'borclu_malik': {'x0': 320, 'x1': 530, 'y0': 200, 'y1': 260},
            'malik_borc': {'x0': 530, 'x1': 610, 'y0': 200, 'y1': 260},
            'tescil_tarih': {'x0': 610, 'x1': 720, 'y0': 200, 'y1': 280},
            'terkin': {'x0': 720, 'x1': 800, 'y0': 200, 'y1': 260}
        }

    def load_banks(self):
        """JSON dosyasından banka bilgilerini yükler, hata durumunda varsayılan listeyi kullanır"""
        try:
            if os.path.exists(self.banks_json_path):
                with open(self.banks_json_path, 'r', encoding='utf-8') as file:
                    loaded_banks = json.load(file)
                    # Yüklenen verinin geçerli olup olmadığını kontrol et
                    if isinstance(loaded_banks, dict) and loaded_banks:
                        return loaded_banks
                    else:
                        raise ValueError("Geçersiz banka verisi formatı")
            else:
                # Dosya yoksa varsayılan listeyi kullan ve kaydet
                self.save_banks(self.default_banks)
                return self.default_banks

        except Exception as e:
            logging.error(f"Banka bilgileri yüklenirken hata: {str(e)}")
            logging.info("Varsayılan banka listesi kullanılıyor ve kaydediliyor")
            # Hata durumunda varsayılan listeyi kullan ve kaydet
            self.save_banks(self.default_banks)
            return self.default_banks

    def extract_bank_name(self, text):
        """Metinden banka adını çıkar ve temizle"""
        try:
            # VKN ve başlıkları temizle
            cleaned_text = re.sub(r'VKN\s*:\s*\d+\s*', '', text).strip()
        
            # SN bilgisini temizle
            cleaned_text = re.sub(r'\(SN:\d+\)\s*', '', cleaned_text).strip()
        
            # "İpoteğin Konulduğu" ile başlayan kısmı temizle
            cleaned_text = re.sub(r'İpoteğin Konulduğu.*$', '', cleaned_text, flags=re.IGNORECASE).strip()
        
            # Başlıkları temizle
            basliklar = ['Alacaklı', 'Müşterek', 'Mi?', 'Borç', 'Faiz', 
                         'Derece', 'Sıra', 'Süre', 'Tesis Tarih - Yev']
            for baslik in basliklar:
                cleaned_text = cleaned_text.replace(baslik, '').strip()
        
            # Kelimeleri ayır ve filigranları temizle
            words = cleaned_text.split()
            cleaned_words = [word for word in words if not self.is_filigran_harf(word)]
        
            # Her kelimenin ilk harfini büyük yap
            cleaned_words = [word.capitalize() if not word.endswith('.') else word.upper() 
                            for word in cleaned_words]
        
            cleaned_text = ' '.join(cleaned_words).strip()
        
            # A.Ş. formatını düzelt
            cleaned_text = cleaned_text.replace('A.ş.', 'A.Ş.')
            cleaned_text = cleaned_text.replace('A.s.', 'A.Ş.')
            cleaned_text = cleaned_text.replace('A.Ş', 'A.Ş.')
        
            # T.A.O. formatını düzelt
            cleaned_text = cleaned_text.replace('T.a.o.', 'T.A.O.')
            cleaned_text = cleaned_text.replace('T.A.O', 'T.A.O.')
        
            # Ltd.Şti. formatını düzelt
            cleaned_text = cleaned_text.replace('Ltd.şti.', 'Ltd.Şti.')
            cleaned_text = cleaned_text.replace('Ltd.Şti', 'Ltd.Şti.')

            # Noktalama işaretlerini düzelt
            cleaned_text = cleaned_text.replace('..', '.').strip()

            # Eğer '.' ile bitiyorsa ve bu A.Ş. veya T.A.O. veya Ltd.Şti. parçası değilse sondaki noktayı kaldır
            if cleaned_text.endswith('.') and not cleaned_text.endswith(('A.Ş.', 'T.A.O.', 'Ltd.Şti.')):
                cleaned_text = cleaned_text[:-1]
        
            return cleaned_text
        except Exception as e:
            logging.error(f"Banka adı çıkarma hatası: {str(e)}")
            return ""

    def clean_general_text(self, text):
        """Genel metin temizleme işlemleri"""
        try:
            # Başlıkları temizle
            basliklar = ['Alacaklı', 'Müşterek', 'Mi?', 'Borç', 'Faiz', 
                         'Derece', 'Sıra', 'Süre', 'Tesis Tarih - Yev']
            for baslik in basliklar:
                text = text.replace(baslik, '').strip()
        
            # Filigran temizliği
            words = text.split()
            cleaned_words = [word for word in words if not self.is_filigran_harf(word)]
            text = ' '.join(cleaned_words)
        
            # Fazla boşlukları temizle
            text = ' '.join(text.split())
        
            # Kısaltmaları düzelt
            for k, v in self.format_fixes.items():
                text = text.replace(k, v)
            
            return text
        except Exception as e:
            logging.error(f"Genel metin temizleme hatası: {str(e)}")
            return text

    def find_similar_bank(self, normalized_text, similarity_threshold=0.95):
        """Benzer banka ismi ara"""
        try:
            best_match = None
            best_ratio = 0
        
            for bank_name in self.bank_names:
                ratio = self.similar(normalized_text, bank_name)
                if ratio > similarity_threshold and ratio > best_ratio:
                    best_ratio = ratio
                    best_match = self.bank_names[bank_name]
        
            return best_match
        except Exception as e:
            logging.error(f"Banka benzerlik kontrolü hatası: {str(e)}")
            return None

    def add_new_bank(self, vkn, bank_name):
        """Yeni banka bilgisini ekle"""
        try:
            if not vkn or not bank_name:
                return False
            
            if vkn not in self.banks:
                # Banks sözlüğüne ekle
                self.banks[vkn] = bank_name
            
                # Bank_names sözlüğünü güncelle
                normalized_name = self.normalize_text(bank_name)
                self.bank_names[normalized_name] = bank_name
            
                # JSON dosyasına kaydet
                if self.save_banks(self.banks):
                    logging.info(f"Yeni banka başarıyla eklendi: {vkn} - {bank_name}")
                    return True
                else:
                    logging.error("Banka JSON kaydetme hatası")
                    return False
            return False
        except Exception as e:
            logging.error(f"Yeni banka ekleme hatası: {str(e)}")
            return False

    def save_banks(self, banks_data):
        """Banka bilgilerini JSON dosyasına kaydet"""
        try:
            with open(self.banks_json_path, 'w', encoding='utf-8') as file:
                json.dump(banks_data, file, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"Banka bilgileri kaydetme hatası: {str(e)}")
            return False

    def create_takbis_tarih_table(self):
        """Takbis tarih tablosunu oluşturur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS takbis_tarih (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tapu_tarih TEXT,
            tasinmaz_kimlik TEXT,
            kayit_tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    def save_takbis_tarih(self, tapu_tarih, tasinmaz_kimlik):
        """Tapu tarih ve taşınmaz kimlik bilgilerini kaydeder"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Önce tablonun var olduğundan emin olalım
            self.create_takbis_tarih_table()
            
            # Aynı taşınmaz kimlik için kayıt var mı kontrol et
            cursor.execute('''
                SELECT COUNT(*) FROM takbis_tarih 
                WHERE tasinmaz_kimlik = ?
            ''', (tasinmaz_kimlik,))
            
            exists = cursor.fetchone()[0] > 0
            
            if exists:
                # Güncelle
                cursor.execute('''
                    UPDATE takbis_tarih 
                    SET tapu_tarih = ?, kayit_tarih = CURRENT_TIMESTAMP
                    WHERE tasinmaz_kimlik = ?
                ''', (tapu_tarih, tasinmaz_kimlik))
                logging.info(f"Takbis tarih kaydı güncellendi: {tasinmaz_kimlik}")
            else:
                # Yeni kayıt ekle
                cursor.execute('''
                    INSERT INTO takbis_tarih (tapu_tarih, tasinmaz_kimlik)
                    VALUES (?, ?)
                ''', (tapu_tarih, tasinmaz_kimlik))
                logging.info(f"Yeni takbis tarih kaydı eklendi: {tasinmaz_kimlik}")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Takbis tarih kaydetme hatası: {str(e)}")
            return False

    def create_database(self):
        """Veritabanı ve ipotek_verileri tablosunu oluşturur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ipotek_verileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tapu_tarih TEXT,
            tasinmaz_kimlik TEXT,
            sayfa_no INTEGER,
            alacakli TEXT,
            musterek_mi TEXT,
            borc TEXT,
            faiz TEXT,
            derece_sira TEXT,
            sure TEXT,
            tesis_tarih TEXT,
            tasinmaz TEXT,
            hisse_pay_payda TEXT,
            borclu_malik TEXT,
            sn_bilgisi TEXT,
            malik_borc TEXT,
            tescil_tarih TEXT,
            terkin TEXT
        )
        ''')
        
        conn.commit()
        return conn

    def check_existing_data(self, tasinmaz_kimlik):
        """Taşınmaza ait ipotek verisinin olup olmadığını kontrol et"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) FROM ipotek_verileri 
                WHERE tasinmaz_kimlik = ?
            ''', (tasinmaz_kimlik,))
            
            count = cursor.fetchone()[0]
            conn.close()
            
            return count > 0
        except Exception as e:
            logging.error(f"Veri kontrol hatası: {str(e)}")
            return False

    def delete_existing_data(self, tasinmaz_kimlik):
        """Var olan ipotek verilerini sil"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                DELETE FROM ipotek_verileri 
                WHERE tasinmaz_kimlik = ?
            ''', (tasinmaz_kimlik,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Veri silme hatası: {str(e)}")
            return False

    def save_to_database(self, results):
        """Sonuçları veritabanına kaydeder"""
        try:
            conn = self.create_database()
            cursor = conn.cursor()
        
            tapu_tarih = results['tapu_bilgileri']['tarih']
            tasinmaz_kimlik = results['tapu_bilgileri']['tasinmaz_kimlik']
        
            for ipotek_bilgi in results['ipotek_bilgileri']:
                ipotek = ipotek_bilgi.get('ipotek', {})  # get metodu ile None durumunu engelle
                hisse = ipotek_bilgi.get('hisse', {})
                sayfa_no = ipotek_bilgi.get('sayfa_no')
            
                # Tüm alanları kontrol et ve None ise boş string ata
                cursor.execute('''
                INSERT INTO ipotek_verileri (
                    tapu_tarih,
                    tasinmaz_kimlik,
                    sayfa_no,
                    alacakli,
                    musterek_mi,
                    borc,
                    faiz,
                    derece_sira,
                    sure,
                    tesis_tarih,
                    tasinmaz,
                    hisse_pay_payda,
                    borclu_malik,
                    sn_bilgisi,
                    malik_borc,
                    tescil_tarih,
                    terkin
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tapu_tarih or '',
                    tasinmaz_kimlik or '',
                    sayfa_no or 0,
                    ipotek.get('alacakli', ''),
                    ipotek.get('musterek_mi', ''),
                    ipotek.get('borc', ''),
                    ipotek.get('faiz', ''),
                    ipotek.get('derece_sira', ''),
                    ipotek.get('sure', ''),
                    ipotek.get('tesis_tarih', ''),
                    hisse.get('tasinmaz', ''),
                    hisse.get('hisse_pay_payda', ''),
                    hisse.get('borclu_malik', ''),
                    hisse.get('sn_bilgisi', ''),
                    hisse.get('malik_borc', ''),
                    hisse.get('tescil_tarih', ''),
                    hisse.get('terkin', '')
                ))
        
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"Veritabanına kaydetme hatası: {str(e)}")
            return False

    def is_filigran_harf(self, text):
        """Metnin filigran harfi olup olmadığını kontrol et"""
        text = text.strip().upper()
        filigran_kelime = "BİLGİ AMAÇLIDIR"
        return (len(text) == 1 and (
            text in set(filigran_kelime) or
            text in self.filigran_karakterler
        ))

    def normalize_text(self, text):
        """Metni normalize eder (büyük harfe çevirir ve özel karakterleri temizler)"""
        if not text:
            return ""
        text = text.upper()
        text = text.replace('İ', 'I').replace('Ü', 'U').replace('Ö', 'O').replace('Ş', 'S').replace('Ç', 'C').replace('Ğ', 'G')
        return text

    def similar(self, a, b):
        """İki metin arasındaki benzerlik oranını hesaplar"""
        return SequenceMatcher(None, self.normalize_text(a), self.normalize_text(b)).ratio()

    def clean_text(self, text, preserve_sn=False):
        """
        Metni temizle ve düzenle. 
        VKN bilgisi varsa bankayı tanımlar ve yeni banka ise kaydeder.
        """
        if not text:
            return ""

        try:
            # VKN kontrolü
            vkn_match = re.search(r'VKN\s*:\s*(\d+)', text)
            if vkn_match:
                vkn = vkn_match.group(1)
                # Mevcut banka kontrolü
                if vkn in self.banks:
                    return self.banks[vkn]
                else:
                    # Metinden banka adını çıkar
                    cleaned_text = self.extract_bank_name(text)
                    if cleaned_text:
                        # Yeni banka bilgisini kaydet
                        success = self.add_new_bank(vkn, cleaned_text)
                        if success:
                            logging.info(f"Yeni banka bilgisi eklendi - VKN: {vkn}, İsim: {cleaned_text}")
                            return cleaned_text

            # VKN yoksa normal metin temizleme
            cleaned_text = self.clean_general_text(text)
        
            # Banka ismi benzerlik kontrolü
            normalized_text = self.normalize_text(cleaned_text)
            best_match = self.find_similar_bank(normalized_text)
            if best_match:
                return best_match

            return cleaned_text.strip()

        except Exception as e:
            logging.error(f"Metin temizleme hatası: {str(e)}")
            return text

    def extract_tapu_info(self, page):
        """İlk sayfadan sadece tarih ve taşınmaz kimlik no'yu çıkar"""
        try:
            page_width = page.width
            page_height = page.height

            tarih_alani = {'x0': page_width * 0.7, 'x1': page_width, 'y0': 0, 'y1': page_height * 0.1}
            tarih_text = self.extract_data_from_area(page, tarih_alani)
            tarih_match = re.search(r'Tarih:\s*(\d{1,2}-\d{1,2}-\d{4}-\d{1,2}:\d{2})', tarih_text)
            tarih = tarih_match.group(1) if tarih_match else ""

            kimlik_alani = {'x0': 0, 'x1': page_width * 0.5, 'y0': 0, 'y1': page_height * 0.4}
            kimlik_text = self.extract_data_from_area(page, kimlik_alani)
            kimlik_match = re.search(r'Taşınmaz Kimlik No:\s*(\d+)', kimlik_text, re.IGNORECASE)
            tasinmaz_kimlik = kimlik_match.group(1) if kimlik_match else ""

            return {
                'tarih': tarih,
                'tasinmaz_kimlik': tasinmaz_kimlik
            }

        except Exception as e:
            logging.error(f"Tarih ve Taşınmaz Kimlik No çıkarma hatası: {str(e)}")
            return None

    def find_hisse_bilgisi_position(self, page):
        """Sayfada 'İpoteğin Konulduğu Hisse Bilgisi' başlığının konumunu bulur ve koordinatları ayarlar"""
        try:
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=True,
                use_text_flow=False
            )
        
            aranan_baslik = "İpoteğin Konulduğu Hisse Bilgisi"
        
            # Başlığı bul
            for word in words:
                if self.normalize_text(word['text']) == self.normalize_text(aranan_baslik):
                    baseline_y = word['top']
                
                    # Sadece y koordinatlarını güncelleyerek x koordinatlarını aynı tutuyoruz
                    return {
                        'tasinmaz': {
                            'x0': 40, 'x1': 240,
                            'y0': baseline_y + 20,
                            'y1': baseline_y + 110
                        },
                        'hisse_pay_payda': {
                            'x0': 240, 'x1': 320,
                            'y0': baseline_y + 20,
                            'y1': baseline_y + 90
                        },
                        'borclu_malik': {
                            'x0': 320, 'x1': 530,
                            'y0': baseline_y + 20,
                            'y1': baseline_y + 110
                        },
                        'malik_borc': {
                            'x0': 530, 'x1': 610,
                            'y0': baseline_y + 20,
                            'y1': baseline_y + 100
                        },
                        'tescil_tarih': {
                            'x0': 610, 'x1': 720,
                            'y0': baseline_y + 20,
                            'y1': baseline_y + 110
                        },
                        'terkin': {
                            'x0': 720, 'x1': 800,
                            'y0': baseline_y + 20,
                            'y1': baseline_y + 90
                        }
                    }
        
            logging.warning("Hisse bilgisi başlığı bulunamadı, varsayılan koordinatlar kullanılıyor.")
            return self.hisse_alanlari
        
        except Exception as e:
            logging.error(f"Hisse bilgisi pozisyon belirleme hatası: {str(e)}")
            return self.hisse_alanlari

    def extract_data_from_area(self, page, area):
        """Belirli bir alandaki kelimeleri çıkar"""
        try:
            area_words = []
            words = page.extract_words(
                x_tolerance=3,
                y_tolerance=3,
                keep_blank_chars=True,
                use_text_flow=False
            )

            for word in words:
                if (area['x0'] <= word['x0'] <= area['x1'] and 
                    area['y0'] <= word['top'] <= area['y1']):
                    area_words.append(word['text'])

            text = ' '.join(area_words)
            return self.clean_text(text)

        except Exception as e:
            logging.error(f"Veri çıkarma hatası: {str(e)}")
            return ""

    def process_page(self, page):
       """
       Sayfadaki tüm verileri işler. Önce standart koordinatlarla dener,
       veri eksik veya hatalıysa dinamik koordinatlara geçer.
       """
       try:
           # 1. STANDART KOORDİNATLARLA DENEME
           ipotek_data = {}
           hisse_data = {}
       
           # Standart koordinatlarla veri çıkarma
           for alan_adi, koordinatlar in self.ipotek_alanlari.items():
               text = self.extract_data_from_area(page, koordinatlar)
               ipotek_data[alan_adi] = self.clean_text(text)

           # Standart hisse verilerini çıkar    
           for alan_adi, koordinatlar in self.hisse_alanlari.items():
               text = self.extract_data_from_area(page, koordinatlar)
               if alan_adi == 'borclu_malik':
                   temizlenmis_text = self.clean_text(text, preserve_sn=True)
                   sn_match = re.search(r'\(SN:(\d+)\)', temizlenmis_text)
                   sn_bilgisi = sn_match.group(1) if sn_match else None
                   hisse_data[alan_adi] = re.sub(r'\(SN:\d+\)\s*', '', temizlenmis_text).strip()
                   hisse_data['sn_bilgisi'] = sn_bilgisi
               else:
                   hisse_data[alan_adi] = self.clean_text(text)

           # VERİ KALİTE KONTROLÜ
           veri_eksik = False
       
           # Alacaklı verisi için özel kontrol
           alacakli_text = ipotek_data.get('alacakli', '')
           if alacakli_text:
               # Alacaklı metninde VKN kontrolü
               if 'VKN:' in alacakli_text:
                   vkn_count = len(re.findall(r'VKN:', alacakli_text))
                   expected_vkn_count = len(re.findall(r'\(SN:\d+\)', alacakli_text))
                   if vkn_count != expected_vkn_count:
                       veri_eksik = True
               # SN sayısı kontrolü
               sn_count = len(re.findall(r'\(SN:\d+\)', alacakli_text))
               if sn_count > 0 and len(alacakli_text.split()) < sn_count * 3:  # Her SN için en az 3 kelime bekle
                   veri_eksik = True
           else:
               veri_eksik = True

           # Diğer önemli alanların kontrolü
           for alan in ['musterek_mi', 'borc', 'tesis_tarih']:
               if not ipotek_data.get(alan):
                   veri_eksik = True
                   break

           # 2. VERİ EKSİK VEYA BULUNAMADIYSA DİNAMİK KOORDİNATLARA GEÇ
           if veri_eksik:
               logging.info("Standart koordinatlarla veri eksik veya hatalı, dinamik koordinatlara geçiliyor...")
           
               # Sayfadaki metinleri çıkar
               words = page.extract_words(
                   x_tolerance=3,
                   y_tolerance=3,
                   keep_blank_chars=True,
                   use_text_flow=False
               )
           
               # Başlıkların konumlarını bul
               alacakli_coords = None
               hisse_bilgisi_coords = None
           
               for word in words:
                   if word['text'] == "Alacaklı":
                       alacakli_coords = word
                   elif word['text'] == "İpoteğin Konulduğu Hisse Bilgisi":
                       hisse_bilgisi_coords = word
                       break

               if alacakli_coords and hisse_bilgisi_coords:
                   # Bölümler arası mesafeyi hesapla
                   vertical_gap = hisse_bilgisi_coords['top'] - alacakli_coords['top']
               
                   # Dinamik ipotek alanları koordinatları
                   dynamic_ipotek_alanlari = {
                       'alacakli': {
                           'x0': 40, 
                           'x1': 250,
                           'y0': alacakli_coords['top'] - 5,
                           'y1': hisse_bilgisi_coords['top']  
                       },
                       'musterek_mi': {
                           'x0': 260,
                           'x1': 320,
                           'y0': alacakli_coords['top'],
                           'y1': alacakli_coords['top'] + vertical_gap * 0.3
                       },
                       'borc': {
                           'x0': 330,
                           'x1': 430,
                           'y0': alacakli_coords['top'],
                           'y1': alacakli_coords['top'] + vertical_gap * 0.3
                       },
                       'faiz': {
                           'x0': 440,
                           'x1': 500,
                           'y0': alacakli_coords['top'],
                           'y1': alacakli_coords['top'] + vertical_gap * 0.3
                       },
                       'derece_sira': {
                           'x0': 510,
                           'x1': 560,
                           'y0': alacakli_coords['top'],
                           'y1': alacakli_coords['top'] + vertical_gap * 0.3
                       },
                       'sure': {
                           'x0': 560,
                           'x1': 600,
                           'y0': alacakli_coords['top'],
                           'y1': alacakli_coords['top'] + vertical_gap * 0.3
                       },
                       'tesis_tarih': {
                           'x0': 610,
                           'x1': 800,
                           'y0': alacakli_coords['top'],
                           'y1': alacakli_coords['top'] + vertical_gap * 0.3
                       }
                   }

                   # Dinamik hisse alanları koordinatları
                   dynamic_hisse_alanlari = {
                       'tasinmaz': {
                           'x0': 40,
                           'x1': 240,
                           'y0': hisse_bilgisi_coords['top'] + 20,
                           'y1': hisse_bilgisi_coords['top'] + vertical_gap * 0.4
                       },
                       'hisse_pay_payda': {
                           'x0': 240,
                           'x1': 320,
                           'y0': hisse_bilgisi_coords['top'] + 20,
                           'y1': hisse_bilgisi_coords['top'] + vertical_gap * 0.4
                       },
                       'borclu_malik': {
                           'x0': 320,
                           'x1': 530,
                           'y0': hisse_bilgisi_coords['top'] + 20,
                           'y1': hisse_bilgisi_coords['top'] + vertical_gap * 0.4
                       },
                       'malik_borc': {
                           'x0': 530,
                           'x1': 610,
                           'y0': hisse_bilgisi_coords['top'] + 20,
                           'y1': hisse_bilgisi_coords['top'] + vertical_gap * 0.4
                       },
                       'tescil_tarih': {
                           'x0': 610,
                           'x1': 720,
                           'y0': hisse_bilgisi_coords['top'] + 20,
                           'y1': hisse_bilgisi_coords['top'] + vertical_gap * 0.4
                       },
                       'terkin': {
                           'x0': 720,
                           'x1': 800,
                           'y0': hisse_bilgisi_coords['top'] + 20,
                           'y1': hisse_bilgisi_coords['top'] + vertical_gap * 0.4
                       }
                   }

                   # Dinamik koordinatlarla ipotek verilerini çıkar
                   ipotek_data = {}
                   for alan_adi, koordinatlar in dynamic_ipotek_alanlari.items():
                       text = self.extract_data_from_area(page, koordinatlar)
                       ipotek_data[alan_adi] = self.clean_text(text)

                   # Dinamik koordinatlarla hisse verilerini çıkar
                   hisse_data = {}
                   for alan_adi, koordinatlar in dynamic_hisse_alanlari.items():
                       text = self.extract_data_from_area(page, koordinatlar)
                       if alan_adi == 'borclu_malik':
                           temizlenmis_text = self.clean_text(text, preserve_sn=True)
                           sn_match = re.search(r'\(SN:(\d+)\)', temizlenmis_text)
                           sn_bilgisi = sn_match.group(1) if sn_match else None
                           hisse_data[alan_adi] = re.sub(r'\(SN:\d+\)\s*', '', temizlenmis_text).strip()
                           hisse_data['sn_bilgisi'] = sn_bilgisi
                       else:
                           hisse_data[alan_adi] = self.clean_text(text)

           return {'ipotek': ipotek_data, 'hisse': hisse_data}

       except Exception as e:
           logging.error(f"Sayfa işleme hatası: {str(e)}")
           return {'ipotek': {}, 'hisse': {}}

    def is_ipotek_page(self, page):
        """Sayfanın ipotek veya rehin sayfası olup olmadığını kontrol eder."""
        try:
            text = page.extract_text()
        
            # Belge boşsa veya çok az içerik varsa
            if not text or len(text.strip()) < 50:
                return False
        
            # İpotek göstergeleri - genel terimler
            genel_ipotek_terimleri = [
                "potek",  # İpotek veya Ipotek
                "Rehin",
                "MÜLKİYETE AİT REHİN BİLGİLERİ",
                "İpoteğin Konulduğu"
            ]
        
            # Önemli tablo başlıkları
            tablo_basliklari = [
                "Alacaklı", 
                "Borç", 
                "Faiz", 
                "Derece",
                "Tesis Tarih"
            ]
        
            # VKN formatı kontrolü
            vkn_kontrol = re.search(r'VKN\s*:\s*\d+', text)
        
            # Banka/finans kurumu belirteçleri
            finans_belirtecleri = [
                "A.Ş.",
                "T.A.O.",
                "Ltd.Şti.",
                "Bankası",
                "Bank"
            ]
        
            # 1. Genel ipotek terimlerinden en az biri var mı?
            ipotek_terim_eslesme = any(terim in text for terim in genel_ipotek_terimleri)
        
            # 2. Tablodaki önemli başlıklardan en az ikisi var mı?
            baslik_sayisi = sum(1 for baslik in tablo_basliklari if baslik in text)
        
            # 3. VKN formatı var mı VEYA finansal kurum belirteci var mı?
            finans_kurumu_var = vkn_kontrol or any(belirtec in text for belirtec in finans_belirtecleri)
        
            # İpotek sayfası için gerekli kriterleri kombinle:
            # - Ya ipotek/rehin terimi VE en az bir tablo başlığı
            # - Ya da en az iki tablo başlığı VE finansal kurum belirteci
            return (ipotek_terim_eslesme and baslik_sayisi >= 1) or (baslik_sayisi >= 2 and finans_kurumu_var)
        
        except Exception as e:
            logging.error(f"İpotek sayfası kontrol hatası: {str(e)}")
            return False

    def extract_from_pdf(self, pdf_path, force_update=False):
        """
        PDF'den tüm verileri çıkar ve veritabanına kaydet
        
        Args:
            pdf_path (str): PDF dosyasının yolu
            force_update (bool): True ise mevcut verileri güncelle
            
        Returns:
            dict: Çıkarılan veriler veya None (hata durumunda)
        """
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # İlk sayfadan tapu bilgilerini al
                first_page = pdf.pages[0]
                tapu_bilgileri = self.extract_tapu_info(first_page)
                
                if not tapu_bilgileri:
                    logging.error("Tapu bilgileri çıkarılamadı")
                    return None
                               
                # Yeni eklenen kısım: Takbis tarih bilgilerini kaydet
                self.save_takbis_tarih(tapu_bilgileri['tarih'], tapu_bilgileri['tasinmaz_kimlik'])
               
                # Mevcut veri kontrolü
                if self.check_existing_data(tapu_bilgileri['tasinmaz_kimlik']):
                    if not force_update:
                        logging.info(f"Taşınmaz {tapu_bilgileri['tasinmaz_kimlik']} için mevcut ipotek verisi bulundu")
                        return None
                    else:
                        # Mevcut verileri sil
                        self.delete_existing_data(tapu_bilgileri['tasinmaz_kimlik'])
                
                ipotek_bilgileri = []
                for page_num, page in enumerate(pdf.pages, 1):
                    if self.is_ipotek_page(page):
                        logging.info(f"Sayfa {page_num}'de ipotek bilgisi bulundu")
                        page_data = self.process_page(page)
                        if any(page_data['ipotek'].values()):
                            page_data['sayfa_no'] = page_num
                            ipotek_bilgileri.append(page_data)
                    else:
                        logging.info(f"Sayfa {page_num} - ipotek sayfası olarak değerlendirilmedi.")

                final_data = {
                    'tapu_bilgileri': tapu_bilgileri,
                    'ipotek_bilgileri': ipotek_bilgileri
                }
                
                # Verileri veritabanına kaydet
                if self.save_to_database(final_data):
                    logging.info("Veriler başarıyla veritabanına kaydedildi.")
                else:
                    logging.error("Verileri veritabanına kaydederken hata oluştu.")
                
                return final_data

        except Exception as e:
            logging.error(f"PDF işleme hatası: {str(e)}")
            return None

    def find_table_coordinates(self, page):
        """Sayfadaki tablo yapısının koordinatlarını tespit eder"""
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=True,
            use_text_flow=False
        )
    
        # Sayfa boyutları
        page_width = page.width
        page_height = page.height
    
        # Anahtar başlıkları ara
        anahtar_basliklar = ["Alacaklı", "İpotek", "Ipotek", "Borç", "Faiz"]
        baslik_y_pozisyonlari = []
    
        for word in words:
            if word['text'] in anahtar_basliklar:
                baslik_y_pozisyonlari.append(word['top'])
    
        # Başlık pozisyonunu belirle
        if baslik_y_pozisyonlari:
            # En sık görülen y pozisyonu (tablo başlıkları genelde aynı y'de)
            from collections import Counter
            y_counter = Counter([int(y) for y in baslik_y_pozisyonlari])
            most_common_y = y_counter.most_common(1)[0][0]
            base_y = most_common_y
        else:
            # Başlık bulunamazsa sayfa üst kısmında ara
            base_y = page_height * 0.2
    
        # Genişliğe göre oransal koordinatlar belirle
        return {
            'alacakli': {'x0': page_width * 0.05, 'x1': page_width * 0.35, 'y0': base_y, 'y1': base_y + page_height * 0.25},
            'musterek_mi': {'x0': page_width * 0.35, 'x1': page_width * 0.45, 'y0': base_y, 'y1': base_y + page_height * 0.15},
            'borc': {'x0': page_width * 0.45, 'x1': page_width * 0.55, 'y0': base_y, 'y1': base_y + page_height * 0.15},
            'faiz': {'x0': page_width * 0.55, 'x1': page_width * 0.65, 'y0': base_y, 'y1': base_y + page_height * 0.15},
            'derece_sira': {'x0': page_width * 0.65, 'x1': page_width * 0.75, 'y0': base_y, 'y1': base_y + page_height * 0.15},
            'sure': {'x0': page_width * 0.75, 'x1': page_width * 0.82, 'y0': base_y, 'y1': base_y + page_height * 0.15},
            'tesis_tarih': {'x0': page_width * 0.82, 'x1': page_width * 0.95, 'y0': base_y, 'y1': base_y + page_height * 0.15}
        }

    def extract_bank_from_vkn(self, page_text):
        """VKN bilgisinden banka adını tespit eder"""
        vkn_match = re.search(r'VKN\s*:\s*(\d+)', page_text)
        if vkn_match:
            vkn = vkn_match.group(1)
            if vkn in self.banks:
                return self.banks[vkn]
        return None

    def find_coordinates(self, page):
        """Sayfadaki belirli metinlerin koordinatlarını yazdırır"""
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=True,
            use_text_flow=False
        )
    
        # Aradığımız başlıklar
        target_headers = ["Alacaklı", "Müşterek", "İpoteğin Konulduğu Hisse Bilgisi"]
    
        for word in words:
            if word['text'] in target_headers:
                print(f"Metin: {word['text']}")
                print(f"x0: {word['x0']}, x1: {word['x1']}")
                print(f"top: {word['top']}, bottom: {word['bottom']}")
                print("---")

    def calculate_dynamic_coordinates(self, page):
        """Dinamik koordinat hesaplama"""
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=True,
            use_text_flow=False
        )
    
        alacakli_y = None
        hisse_y = None
    
        # Başlıkların koordinatlarını bul
        for word in words:
            if word['text'] == "Alacaklı":
                alacakli_y = word['top']
                print(f"Alacaklı Y pozisyonu: {alacakli_y}")
            elif word['text'] == "İpoteğin Konulduğu Hisse Bilgisi":
                hisse_y = word['top']
                print(f"Hisse Bilgisi Y pozisyonu: {hisse_y}")
    
        if alacakli_y and hisse_y:
            vertical_gap = hisse_y - alacakli_y
            print(f"Dikey mesafe: {vertical_gap}")
        
            # İpotek alanlarını güncelle
            self.ipotek_alanlari.update({
                'alacakli': {'x0': 40, 'x1': 250, 'y0': alacakli_y, 'y1': alacakli_y + 90},
                'musterek_mi': {'x0': 260, 'x1': 320, 'y0': alacakli_y, 'y1': alacakli_y + 70},
                'borc': {'x0': 330, 'x1': 430, 'y0': alacakli_y, 'y1': alacakli_y + 70},
                'faiz': {'x0': 440, 'x1': 500, 'y0': alacakli_y, 'y1': alacakli_y + 70},
                'derece_sira': {'x0': 510, 'x1': 560, 'y0': alacakli_y, 'y1': alacakli_y + 70},
                'sure': {'x0': 560, 'x1': 600, 'y0': alacakli_y, 'y1': alacakli_y + 70},
                'tesis_tarih': {'x0': 610, 'x1': 800, 'y0': alacakli_y, 'y1': alacakli_y + 90}
            })

            # Hisse alanlarını güncelle
            self.hisse_alanlari.update({
                'tasinmaz': {'x0': 40, 'x1': 240, 'y0': hisse_y + 20, 'y1': hisse_y + 110},
                'hisse_pay_payda': {'x0': 240, 'x1': 320, 'y0': hisse_y + 20, 'y1': hisse_y + 90},
                'borclu_malik': {'x0': 320, 'x1': 530, 'y0': hisse_y + 20, 'y1': hisse_y + 110},
                'malik_borc': {'x0': 530, 'x1': 610, 'y0': hisse_y + 20, 'y1': hisse_y + 100},
                'tescil_tarih': {'x0': 610, 'x1': 720, 'y0': hisse_y + 20, 'y1': hisse_y + 110},
                'terkin': {'x0': 720, 'x1': 800, 'y0': hisse_y + 20, 'y1': hisse_y + 90}
            })

    def analyze_page_structure(self, page):
        """Sayfadaki tüm metinleri ve konumlarını analiz eder"""
        print("\nSayfa Yapısı Analizi:")
        print("-" * 50)
    
        words = page.extract_words(
            x_tolerance=3,
            y_tolerance=3,
            keep_blank_chars=True,
            use_text_flow=False
        )
    
        # Önemli başlıkları ve metinleri grupla
        current_section = None
        for word in words:
            # Başlık kontrolü
            if word['text'] in ["Alacaklı", "Müşterek", "İpoteğin Konulduğu Hisse Bilgisi"]:
                current_section = word['text']
                print(f"\n{current_section} Bölümü:")
                print(f"Başlık Konumu: x0={word['x0']:.2f}, x1={word['x1']:.2f}, y0={word['top']:.2f}, y1={word['bottom']:.2f}")
            else:
                # Metin içeriği
                print(f"İçerik: {word['text']}")
                print(f"Konum: x0={word['x0']:.2f}, x1={word['x1']:.2f}, y0={word['top']:.2f}, y1={word['bottom']:.2f}")

    def find_content_area(self, page, start_y, section_width=250):
        """Belirli bir y koordinatından başlayarak içeriği bulur"""
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        content_words = []
    
        for word in words:
            # Başlangıç y koordinatından sonraki ve x ekseni uygun olan kelimeleri al
            if (word['top'] > start_y and 
                word['top'] < start_y + section_width and 
                word['x0'] < 250):  # Alacaklı bölümü için x sınırı
                content_words.append(word['text'])
    
        return ' '.join(content_words)