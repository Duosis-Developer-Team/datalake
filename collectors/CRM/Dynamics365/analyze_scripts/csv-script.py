import json
import csv

def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f).get('value', [])
    except FileNotFoundError:
        print(f"[-] Dosya bulunamadı: {filepath}. Lütfen catalog endpoint'lerini çektiğinizden emin olun.")
        return []

def build_valuation_catalog():
    print("[*] Katalog verileri okunuyor...")
    
    pricelevels_data = load_json("raw_catalog_pricelevels.json")
    products_data = load_json("raw_catalog_products.json")
    pricing_details_data = load_json("raw_catalog_productpricelevels.json")

    if not pricing_details_data:
        print("[-] Fiyat detayları bulunamadı, işlem iptal edildi.")
        return

    # ID'leri isimlere çevirmek için sözlük (dictionary) oluşturuyoruz
    price_levels = {p['pricelevelid']: p.get('name', 'Bilinmeyen Liste') for p in pricelevels_data}
    products = {p['productid']: p.get('name', 'Bilinmeyen Ürün') for p in products_data}

    csv_filename = "standart_fiyat_katalogu.csv"
    headers = ["Fiyat_Listesi_Adi", "Hizmet_Adi", "Birim", "Standart_Birim_Fiyat_TL"]

    with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(headers)
        
        for item in pricing_details_data:
            list_id = item.get("_pricelevelid_value")
            prod_id = item.get("_productid_value")
            
            # Aradığınız Birim Fiyat (Amount)
            amount = item.get("amount", 0) 
            unit = item.get("_uomid_value@OData.Community.Display.V1.FormattedValue", "Birim Yok")
            
            list_name = price_levels.get(list_id, str(list_id))
            prod_name = products.get(prod_id, str(prod_id))
            
            writer.writerow([list_name, prod_name, unit, amount])

    print(f"[+] Başarılı! Standart fiyatlar csv'ye yazıldı: {csv_filename}")

if __name__ == "__main__":
    build_valuation_catalog()
