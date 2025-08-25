#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import pandas as pd

def main():
    """
    NiFi'den stdin yoluyla gelen JSON verisini işler, Brocade ve IBM envanterini
    eşleştirir ve sonucu stdout'a JSON olarak yazar.
    """
    try:
        # 1. NiFi'den gelen birleşik JSON verisini oku
        data = json.load(sys.stdin)

        # 2. JSON içindeki her bir listeyi pandas DataFrame'e çevir
        df_devices = pd.DataFrame(data.get("brocade_devices", []))
        df_ports = pd.DataFrame(data.get("port_status", []))
        df_ibm = pd.DataFrame(data.get("ibm_inventory", []))

        # Eğer herhangi bir veri seti boşsa, boş bir sonuçla çık
        if df_devices.empty or df_ibm.empty:
            print(json.dumps([]))
            return

        # 3. VERİ HAZIRLAMA VE OPTİMİZASYON
        # Brocade WWPN'lerindeki ':' karakterlerini temizleyerek yeni bir sütun oluştur
        df_devices['cleaned_wwpn'] = df_devices['device_wwpn'].str.replace(':', '', regex=False)

        # IBM DataFrame'ini, wwpn ve wwpn2'yi tek bir sütunda birleştirecek şekilde 'unpivot' yap
        # Bu, tek bir birleştirme işlemi yapmamızı sağlar
        df_ibm_melted = pd.melt(df_ibm,
                                id_vars=['servername', 'lparname'],
                                value_vars=['wwpn', 'wwpn2'],
                                value_name='cleaned_wwpn'
                               ).dropna(subset=['cleaned_wwpn']) # Boş wwpn'leri kaldır

        # 4. EŞLEŞTİRME (JOIN)
        # Temizlenmiş WWPN'ler üzerinden iki DataFrame'i birleştir (SQL JOIN'in karşılığı)
        df_merged = pd.merge(
            df_devices,
            df_ibm_melted,
            on='cleaned_wwpn',
            how='inner' # Sadece eşleşen kayıtları al
        )

        # Port adlarını eklemek için port_status verisiyle birleştirme
        # Yinelenen port_index kayıtlarını kaldırarak haritalamayı temizle
        if not df_ports.empty:
            df_ports = df_ports.drop_duplicates(subset=['port_index'])
            df_merged = pd.merge(
                df_merged,
                df_ports,
                on='port_index',
                how='left'
            )
        else:
            df_merged['name'] = None


        # 5. SONUÇLARI FORMATLAMA VE ÇIKTI
        # İstenen sütunları seç ve yeniden adlandır
        final_df = df_merged[[
            'switch_host',
            'collection_timestamp',
            'name', # port adı
            'device_wwpn',
            'servername',
            'lparname'
        ]].rename(columns={'name': 'port_name'})

        # DataFrame'i JSON formatında standart çıktıya yazdır
        # NiFi'deki bir sonraki işlemci bu çıktıyı yakalayacak
        result_json = final_df.to_json(orient="records", date_format="iso")
        print(result_json)

    except Exception as e:
        # Hata durumunda, NiFi'nin loglarında görmek için standart hataya yazdır
        print(f"Bir hata oluştu: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()