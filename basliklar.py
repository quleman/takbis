import fitz  # PyMuPDF kütüphanesi
import re
import json
from typing import Dict, Any
import logging
import sqlite3

class FitzTapuAnalyzer:
    def __init__(self, db_path=None, tasinmaz_kimlik=None):
        # Veritabanı yolunu parametre olarak al
        self.db_path = db_path or 'veritabani.db'
        self.tasinmaz_kimlik = tasinmaz_kimlik
        
        # Başlık tablosunu oluştur
        self.create_baslik_table()
        
        # Tapu belgesinde arayacağımız başlıklar
        self.header_order = [
            "TAPU KAYIT BİLGİSİ",
            "TEFERRUAT BİLGİLERİ",
            "MUHDESAT BİLGİLERİ",
            "MÜLKİYET BİLGİLERİ",
            "MÜLKİYETE AİT ŞERH BEYAN İRTİFAK BİLGİLERİ",
            "MÜLKİYETE AİT REHİN BİLGİLERİ",
            "EKLENTİ BİLGİLERİ",
            "TAŞINMAZA AİT ŞERH BEYAN İRTİFAK BİLGİLERİ"
        ]
        self.found_headers = {}  # Bulunan başlıkların bilgilerini tutacak
        self.header_characteristics = None  # Başlık karakteristiklerini tutacak

    def create_baslik_table(self):
        """Başlık bilgileri için tablo oluştur"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baslik_bilgileri (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tasinmaz_kimlik TEXT,
                    baslik TEXT,
                    sayfa_no INTEGER,
                    y_koordinat REAL,
                    auto_detected BOOLEAN DEFAULT FALSE,
                    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        
            conn.commit()
        
        except Exception as e:
            logging.error(f"Başlık tablosu oluşturma hatası: {str(e)}")
        finally:
            if conn:
                conn.close()

    def save_header_to_db(self, header, page_num, y_coord, auto_detected=False):
        """Başlık bilgilerini veritabanına kaydet"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
        
            cursor.execute("""
                INSERT INTO baslik_bilgileri 
                (tasinmaz_kimlik, baslik, sayfa_no, y_koordinat, auto_detected)
                VALUES (?, ?, ?, ?, ?)
            """, (self.tasinmaz_kimlik, header, page_num, y_coord, auto_detected))
        
            conn.commit()
            return True
        
        except Exception as e:
            logging.error(f"Başlık kaydetme hatası: {str(e)}")
            return False
        finally:
            if conn:
                conn.close()

    def clean_text(self, text: str) -> str:
        """Metindeki gereksiz karakterleri temizler"""
        text = re.sub(r'BİLGİ AMAÇLIDIR', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s{2,}', ' ', text)  # Çoklu boşlukları temizle
        text = text.replace('- ', '')  # Kesme işaretli kelimeleri birleştir
        return text.strip()

    def detect_header_characteristics(self) -> Dict[str, Any]:
        """Bulunan başlıkların ortak özelliklerini tespit eder"""
        if not self.found_headers:
            return None

        fonts = []
        font_sizes = []
        
        for header_info in self.found_headers.values():
            fonts.append(header_info['font'])
            font_sizes.append(header_info['font_size'])

        # En sık kullanılan özellikleri bul
        common_font = max(set(fonts), key=fonts.count)
        common_font_size = max(set(font_sizes), key=font_sizes.count)
        
        # Font boyutu için tolerans aralığı
        size_tolerance = 1.0

        return {
            'font': common_font,
            'font_size': common_font_size,
            'size_tolerance': size_tolerance
        }

    def is_potential_header(self, text: str, font: str, font_size: float, x_coord: float) -> bool:
        """Verilen metnin başlık olma potansiyelini gelişmiş kurallarla kontrol eder"""
        if not self.header_characteristics:
            return False

        # 1. Font ve boyut kontrolü
        font_match = font == self.header_characteristics['font']
        size_match = abs(font_size - self.header_characteristics['font_size']) <= self.header_characteristics['size_tolerance']
    
        # 2. X koordinat kontrolü (0-50 arası)
        x_coord_check = 0 <= x_coord <= 50
    
        # 3. İstenmeyen desenlerin kontrolü
        excluded_patterns = [
            r"\(SN:\d+\)",  # (SN:173025404)
            r"\d{8}-\d+-\w+",  # 20240117-2274-F06463
            r"^BU BELGE TOPLAM",
            r"^Kaydı Oluşturan",
            r"\bTABLO\b",
            r"\d+\s*\/\s*\d+"  # 12/34 formatı
        ]
    
        pattern_matches = any(re.search(pattern, text, re.IGNORECASE) for pattern in excluded_patterns)
    
        # 4. Büyük harf ve BİLGİLERİ/BİLGİL ile bitiş kontrolü
        text_format_match = text.isupper() and re.search(r'BİLGİ(LERİ)?$', text)
    
        # 5. Uzunluk kontrolü (en az 3 kelime)
        word_count = len(text.split())
        length_check = word_count >= 3  # Tek kelimelik "başlıklar"ı elemek için

        return all([
            font_match,
            size_match,
            x_coord_check,
            text_format_match,
            length_check,
            not pattern_matches
        ])

    def analyze_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """PDF'i analiz eder ve başlıkları bulur"""
        try:
            logging.basicConfig(level=logging.INFO)

            doc = fitz.open(pdf_path)
        
            # Önce bilinen başlıkları bul
            for page_num, page in enumerate(doc, 1):
                blocks = page.get_text("dict")["blocks"]
            
                for block in blocks:
                    if "lines" not in block:
                        continue
                
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if not text:
                                continue
                        
                            clean_text = self.clean_text(text)
                        
                            # Bilinen başlıkları kontrol et
                            for header in self.header_order:
                                if header in clean_text:
                                    y_coord = span["origin"][1]  # Y koordinatını al
                                
                                    # Başlık bilgilerini veritabanına kaydet
                                    if self.tasinmaz_kimlik:
                                        self.save_header_to_db(header, page_num, y_coord)
                                
                                    self.found_headers[header] = {
                                        'page': page_num,
                                        'text': clean_text,
                                        'position': {
                                            'x': span["origin"][0],
                                            'y': y_coord
                                        },
                                        'font': span["font"],
                                        'font_size': span["size"]
                                    }

            # Başlık karakteristiklerini öğren
            self.header_characteristics = self.detect_header_characteristics()

            # Benzer formatta olan yeni başlıkları bul
            if self.header_characteristics:
                for page_num, page in enumerate(doc, 1):
                    blocks = page.get_text("dict")["blocks"]
                
                    for block in blocks:
                        if "lines" not in block:
                            continue
                    
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                if not text:
                                    continue
                            
                                clean_text = self.clean_text(text)
                            
                                # Eğer bu metin zaten bilinen bir başlık değilse ve başlık formatına uyuyorsa
                                if (clean_text not in self.found_headers and                 
                                    self.is_potential_header(clean_text, span["font"], span["size"], span["origin"][0])):
                                
                                    y_coord = span["origin"][1]  # Y koordinatını al
                                
                                    # Otomatik tespit edilen başlığı veritabanına kaydet
                                    if self.tasinmaz_kimlik:
                                        self.save_header_to_db(clean_text, page_num, y_coord)
                                
                                    self.found_headers[clean_text] = {
                                        'page': page_num,
                                        'text': clean_text,
                                        'position': {
                                            'x': span["origin"][0],
                                            'y': y_coord
                                        },
                                        'font': span["font"],
                                        'font_size': span["size"],
                                        'auto_detected': True  # Otomatik tespit edildiğini belirt
                                    }

            logging.info("\nBulunan Başlıklar:")
            for header, info in self.found_headers.items():
                logging.info(f"Başlık: {header}")
                logging.info(f"Sayfa: {info['page']}")
                logging.info(f"Font: {info['font']}")
                logging.info(f"Font Boyutu: {info['font_size']}")
                logging.info(f"Pozisyon: X={info['position']['x']:.1f}, Y={info['position']['y']:.1f}")
                if info.get('auto_detected'):
                    logging.info("(Otomatik Tespit Edildi)")

            result = {
                'status': 'success',
                'headers': self.found_headers,
                'message': f'Toplam {len(self.found_headers)} başlık bulundu'
            }
    
            #print(result)  # Log için bırakılabilir.
            return result  # Bu eklenmeli.
       
        except Exception as e:
            return {
                'status': 'error',
                'headers': {},
                'message': f'Hata oluştu: {str(e)}'
            }
        finally:
            if 'doc' in locals():
                doc.close()
