import sqlite3
from difflib import SequenceMatcher
import logging


class TapuProcessor:
    def __init__(self, db_path):
        self.db_path = db_path
    
    # isheader fonk call    
    def similar(self, a, b):
        return SequenceMatcher(None, str(a).lower(), str(b).lower()).ratio()
    
    # updateheader fonk call
    def is_header(self, row):
        """Satırın başlık olup olmadığını kontrol eder"""
    
        # Tekli ipotek özel kontrolü
        first_cell = str(row.get('hucreno_1', '')).strip().lower()
        ipotek_variants = ['ipotek', 'ıpotek', 'İpotek', 'IPOTEK', 'İPOTEK']
        if first_cell and any(variant.lower() == first_cell for variant in ipotek_variants):
            # Diğer hücrelerin boş olduğunu kontrol et
            other_cells_empty = all(
                not str(row.get(f'hucreno_{i}', '')).strip() 
                for i in range(2, 9)
            )
            if other_cells_empty:
                return True
            
        # Boş satır kontrolü
        if not any(str(value).strip() for value in row.values() if value is not None):
            return False
    

        # Başlık tipleri
        header_types = {
            'kisitlama': {
                'hucreno_1': ['Ş//', 'Ş.'],
                'hucreno_2': ['Açıklama'],
                'hucreno_3': ['Kısıtlı Malik', 'Malik (Hisse)'],
                'hucreno_4': ['Malik/Lehtar'],
                'hucreno_5': ['Tesis Kurum', 'Tarih- Yevmiye'],
                'hucreno_6': ['Terkin Sebebi']
            },
            'kisitlama2': {
                'hucreno_1': ['Ş//', 'Ş.'],
                'hucreno_2': ['Açıklama'],
                'hucreno_3': ['Kısıtlı Malik', 'Malik (Hisse)'],
                'hucreno_4': ['Malik/Lehtar'],
                'hucreno_5': ['Tesis Kurum', 'Tarih- Yevmiye'],
                'hucreno_6': ['Terkin Sebebi', 'Terkin Sebebi- Tarih- Yevmiye'],
            },
            'sistem_bilgi': { 
                'hucreno_1': ['Sistem No'],
                'hucreno_2': ['Tip'],
                'hucreno_3': ['Tanım'],
                'hucreno_4': ['Adet'],
                'hucreno_5': ['Deger'],
                'hucreno_6': ['Tesis Kurum', 'Tarih- Yevmiye']
            },
            'serh_beyan': {
                'hucreno_1': ['Ş//', 'Ş.'],
                'hucreno_2': ['Açıklama'],
                'hucreno_3': ['Malik/Lehtar'],
                'hucreno_4': ['Tesis Kurum'],
                'hucreno_5': ['Terkin']
            },
            'ipotek': {
                'hucreno_1': ['İpotek', 'Ipotek', 'IPOTEK', 'İPOTEK'],
                'hucreno_2': ['Hisse Pay', 'Payda'],
                'hucreno_3': ['Borçlu'],
                'hucreno_4': ['Malik'],
                'hucreno_5': ['Tescil'],
                'hucreno_6': ['Terkin']
            },
            'ipotek_2': {
                'hucreno_1': ['Taşınmaz'],
                'hucreno_2': ['Hisse Pay', 'Pay/Payda'],
                'hucreno_3': ['Borçlu', 'Borçlu Malik'],
                'hucreno_4': ['Malik', 'Borç'],
                'hucreno_5': ['Tescil', 'Tarih - Yev'],
                'hucreno_6': ['Terkin', 'Terkin Sebebi', 'Tarih Yev']
            },
            'ipotek_detay': {
                'hucreno_1': ['Alacaklı'],
                'hucreno_2': ['Müşterek'],
                'hucreno_3': ['Borç'],
                'hucreno_4': ['Faiz'],
                'hucreno_5': ['Derece'],
                'hucreno_6': ['Süre'],
                'hucreno_7': ['Tesis']
            } ,
            'malik_bilgi': {
                'hucreno_1': ['Hisse', 'Sistem'],
                'hucreno_2': ['Malik'],
                'hucreno_3': ['El Birliği'],
                'hucreno_4': ['Pay'],
                'hucreno_5': ['Metrekare'],
                'hucreno_6': ['Toplam'],
                'hucreno_7': ['Edinme'],
                'hucreno_8': ['Terkin']
            },
            'tekli_ipotek': {
                'hucreno_1': ['Ipotek'],
                'hucreno_2': ['',' '],
                'hucreno_3': ['',' '],
                'hucreno_4': ['',' '],
                'hucreno_5': ['',' '],
                'hucreno_6': ['',' '],
                'hucreno_7': ['',' '],
                'hucreno_8': ['',' ']
            },
            'hissedarm2': {
                'hucreno_1': ['No'],
                'hucreno_2': ['',' '],
                'hucreno_3': ['No'],
                'hucreno_4': ['Payda'],
                'hucreno_5': ['',' '],
                'hucreno_6': ['Metrekare'],
                'hucreno_7': ['Sebebi-Tarih- Yevmiye','Sebebi-Tarih - Yevmiye'],
                'hucreno_8': ['Tarih-Yevmiye']
            }
        }
    
        # Sayfa 1 özel başlıkları
        page_one_headers = [
            'Makbuz No',
            'Dekont No',
            'Başvuru No',
            'Zemin Tipi:',
            'Taşınmaz Kimlik No:',
            'İl/İlçe:',
            'Ada/Parsel:',
            'Mahalle/Köy Adı:',
            'Mevkii:',
            'Cilt/Sayfa No:',
            'Kayıt Durum:',
            'Kurum Adı:',
            'AT Yüzölçüm(m2):',
            'Bağımsız Bölüm Nitelik:',
            'Bağımsız Bölüm Brüt YüzÖlçümü:',
            'Bağımsız Bölüm Net YüzÖlçümü:',
            'Blok/Kat/Giriş/BBNo:',
            'Arsa Pay/Payda:',
            'Ana Taşınmaz Nitelik:'
        ]

        # Sayfa 1 başlık kontrolü
        first_cell = str(row.get('hucreno_1', '')).strip()
        for header in page_one_headers:
            if self.similar(first_cell, header) > 0.8:  # Benzerlik eşiği
                return True
    
        # Diğer başlık tipleri kontrolü
        for header_type, patterns in header_types.items():
            matches = 0
            required_matches = 2  # En az 2 hücre eşleşmesi gerekiyor
        
            for column, expected_values in patterns.items():
                if column not in row:
                    continue
                
                cell_value = str(row[column]).strip().lower()
                if not cell_value:
                    continue
                
                for expected in expected_values:
                    if self.similar(cell_value, expected.lower()) > 0.8:
                        matches += 1
                        break
                    
            if matches >= required_matches:
                return True
            
        return False

    #baslikontrol EVET, HAYIR yazımı
    def update_headers(self):
        """Veritabanındaki başlıkları günceller"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            # Sadece hucreno_11 değeri 'X' olmayan kayıtların başlık kontrollerini sıfırla
            cursor.execute("""
                UPDATE tapu_verileri 
                SET baslikontrol = 'HAYIR'
                WHERE hucreno_11 IS NULL OR hucreno_11 != 'X'
            """)          
        
            # Sadece hucreno_11 değeri 'X' olmayan satırları kontrol et
            cursor.execute("""
                SELECT rowid, * 
                FROM tapu_verileri 
                WHERE hucreno_11 IS NULL OR hucreno_11 != 'X'
            """)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
        
            for row in rows:
                row_dict = dict(zip(columns, row))
                row_id = row_dict['rowid']
            
                # Başlık kontrolü
                if self.is_header(row_dict):
                    cursor.execute("""
                        UPDATE tapu_verileri 
                        SET baslikontrol = 'EVET' 
                        WHERE rowid = ?
                    """, (row_id,))
            
            conn.commit()            
        
        except Exception as e:            
            conn.rollback()
        finally:
            conn.close()

    #Verileri birleştirme işlemi
    def merge_rows(self):        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            cursor.execute("""
                SELECT MAX(rowid) 
                FROM tapu_verileri 
                WHERE hucreno_11 IS NULL OR hucreno_11 != 'X'
            """)
            max_id = cursor.fetchone()[0]

            if not max_id:  # İşlenecek kayıt yoksa
                return True
        
            for current_id in range(max_id, 1, -1):
                # Mevcut satırı al - sadece işlenmemiş kayıtlar
                cursor.execute("""
                    SELECT rowid, baslikontrol, hucreno_1, hucreno_2, hucreno_3, hucreno_4,
                           hucreno_5, hucreno_6, hucreno_7, hucreno_8, hucreno_9, hucreno_10, hucreno_11
                    FROM tapu_verileri 
                    WHERE rowid = ?
                    AND (hucreno_11 IS NULL OR hucreno_11 != 'X')
                """, (current_id,))

                current_row = cursor.fetchone()
            
                if not current_row:
                    continue
                
                # Başlık satırı veya hucreno_1 dolu ise atla
                if current_row[1] == 'EVET' or (current_row[2] and current_row[2].strip()):
                    continue
            
                # Bir üst satırı al
                cursor.execute("""
                    SELECT rowid, baslikontrol, hucreno_1, hucreno_2, hucreno_3, hucreno_4,
                           hucreno_5, hucreno_6, hucreno_7, hucreno_8, hucreno_9, hucreno_10, hucreno_11
                    FROM tapu_verileri 
                    WHERE rowid = ?
                """, (current_id - 1,))
                upper_row = cursor.fetchone()
            
                if not upper_row or upper_row[1] == 'EVET':
                    continue
            
                # Birleştirme işlemi
                update_values = []
                needs_update = False
            
                for i in range(2, 13):  # hucreno_1'den hucreno_11'e
                    upper_value = str(upper_row[i] or '').strip()
                    current_value = str(current_row[i] or '').strip()
                
                    if current_value:
                        merged_value = f"{upper_value} {current_value}".strip()
                        update_values.append(merged_value)
                        needs_update = True
                    else:
                        update_values.append(upper_value)
            
                if needs_update:
                    # Üst satırı güncelle
                    cursor.execute("""
                        UPDATE tapu_verileri 
                        SET hucreno_1=?, hucreno_2=?, hucreno_3=?, hucreno_4=?,
                            hucreno_5=?, hucreno_6=?, hucreno_7=?, hucreno_8=?,
                            hucreno_9=?, hucreno_10=?, hucreno_11=?
                        WHERE rowid = ?
                    """, (*update_values, current_id - 1))
                
                    # Mevcut satırı işaretle
                    cursor.execute("""
                        UPDATE tapu_verileri 
                        SET baslikontrol = 'SILINECEK'
                        WHERE rowid = ?
                    """, (current_id,))
        
            conn.commit()
            #print("Veri birleştirme tamamlandı")
        
        except Exception as e:
            #print(f"Hata: {e}")
            conn.rollback()
        finally:
            conn.close()

    def create_tasinmaz_table(self):
            """Taşınmaz tablosunu siler ve yeniden oluşturur"""
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
    
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tasinmaz (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        tasinmaz_no TEXT UNIQUE,
                        zemintipi TEXT,
                        il_ilce TEXT,
                        kurum_adi TEXT,
                        mahalle TEXT,
                        mevki TEXT,
                        cilt_sayfa_no TEXT,
                        kayitdurumu TEXT,
                        ada_parsel TEXT,
                        at_yuzolcum TEXT,
                        bb_nitelik TEXT,
                        bb_brüt_yuzolcum TEXT,
                        bb_net_yuzolcum TEXT,
                        blok_kat_girisi_bbno TEXT,
                        arsa_pay_payda TEXT,
                        ana_tasinmaz_nitelik TEXT,
                        tapu_tarih TEXT,
                        baslik_islem_yapildi BOOLEAN DEFAULT FALSE 
                    )
                """)

                # Sadece işlenmemiş kayıtları al
                cursor.execute("""
                    SELECT rowid, hucreno_1, hucreno_2 
                    FROM tapu_verileri 
                    WHERE sayfano = 1
                    AND (hucreno_11 IS NULL OR hucreno_11 != 'X')
                    ORDER BY rowid
                """)
                rows = cursor.fetchall()

                tapu_count = 0
                current_group = []
                all_groups = []

                # Verileri gruplara ayır
                for row in rows:
                    current_group.append(row)
                    # Eğer "Zemin Tipi:" bulunursa ve öncesinde grup varsa, yeni grup başlat
                    if row[1] and self.similar(row[1], 'Zemin Tipi:') >= 0.60 and len(current_group) > 1:
                        all_groups.append(current_group[:-1])
                        current_group = [row]

                # Son grubu ekle
                if current_group:
                    all_groups.append(current_group)

                # Her grup için işlem yap
                for group in all_groups:
                    try:
                        # Taşınmaz numarasını bul
                        tasinmaz_no = None
                        for row in group:
                            if row[1] and self.similar(row[1], 'Taşınmaz Kimlik No:') >= 0.85:
                                tasinmaz_no = row[2]
                                break

                        if not tasinmaz_no:
                            #print(f"Grup içinde taşınmaz no bulunamadı, atlanıyor.")
                            continue

                        # Bu taşınmaz no zaten var mı kontrol et
                        cursor.execute("SELECT COUNT(*) FROM tasinmaz WHERE tasinmaz_no = ?", (tasinmaz_no,))
                        if cursor.fetchone()[0] > 0:
                            continue

                        # Alan eşleştirmeleri
                        field_matches = {
                            'zemintipi': ('Zemin Tipi:', 0.60),
                            'il_ilce': ('İl/İlçe:', 0.60),
                            'kurum_adi': ('Kurum Adı:', 0.60),
                            'mahalle': ('Mahalle/Köy Adı:', 0.60),
                            'mevki': ('Mevkii:', 0.60),
                            'cilt_sayfa_no': ('Cilt/Sayfa No:', 0.60),
                            'kayitdurumu': ('Kayıt Durum:', 0.60),
                            'ada_parsel': ('Ada/Parsel:', 0.60),
                            'at_yuzolcum': ('AT Yüzölçüm(m2):', 0.80),
                            'bb_nitelik': ('Bağımsız Bölüm Nitelik:', 0.98),
                            'bb_brüt_yuzolcum': ('Bağımsız Bölüm Brüt YüzÖlçümü:', 0.98),
                            'bb_net_yuzolcum': ('Bağımsız Bölüm Net YüzÖlçümü:', 0.98),
                            'blok_kat_girisi_bbno': ('Blok/Kat/Giriş/BBNo:', 0.50),
                            'arsa_pay_payda': ('Arsa Pay/Payda:', 0.50)
                        }

                        # Her alan için değer bul
                        field_values = {'tasinmaz_no': tasinmaz_no}
                    
                        # Normal alanları doldur
                        for field, (pattern, threshold) in field_matches.items():
                            field_values[field] = None
                            for row in group:
                                if row[1] and self.similar(row[1], pattern) >= threshold:
                                    field_values[field] = row[2] if row[2] else None
                                    break
                    
                        # Ana taşınmaz nitelik için özel sorgu
                        cursor.execute("""
                            SELECT hucreno_2
                            FROM tapu_verileri
                            WHERE tasinmaz_kimlik = ? 
                            AND sayfano = 1 
                            AND hucreno_1 LIKE '%Ana Taşınmaz Nitelik:%'
                        """, (tasinmaz_no,))

                        result = cursor.fetchone()

                        if result and result[0]:  # Eğer direkt eşleşme bulunduysa
                            field_values['ana_tasinmaz_nitelik'] = result[0]
                        else:  # Bulunamadıysa ikinci yöntemi dene
                            cursor.execute("""
                                SELECT hucreno_2
                                FROM tapu_verileri
                                WHERE tasinmaz_kimlik = ?
                                AND takyidat_baslik = 'TAPU KAYIT BİLGİSİ'
                                AND sayfano = 1
                                ORDER BY satirno DESC
                                LIMIT 1
                            """, (tasinmaz_no,))
    
                            result = cursor.fetchone()
                            if result:
                                field_values['ana_tasinmaz_nitelik'] = result[0]
                            else:
                                field_values['ana_tasinmaz_nitelik'] = None

                        # Verileri taşınmaz tablosuna ekle
                        fields = list(field_values.keys())
                        placeholders = ','.join(['?' for _ in range(len(fields))])
                        insert_query = f"""
                            INSERT INTO tasinmaz (
                                {','.join(fields)}
                            ) VALUES ({placeholders})
                        """
                
                        cursor.execute(insert_query, [field_values[field] for field in fields])
                        tapu_count += 1
                        #print(f"Taşınmaz no {tasinmaz_no} için veriler başarıyla eklendi.")

                    except Exception as e:
                        #print(f"Grup işlenirken hata: {e}")
                        continue

                conn.commit()
                #print(f"İşlem tamamlandı. Toplam {tapu_count} adet tapu verisi aktarıldı.")
        
            except Exception as e:
                #print(f"Genel hata: {e}")
                conn.rollback()
            finally:
                conn.close()

    #Tasinmaz numaralarini tapu_verileri tablosuna ekler
    def assign_tasinmaz_numbers(self):        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        try:
            cursor.execute("""
                WITH TapuBolum AS (
                    SELECT 
                        rowid,
                        hucreno_1,
                        hucreno_2,
                        CASE 
                            WHEN hucreno_1 = 'Makbuz No' THEN 1 
                            ELSE 0 
                        END as yeni_tapu_baslangic
                    FROM tapu_verileri
                    WHERE hucreno_11 IS NULL OR hucreno_11 != 'X'
                    ORDER BY rowid
                )
                SELECT 
                    rowid,
                    SUM(yeni_tapu_baslangic) OVER (ORDER BY rowid) as tapu_grup_no
                FROM TapuBolum
            """)
        
            gruplar = cursor.fetchall()
        
            # Her bir grup için taşınmaz numarasını bul ve güncelle
            current_grup = None
            current_tasinmaz = None
        
            for rowid, grup_no in gruplar:
                if grup_no != current_grup:
                    # Yeni grup başladı, taşınmaz numarasını bul
                    cursor.execute("""
                        SELECT hucreno_2 
                        FROM tapu_verileri 
                        WHERE hucreno_1 LIKE '%Taşınmaz Kimlik No%'
                        AND rowid >= ?
                        ORDER BY rowid
                        LIMIT 1
                    """, (rowid,))
                
                    result = cursor.fetchone()
                    if result:
                        current_tasinmaz = result[0]
                    current_grup = grup_no
            
                if current_tasinmaz:
                    cursor.execute("""
                        UPDATE tapu_verileri
                        SET tasinmaz_kimlik = ?
                        WHERE rowid = ?
                    """, (current_tasinmaz, rowid))
        
            conn.commit()
            return True
        
        except Exception as e:
            #print(f"Hata: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def delete_marked_rows(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            cursor.execute("""
                DELETE FROM tapu_verileri 
                WHERE baslikontrol = 'SILINECEK'
                AND (hucreno_11 IS NULL OR hucreno_11 != 'X')
            """)
            conn.commit()
        
        except Exception as e:
            conn.rollback()
        finally:
            conn.close()

    def update_tapu_kayit_bilgisi(self):
        """
        Belirli koşullara uyan kayıtların takyidat_baslik alanını günceller
        """

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            updates = 0
            # sayfa 1'deki tüm kayıtları al
            cursor.execute("""
                SELECT rowid, hucreno_1, satirno 
                FROM tapu_verileri 
                WHERE sayfano = 1
            """)
            records = cursor.fetchall()
        
            # Her kayıt için kontrol et
            for rowid, hucreno_1, satirno in records:
                if not hucreno_1:
                    continue
                
                hucreno_1 = str(hucreno_1).strip()
                
                # Zemin Tipi kontrolü
                if (self.similar(hucreno_1, "Zemin Tipi:") >= 0.95) and (satirno in [1, 2, 3]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue
                    
                # Taşınmaz Kimlik No kontrolü    
                if (self.similar(hucreno_1, "Taşınmaz Kimlik No:") >= 0.95) and (satirno in [2, 3, 4]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue
                    
                # İl/İlçe kontrolü
                if (self.similar(hucreno_1, "İl/İlçe:") >= 0.95) and (satirno in [3, 4, 5]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Kurum Adı kontrolü
                if (self.similar(hucreno_1, "Kurum Adı:") >= 0.95) and (satirno in [4, 5, 6]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Mahalle/Köy Adı kontrolü
                if (self.similar(hucreno_1, "Mahalle/Köy Adı:") >= 0.95) and (satirno in [5, 6, 7]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Mevkii kontrolü
                if (self.similar(hucreno_1, "Mevkii:") >= 0.95) and (satirno in [6, 7, 8]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Cilt/Sayfa No kontrolü
                if (self.similar(hucreno_1, "Cilt/Sayfa No:") >= 0.95) and (satirno in [7, 8, 9]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Kayıt Durum kontrolü
                if (self.similar(hucreno_1, "Kayıt Durum:") >= 0.95) and (satirno in [8, 9, 10]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Ada/Parsel kontrolü
                if (self.similar(hucreno_1, "Ada/Parsel:") >= 0.95) and (satirno in [9, 10, 11]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # AT Yüzölçüm(m2) kontrolü
                if (self.similar(hucreno_1, "AT Yüzölçüm(m2):") >= 0.95) and (satirno in [10, 11, 12]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Bağımsız Bölüm Nitelik kontrolü
                if (self.similar(hucreno_1, "Bağımsız Bölüm Nitelik:") >= 0.95) and (satirno in [11, 12, 13]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue
                
                # Bağımsız Bölüm Brüt YüzÖlçümü kontrolü
                if (self.similar(hucreno_1, "Bağımsız Bölüm Brüt YüzÖlçümü:") >= 0.95) and (satirno in [12, 13, 14]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Bağımsız Bölüm Net YüzÖlçümü kontrolü
                if (self.similar(hucreno_1, "Bağımsız Bölüm Net YüzÖlçümü:") >= 0.95) and (satirno in [13, 14, 15]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Blok/Kat/Giriş/BBNo kontrolü
                if (self.similar(hucreno_1, "Blok/Kat/Giriş/BBNo:") >= 0.95) and (satirno in [14, 15, 16]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Arsa Pay/Payda kontrolü
                if (self.similar(hucreno_1, "Arsa Pay/Payda:") >= 0.95) and (satirno in [15, 16, 17]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue

                # Ana Taşınmaz Nitelik kontrolü
                if (self.similar(hucreno_1, "Ana Taşınmaz Nitelik:") >= 0.95) and (satirno in [16, 17]):
                    cursor.execute("UPDATE tapu_verileri SET takyidat_baslik = 'TAPU KAYIT BİLGİSİ' WHERE rowid = ?", (rowid,))
                    updates += 1
                    continue
                
            # En son işlem olarak başarıyla işlenen kayıtları işaretle
            cursor.execute("""
                UPDATE tapu_verileri 
                SET hucreno_11 = 'X'
                WHERE (hucreno_11 IS NULL OR hucreno_11 != 'X')
            """)
        
            conn.commit()
            return True
        
        except Exception as e:
            conn.rollback()
            return False
        finally:
            conn.close()

    def process_all(self):
        """Tüm işlemleri sırayla çalıştırır"""
        try:
            self.update_headers()
            self.merge_rows()
            self.delete_marked_rows()
            self.create_tasinmaz_table()
            self.assign_tasinmaz_numbers()
            self.update_tapu_kayit_bilgisi()            
            return True
    
        except Exception as e:
            return False


    #______________Takproson dan cagrilanlar__________________# 

    # Takproson dan cagriliyor koordinat sistemine gore bulunan basliklari yaz 
    def update_takyidat_headers(self):
        """Takyidat başlıklarını günceller"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Sadece işlenmemiş taşınmazları al
            cursor.execute("""
                SELECT tasinmaz_no 
                FROM tasinmaz 
                WHERE baslik_islem_yapildi = FALSE 
                OR baslik_islem_yapildi IS NULL
            """)
    
            tasinmaz_nolar = cursor.fetchall()
           
            #print("İşlenen t a ş ı n m a z l a r ", tasinmaz_nolar)

            if not tasinmaz_nolar:
                return True, "İşlenecek yeni taşınmaz kaydı bulunmuyor."

            toplam_guncellenen = 0
            islem_yapilan_tasinmazlar = []
    
            for tasinmaz_no, in tasinmaz_nolar:
                try:
                    # Bu taşınmaz için başlık bilgilerini sıralı şekilde al
                    cursor.execute("""
                        SELECT baslik, baslik_deger
                        FROM baslik_bilgileri 
                        WHERE tasinmaz_kimlik = ? 
                        ORDER BY baslik_deger
                    """, (tasinmaz_no,))
            
                    basliklar = cursor.fetchall()
            
                    if not basliklar:
                        logging.warning(f"Taşınmaz {tasinmaz_no} için başlık bulunamadı")
                        continue

                    # Her başlık için işlem yap
                    baslik_islem_basarili = True
                    guncellenen_kayit = 0
            
                    for i, (baslik, baslik_deger) in enumerate(basliklar):
                        try:
                            if i == 0:  # İlk başlık
                                next_deger = basliklar[1][1] if len(basliklar) > 1 else float('inf')
                                where_clause = "baslik_deger < ?"
                                params = (baslik, tasinmaz_no, next_deger, baslik)
                            elif i == len(basliklar) - 1:  # Son başlık
                                where_clause = "baslik_deger >= ?"
                                params = (baslik, tasinmaz_no, baslik_deger, baslik)
                            else:  # Ara başlıklar
                                next_deger = basliklar[i + 1][1]
                                where_clause = "baslik_deger >= ? AND baslik_deger < ?"
                                params = (baslik, tasinmaz_no, baslik_deger, next_deger, baslik)

                            # Güncelleme yap
                            update_sql = f"""
                                UPDATE tapu_verileri 
                                SET takyidat_baslik = ?
                                WHERE tasinmaz_kimlik = ? 
                                AND {where_clause}
                                AND (takyidat_baslik IS NULL OR takyidat_baslik != ?) 
                                {"" if baslik == "TAPU KAYIT BİLGİSİ" else "AND (baslikontrol != 'EVET' OR baslikontrol IS NULL)"}
                            """

                            cursor.execute(update_sql, params)
                            guncellenen_kayit += cursor.rowcount

                        except Exception as e:
                            logging.error(f"Başlık işleme hatası - Taşınmaz: {tasinmaz_no}, Başlık: {baslik}: {str(e)}")
                            baslik_islem_basarili = False
                            break

                    if baslik_islem_basarili and guncellenen_kayit > 0:
                        # Bu taşınmaz için işlem başarılı, durumu güncelle
                        cursor.execute("""
                            UPDATE tasinmaz 
                            SET baslik_islem_yapildi = TRUE 
                            WHERE tasinmaz_no = ?
                        """, (tasinmaz_no,))
                
                        toplam_guncellenen += guncellenen_kayit
                        islem_yapilan_tasinmazlar.append(tasinmaz_no)
                
                        # Her taşınmaz sonrası commit
                        conn.commit()

                except Exception as e:
                    logging.error(f"Taşınmaz işleme hatası - Taşınmaz: {tasinmaz_no}: {str(e)}")
                    conn.rollback()
                    continue

            return True, f"""Başlık güncellemeleri tamamlandı.
                Toplam {len(islem_yapilan_tasinmazlar)} taşınmaz işlendi.
                Toplam {toplam_guncellenen} kayıt güncellendi."""

        except Exception as e:
            return False, f"Genel hata oluştu: {str(e)}"

        finally:
            if conn:
                conn.close()

    #Takproson dan cagriliyor 
    def update_missing_headers(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            # 1. Tapu verilerinden boş başlıklı kayıtları bul
            cursor.execute("""
                SELECT rowid, hucreno_1, tasinmaz_kimlik 
                FROM tapu_verileri 
                WHERE (takyidat_baslik IS NULL OR takyidat_baslik = '')
                AND baslikontrol = 'HAYIR'
                AND hucreno_1 IS NOT NULL
                AND trim(hucreno_1) != ''
            """)
        
            empty_headers = cursor.fetchall()
            updated_count = 0
        
            for record in empty_headers:
                rowid, hucreno_1, tasinmaz_kimlik = record
            
                # 2. Koordinat bilgilerinden eşleşen kaydı bul - önce tam eşleşme, sonra LIKE
                cursor.execute("""
                    SELECT sayfano, y_koordinat, hucreno_1_deger
                    FROM koordinat_bilgileri_ext 
                    WHERE tasinmaz_kimlik = ?
                    AND length(?) >= 3
                    AND (
                        hucreno_1_deger = ?
                        OR 
                        (hucreno_1_deger LIKE ? || '%' AND hucreno_1_deger != ?)
                    )
                    ORDER BY 
                        CASE 
                            WHEN hucreno_1_deger = ? THEN 0
                            ELSE 1
                        END
                    LIMIT 1
                """, (tasinmaz_kimlik, hucreno_1.strip(), hucreno_1.strip(), 
                      hucreno_1.strip(), hucreno_1.strip(), hucreno_1.strip()))
            
                coord_record = cursor.fetchone()
                if not coord_record:
                    continue
                
                sayfano, y_koordinat, matched_hucreno = coord_record
            
                # 3. Başlık değerini hesapla
                baslik_deger = int(sayfano * 1000 + y_koordinat)
            
                # 4. Koordinat tablosunu güncelle - eşleşen kayıt için
                cursor.execute("""
                    UPDATE koordinat_bilgileri_ext 
                    SET baslik_deger = ? 
                    WHERE tasinmaz_kimlik = ?
                    AND hucreno_1_deger = ?
                """, (baslik_deger, tasinmaz_kimlik, matched_hucreno))
            
                # 5. En yakın küçük başlık değerini bul
                cursor.execute("""
                    SELECT baslik, baslik_deger 
                    FROM baslik_bilgileri 
                    WHERE tasinmaz_kimlik = ? 
                    AND baslik_deger <= ? 
                    ORDER BY baslik_deger DESC 
                    LIMIT 1
                """, (tasinmaz_kimlik, baslik_deger))
            
                header_record = cursor.fetchone()
                if not header_record:
                    continue
                
                baslik, _ = header_record

                # 5.5 Tapu verilerine baslik_deger bilgisini ekle
                cursor.execute("""
                    UPDATE tapu_verileri 
                    SET baslik_deger = ? 
                    WHERE rowid = ?
                """, (baslik_deger, rowid))
            
                # 6. Tapu verilerini güncelle
                cursor.execute("""
                    UPDATE tapu_verileri 
                    SET takyidat_baslik = ? 
                    WHERE rowid = ?
                """, (baslik, rowid))
            
                updated_count += 1
        
            conn.commit()
            return True, f"{updated_count} kayıt güncellendi"
        
        except Exception as e:
            conn.rollback()
            return False, f"Hata: {str(e)}"
        
        finally:
            conn.close()

    # #Takproson dan cagriliyor Sayfa numaralarini 1000 ile carp ve ykoordinat degerini ekle  
    def add_baslik_deger_columns(self):
        """Tablolara baslik_deger kolonunu ekler ve değerleri hesaplar"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Sütunların var olup olmadığını kontrol et
            cursor.execute("PRAGMA table_info(baslik_bilgileri)")
            baslik_columns = [column[1] for column in cursor.fetchall()]
        
            cursor.execute("PRAGMA table_info(tapu_verileri)")
            tapu_columns = [column[1] for column in cursor.fetchall()]

            # baslik_bilgileri tablosuna baslik_deger kolonunu ekle
            if 'baslik_deger' not in baslik_columns:
                cursor.execute("""
                    ALTER TABLE baslik_bilgileri 
                    ADD COLUMN baslik_deger INTEGER
                """)

            # tapu_verileri tablosuna baslik_deger kolonunu ekle    
            if 'baslik_deger' not in tapu_columns:
                cursor.execute("""
                    ALTER TABLE tapu_verileri 
                    ADD COLUMN baslik_deger INTEGER
                """)

            # baslik_bilgileri tablosundaki değerleri güncelle
            cursor.execute("""
                UPDATE baslik_bilgileri 
                SET baslik_deger = (
                    CAST(sayfa_no AS INTEGER) * 1000 + 
                    CAST(ROUND(CAST(y_koordinat AS REAL)) AS INTEGER)
                )
                WHERE baslik_deger IS NULL 
                AND sayfa_no IS NOT NULL 
                AND y_koordinat IS NOT NULL
            """)
        
            # tapu_verileri tablosundaki değerleri güncelle
            cursor.execute("""
                UPDATE tapu_verileri 
                SET baslik_deger = CAST((CAST(sayfano AS INTEGER) * 1000) + 
                    CAST(ROUND(y_koordinat) AS INTEGER) AS INTEGER)
                WHERE baslik_deger IS NULL 
                AND sayfano IS NOT NULL 
                AND y_koordinat IS NOT NULL
            """)
            
            # Güncellenen kayıt sayısını al
            cursor.execute("SELECT COUNT(*) FROM baslik_bilgileri WHERE baslik_deger IS NOT NULL")
            baslik_count = cursor.fetchone()[0]
        
            cursor.execute("SELECT COUNT(*) FROM tapu_verileri WHERE baslik_deger IS NOT NULL")
            tapu_count = cursor.fetchone()[0]

            conn.commit()
        
            # Başlık değerleri güncellendikten sonra takyidat başlıklarını güncelle
            baslik_sonuc, mesaj = self.update_takyidat_headers()
        
            if not baslik_sonuc:
                logging.error(f"Takyidat başlıkları güncellenirken hata: {mesaj}")
                return False, 0, 0
            
            return True, baslik_count, tapu_count
        
        except Exception as e:
            print(f"Hata: {str(e)}")
            conn.rollback()
            return False, 0, 0
    
        finally:
            conn.close()

    #Takproson dan cagriliyor
    def update_coordinate_assignments(self):   
        """
        Aynı koordinata sahip verilerin düzeltilmesi için koordinat ataması yapar
        ve takyidat başlıklarını günceller
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            # Debug: Başlangıç durumu kontrolü
            #cursor.execute("SELECT COUNT(*) FROM koordinat_bilgileri_ext WHERE baslik_deger IS NULL")
            #null_count = cursor.fetchone()[0]
            #print(f"Başlangıçta baslik_deger NULL olan kayıt sayısı: {null_count}")

            # Önce koordinat_bilgileri_ext tablosunda baslik_deger hesapla
            cursor.execute("""
                UPDATE koordinat_bilgileri_ext 
                SET baslik_deger = (sayfano * 1000) + CAST(ROUND(y_koordinat) AS INTEGER)
                WHERE baslik_deger IS NULL
            """)
        
            #print(f"koordinat_bilgileri_ext güncelleme etkilenen kayıt: {cursor.rowcount}")

            # Tekrarlanan koordinatları bul
            cursor.execute("""
                WITH TekrarEdenler AS (
                    SELECT tv1.rowid as tv_rowid, 
                           tv1.tasinmaz_kimlik, 
                           tv1.sayfano, 
                           tv1.baslik_deger,
                           tv1.hucreno_1,
                           COUNT(*) OVER (PARTITION BY tv1.tasinmaz_kimlik, tv1.sayfano, tv1.baslik_deger) as tekrar_sayisi
                    FROM tapu_verileri tv1
                    WHERE tv1.baslik_deger IS NOT NULL 
                    AND tv1.takyidat_baslik != 'TAPU KAYIT BİLGİSİ'
                )
                SELECT * FROM TekrarEdenler 
                WHERE tekrar_sayisi > 1
                ORDER BY tasinmaz_kimlik, sayfano, baslik_deger, tv_rowid
            """)
        
            tekrarlanan_kayitlar = cursor.fetchall()
            #print(f"\nToplam tekrarlanan kayıt sayısı: {len(tekrarlanan_kayitlar)}")

            guncellenen_kayit_sayisi = 0
        
            for kayit in tekrarlanan_kayitlar:
                tv_rowid, tasinmaz_kimlik, sayfano, baslik_deger, hucreno_1, tekrar_sayisi = kayit
                                
                #print(f"\nİşlenen Kayıt:")
                #print(f"rowid: {tv_rowid}")
                #print(f"tasinmaz_kimlik: {tasinmaz_kimlik}")
                #print(f"sayfano: {sayfano}")
                #print(f"baslik_deger: {baslik_deger}")
                #print(f"hucreno_1: {hucreno_1}")

                # Eşleşen koordinat kaydını bul
                cursor.execute("""
                    SELECT id, baslik_deger, y_koordinat
                    FROM koordinat_bilgileri_ext
                    WHERE tasinmaz_kimlik = ?
                    AND sayfano = ?
                    AND hucreno_1_deger = ?
                    AND (tapu_rowid IS NULL OR tapu_rowid = '')
                    ORDER BY satirno
                    LIMIT 1
                """, (tasinmaz_kimlik, sayfano, hucreno_1))
            
                koordinat_kaydi = cursor.fetchone()
            
                if koordinat_kaydi:
                    koordinat_id, yeni_baslik_deger, y_koordinat = koordinat_kaydi
                    
                    #print(f"Eşleşen Koordinat Kaydı:")
                    #print(f"koordinat_id: {koordinat_id}")
                    #print(f"yeni_baslik_deger: {yeni_baslik_deger}")
                    #print(f"y_koordinat: {y_koordinat}")
                    
                    # koordinat_bilgileri_ext tablosunu güncelle
                    cursor.execute("""
                        UPDATE koordinat_bilgileri_ext
                        SET tapu_rowid = ?
                        WHERE id = ?
                    """, (tv_rowid, koordinat_id))
                
                    #print(f"koordinat_bilgileri_ext güncelleme sonucu: {cursor.rowcount}")
                
                    # tapu_verileri tablosunu güncelle
                    cursor.execute("""
                        UPDATE tapu_verileri
                        SET baslik_deger = ?,
                            y_koordinat = ?
                        WHERE rowid = ?
                    """, (yeni_baslik_deger, y_koordinat, tv_rowid))
                
                    #print(f"tapu_verileri güncelleme sonucu: {cursor.rowcount}")
                
                    if cursor.rowcount > 0:
                        guncellenen_kayit_sayisi += 1
                else:
                    print(f"Eşleşen koordinat kaydı bulunamadı!")

            # Koordinat düzeltmesi sonrası takyidat başlıklarını güncelle
            cursor.execute("""
                UPDATE tapu_verileri 
                SET takyidat_baslik = (
                    SELECT bb.baslik
                    FROM baslik_bilgileri bb
                    WHERE bb.tasinmaz_kimlik = tapu_verileri.tasinmaz_kimlik
                    AND bb.baslik_deger <= tapu_verileri.baslik_deger
                    ORDER BY bb.baslik_deger DESC
                    LIMIT 1
                )
                WHERE EXISTS (
                    SELECT 1 
                    FROM koordinat_bilgileri_ext ke
                    WHERE ke.tapu_rowid = tapu_verileri.rowid
                    AND ke.tapu_rowid IS NOT NULL
                )
                AND takyidat_baslik != 'TAPU KAYIT BİLGİSİ'
            """)
        
            #print(f"\nTakyidat başlıkları güncelleme sonucu: {cursor.rowcount} kayıt güncellendi")
        
            conn.commit()
            #print(f"\nToplam güncellenen kayıt sayısı: {guncellenen_kayit_sayisi}")
        
            # Son durum kontrolü
            cursor.execute("""
                SELECT COUNT(*) as tekrar_sayisi
                FROM (
                    SELECT tasinmaz_kimlik, sayfano, baslik_deger, COUNT(*) as sayi
                    FROM tapu_verileri
                    WHERE baslik_deger IS NOT NULL 
                    AND takyidat_baslik != 'TAPU KAYIT BİLGİSİ'
                    GROUP BY tasinmaz_kimlik, sayfano, baslik_deger
                    HAVING COUNT(*) > 1
                ) tekrarlar
            """)
        

            kalan_tekrar = cursor.fetchone()[0]
            conn.commit()

            basarili, mesaj = self.final_header_check()

            if basarili:
                # Mesaj kutusunda göster
                print("Başlık Kontrol Raporu", mesaj)
                #print(f"İşlem sonrası kalan tekrarlı koordinat sayısı: {kalan_tekrar}")

                # Gereksiz kayıtlar temizleniyor
                cursor.execute("""
                    DELETE FROM koordinat_bilgileri_ext 
                    WHERE tapu_rowid IS NULL 
                    OR tapu_rowid = ''
                """)

                delete_count = cursor.rowcount
                conn.commit()

                print(f"Gereksiz koordinat kayıtlarından {delete_count} adet silindi")
            else:
                print("Hata", mesaj)
        
            return True
        
        except Exception as e:
            print(f"Koordinat atama hatası: {str(e)}")
            logging.error(f"Koordinat atama hatası: {str(e)}")
            conn.rollback()
            return False
        
        finally:
            conn.close()

    #Takproson dan cagriliyor
    def final_header_check(self):
        """
        Boş başlıklı kayıtlar için son kontrol ve güncelleme yapar.
        Bulunamayan kayıtları raporlar.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            # Boş başlıklı kayıtları bul
            cursor.execute("""
                SELECT rowid, sayfano, tasinmaz_kimlik 
                FROM tapu_verileri 
                WHERE (takyidat_baslik IS NULL OR takyidat_baslik = '')
                AND baslikontrol = 'HAYIR'
            """)
        
            empty_headers = cursor.fetchall()
            missing_records = []  # Başlık bulunamayan kayıtlar için
            updated_count = 0
        
            for record in empty_headers:
                rowid, sayfano, tasinmaz_kimlik = record
                header_found = False
            
                # Bu taşınmaz için min ve max rowid değerlerini al
                cursor.execute("""
                    SELECT MIN(rowid), MAX(rowid) 
                    FROM tapu_verileri 
                    WHERE tasinmaz_kimlik = ?
                """, (tasinmaz_kimlik,))
                min_rowid, max_rowid = cursor.fetchone()
            
                # İleri doğru arama (rowid + 1, +2, ..., +6)
                for offset in range(1, 7):
                    next_rowid = rowid + offset
                
                    # Maksimum rowid sınırını kontrol et
                    if next_rowid > max_rowid:
                        break
                    
                    cursor.execute("""
                        SELECT takyidat_baslik, baslikontrol
                        FROM tapu_verileri 
                        WHERE rowid = ?
                        AND tasinmaz_kimlik = ?
                    """, (next_rowid, tasinmaz_kimlik))
                
                    next_record = cursor.fetchone()
                    if not next_record:
                        break
                    
                    next_header, next_baslikontrol = next_record
                
                    if next_baslikontrol == 'EVET':
                        break
                    
                    if next_header and next_baslikontrol == 'HAYIR':
                        cursor.execute("""
                            UPDATE tapu_verileri 
                            SET takyidat_baslik = ? 
                            WHERE rowid = ?
                        """, (next_header, rowid))
                        header_found = True
                        updated_count += 1
                        break
            
                # Eğer ileri aramada bulunamadıysa geriye doğru ara
                if not header_found:
                    for offset in range(1, 7):
                        prev_rowid = rowid - offset
                    
                        # Minimum rowid sınırını kontrol et
                        if prev_rowid < min_rowid:
                            break
                        
                        cursor.execute("""
                            SELECT takyidat_baslik, baslikontrol
                            FROM tapu_verileri 
                            WHERE rowid = ?
                            AND tasinmaz_kimlik = ?
                        """, (prev_rowid, tasinmaz_kimlik))
                    
                        prev_record = cursor.fetchone()
                        if not prev_record:
                            break
                        
                        prev_header, prev_baslikontrol = prev_record
                    
                        if prev_baslikontrol == 'EVET':
                            break
                        
                        if prev_header and prev_baslikontrol == 'HAYIR':
                            cursor.execute("""
                                UPDATE tapu_verileri 
                                SET takyidat_baslik = ? 
                                WHERE rowid = ?
                            """, (prev_header, rowid))
                            header_found = True
                            updated_count += 1
                            break
            
                # Eğer hala başlık bulunamadıysa raporla
                if not header_found:
                    missing_records.append({
                        'rowid': rowid,
                        'sayfano': sayfano,
                        'tasinmaz_kimlik': tasinmaz_kimlik
                    })
        
            conn.commit()
        
            # Rapor mesajını oluştur
            report_message = f"Toplam {updated_count} kayıt güncellendi.\n\n"
            if missing_records:
                report_message += "Başlık bulunamayan kayıtlar:\n"
                for record in missing_records:
                    report_message += f"RowID: {record['rowid']}, Sayfa: {record['sayfano']}, " \
                                    f"Taşınmaz No: {record['tasinmaz_kimlik']}\n"
        
            return True, report_message
        
        except Exception as e:
            return False, f"Hata oluştu: {str(e)}"
        
        finally:
            conn.close()

    #Takproson dan cagriliyor      pdf üzerinde tablo başlıkları sonraki sayfaya taşınca 
    def delete_empty_cells_with_yevmiye(self):
        """
        Belirli hücreleri boş olan ve yevmiye içeren kayıtları siler
        """        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
    
        try:
            # İlk durum: hucreno_1,2,3 boş, hucreno_4 = Yevmiye
            cursor.execute("""
                DELETE FROM tapu_verileri 
                WHERE (hucreno_1 IS NULL OR trim(hucreno_1) = '')
                AND (hucreno_2 IS NULL OR trim(hucreno_2) = '')
                AND (hucreno_3 IS NULL OR trim(hucreno_3) = '')
                AND baslikontrol = 'HAYIR'
                AND hucreno_4 = 'Yevmiye'
            """)
        
            # İkinci durum: hucreno_1,2,3 boş, hucreno_4 = Yevmiye veya hucreno_5 = Sebebi- Tarih- Yevmiye
            cursor.execute("""
                DELETE FROM tapu_verileri 
                WHERE (hucreno_1 IS NULL OR trim(hucreno_1) = '')
                AND (hucreno_2 IS NULL OR trim(hucreno_2) = '')
                AND (hucreno_3 IS NULL OR trim(hucreno_3) = '')
                AND baslikontrol = 'HAYIR'
                AND (
                    hucreno_4 = 'Yevmiye'
                    OR hucreno_5 = 'Sebebi- Tarih- Yevmiye'
                )
            """)
        
            # Üçüncü durum: hucreno_1,2,3,4 boş, hucreno_5 = Yevmiye veya Sebebi- Tarih- Yevmiye
            cursor.execute("""
                DELETE FROM tapu_verileri 
                WHERE (hucreno_1 IS NULL OR trim(hucreno_1) = '')
                AND (hucreno_2 IS NULL OR trim(hucreno_2) = '')
                AND (hucreno_3 IS NULL OR trim(hucreno_3) = '')
                AND (hucreno_4 IS NULL OR trim(hucreno_4) = '')
                AND baslikontrol = 'HAYIR'
                AND (
                    hucreno_5 = 'Yevmiye'
                    OR hucreno_5 = 'Sebebi- Tarih- Yevmiye'
                )
            """)
        
            # Dördüncü durum: hucreno_1,2,3 boş, hucreno_4 = Yevmiye veya Sebebi- Tarih- Yevmiye
            cursor.execute("""
                DELETE FROM tapu_verileri 
                WHERE (hucreno_1 IS NULL OR trim(hucreno_1) = '')
                AND (hucreno_2 IS NULL OR trim(hucreno_2) = '')
                AND (hucreno_3 IS NULL OR trim(hucreno_3) = '')
                AND baslikontrol = 'HAYIR'
                AND (
                    hucreno_4 = 'Yevmiye'
                    OR hucreno_4 = 'Sebebi- Tarih- Yevmiye'
                )
            """)
        
            # Beşinci durum: hucreno_1,2,3,4 boş, hucreno_5 dolu
            cursor.execute("""
                DELETE FROM tapu_verileri 
                WHERE (hucreno_1 IS NULL OR trim(hucreno_1) = '')
                AND (hucreno_2 IS NULL OR trim(hucreno_2) = '')
                AND (hucreno_3 IS NULL OR trim(hucreno_3) = '')
                AND (hucreno_4 IS NULL OR trim(hucreno_4) = '')
                AND baslikontrol = 'HAYIR'
                AND (hucreno_5 IS NOT NULL AND trim(hucreno_5) != '')
            """)
        
            deleted_count = cursor.rowcount
            conn.commit()
            return True, f"{deleted_count} kayıt silindi."
        
        except Exception as e:
            conn.rollback()
            return False, f"Hata oluştu: {str(e)}"
        
        finally:
            conn.close()
     
