# Sosyal Ag Analizi Proje Raporu

## 1. Proje Basligi ve Problem Tanimi

**Proje basligi:** Urun odakli influencer onerisi icin sosyal ag temelli creator omurgasi analizi

Bu projede analiz edilen ag, urun odakli influencer onerisi sisteminin karar omurgasi olarak kullanilan creator benzerlik agidir. Dugumler tekil creator hesaplarini temsil etmektedir. Kenarlar ise iki creator arasindaki kategori ve hashtag benzerligini gostermektedir. Ag **yonlusuz** ve **agirlikli** olarak modellenmistir. Kenar agirligi, kategori Jaccard benzerliginin %75'i ile hashtag Jaccard benzerliginin %25'inin toplamindan uretilmistir.

**Arastirma sorusu:** Bir urun sorgusu verildiginde sistem hangi influencer'i alan otoritesi, etkilesim ve gerekirse kopru rolu uzerinden one cikarmalidir; bunu destekleyen ag yapisi nasil gorunmektedir?

## 2. Veri Seti

Veri kaynagi proje kapsaminda Apify tabanli Instagram profil ve hashtag taramasi ile olusturulan yerel veri setidir. Analizde kullanilan temiz veri dosyasi:

- `C:\Users\emirh\OneDrive\Desktop\Project_SNA\data\processed\clean_creator_dataset.csv`

| Baslik | Aciklama |
|---|---|
| Veri kaynagi | Instagram profil/hashtag taramasi, yerel islenmis veri |
| Dugum turu | Creator / influencer hesabi |
| Kenar turu | Icerik benzerligi (kategori + hashtag overlap) |
| Dugum sayisi | 389 |
| Kenar sayisi | 6711 |
| Veri formati | CSV, GraphML, PNG, Markdown, Python |

## 3. Ag Modelleme

Ag su sekilde tanimlanmistir:

**G = (V, E)**

- **V:** creator hesaplari
- **E:** iki creator arasindaki benzerlik kenarlari

Beklenen ciktilar bu proje ile birlikte otomatik uretilmistir:

- Dugum listesi
- Kenar listesi
- Komsuluk matrisi
- GraphML formati
- Ag gorselleri

Projede kullanilan temel Python dosyalari:

- `sna_project.py`: agi kurar, olcutleri hesaplar, gorselleri, raporu ve notebook'u uretir.
- `recommender.py`: urun sorgusu geldikten sonra ag olcutlerini kullanarak influencer siralar.
- `taxonomy.py`: urun sinyallerini kategori ve kullanim baglamina donusturen sozluk ve yorumlama katmanini yonetir.
- `app.py`: sistemi basit bir web arayuzu uzerinden calistirir.

## 4. Temel Ag Olcutleri

| Olcut | Deger |
|---|---|
| Dugum sayisi | 389 |
| Kenar sayisi | 6711 |
| Bagli bilesen sayisi | 2 |
| En buyuk bilesen | 338 dugum (86.89%) |
| Yogunluk | 0.0889 |
| Ortalama derece | 34.5039 |
| Ortalama agirlikli derece | 18.7097 |
| Ortalama kumeleme katsayisi | 0.6899 |
| Cap (en buyuk bagli bilesen) | 6 |
| Ortalama en kisa yol (LCC) | 2.97 |

Bu sonuclar agin genel olarak **orta yogunlukta** bir yapida oldugunu gostermektedir. Cap degeri 6 oldugu icin cekirdek yapinin **orta duzeyde kompakt** oldugu soylenebilir. Tum ag iki bagli bilesenden olusmaktadir; bu nedenle cap ve yakinlik temelli olcutler en buyuk bagli bilesen uzerinden yorumlanmistir.

## 5. Merkezilik Analizi

Merkezilik hesaplari en buyuk bagli bilesen uzerinden yapilmistir.

### Top 5 Degree Centrality
| rank | username | score | categories |
| --- | --- | --- | --- |
| 1 | annevebebek2025 | 0.181009 | anne_bebek,evcil_hayvan |
| 2 | hamilelikveanne | 0.181009 | anne_bebek,evcil_hayvan |
| 3 | itssyamaan | 0.181009 | anne_bebek,evcil_hayvan |
| 4 | bizimbebekgunlugu | 0.181009 | anne_bebek,evcil_hayvan |
| 5 | mucizeyolculugum | 0.181009 | anne_bebek,evcil_hayvan |

### Top 5 Betweenness Centrality
| rank | username | score | categories |
| --- | --- | --- | --- |
| 1 | studyconkris | 0.074254 | egitim_kariyer,ev_yasam,evcil_hayvan |
| 2 | merlin.kleiner.verzauberer | 0.059526 | evcil_hayvan,anne_bebek,egitim_kariyer |
| 3 | ikkiturkiye | 0.057941 | otomotiv,finans_is |
| 4 | asliglbaz | 0.033481 | anne_bebek,yemek_mutfak |
| 5 | muzeyyenin_aynasi | 0.03342 | yemek_mutfak,egitim_kariyer |

### Top 5 Closeness Centrality
| rank | username | score | categories |
| --- | --- | --- | --- |
| 1 | itssyamaan | 0.170093 | anne_bebek,evcil_hayvan |
| 2 | annevebebek2025 | 0.16941 | anne_bebek,evcil_hayvan |
| 3 | bizimbebekgunlugu | 0.169324 | anne_bebek,evcil_hayvan |
| 4 | mucizeyolculugum | 0.169128 | anne_bebek,evcil_hayvan |
| 5 | hamilelikveanne | 0.169111 | anne_bebek,evcil_hayvan |

### Top 5 Eigenvector Centrality
| rank | username | score | categories |
| --- | --- | --- | --- |
| 1 | emine.bites | 0.113336 | yemek_mutfak |
| 2 | 1gezi_1kahve | 0.113267 | yemek_mutfak |
| 3 | telveli.kahvem68 | 0.113235 | yemek_mutfak |
| 4 | shushucum | 0.11317 | yemek_mutfak |
| 5 | ela.kitchenn | 0.113084 | yemek_mutfak |

### Top 5 PageRank
| rank | username | score | categories |
| --- | --- | --- | --- |
| 1 | annevebebek2025 | 0.004368 | anne_bebek,evcil_hayvan |
| 2 | hamilelikveanne | 0.004364 | anne_bebek,evcil_hayvan |
| 3 | itssyamaan | 0.004361 | anne_bebek,evcil_hayvan |
| 4 | bizimbebekgunlugu | 0.00436 | anne_bebek,evcil_hayvan |
| 5 | mucizeyolculugum | 0.004344 | anne_bebek,evcil_hayvan |

Merkezilik sonuclari birlikte okundugunda:

- **En baglantili dugum:** `annevebebek2025`. Bu hesap benzer ilgi alanlarina sahip cok sayida creator ile baglantilidir.
- **En guclu kopru dugum:** `studyconkris`. Bu hesap farkli tema gruplari arasinda gecis noktasi gorevi gorur.
- **En hizli erisen dugum:** `itssyamaan`. Bu hesap cekirdek ag icinde digerlerine daha kisa yollarla ulasabilmektedir.
- **Etkili dugum:** `emine.bites`. Bu hesap yalnizca cok baglantili degil, ayni zamanda onemli hesaplara da baglidir.
- **Otorite benzeri dugum:** `annevebebek2025`. Bu dugum, agirlikli baglanti yapisi icinde yuksek genel oneme sahiptir.

## 6. Topluluk Analizi

Topluluk analizi Louvain algoritmasi ile yapilmistir.

| Olcut | Deger |
|---|---|
| Topluluk sayisi | 8 |
| Modularity | 0.630465 |
| En buyuk topluluk | Topluluk 1 (69 dugum) |
| En buyuk toplulugun baskin temalari | otomotiv (54), guzellik_kozmetik (24), oyuncak_hobi (21), evcil_hayvan (11), oyun_espor (6) |

Topluluk ozet tablosu:

| community_id | size | share_of_lcc | top_categories |
| --- | --- | --- | --- |
| 1 | 69 | 0.2041 | otomotiv (54), guzellik_kozmetik (24), oyuncak_hobi (21), evcil_hayvan (11), oyun_espor (6) |
| 2 | 52 | 0.1538 | yemek_mutfak (52), evcil_hayvan (7), oyuncak_hobi (7), fitness_saglik (6), anne_bebek (5) |
| 3 | 46 | 0.1361 | egitim_kariyer (46), evcil_hayvan (27), otomotiv (11), finans_is (4), oyuncak_hobi (2) |
| 4 | 40 | 0.1183 | evcil_hayvan (40), anne_bebek (18), oyuncak_hobi (4), taki_aksesuar (4), otomotiv (2) |
| 5 | 38 | 0.1124 | moda_yasam (36), anne_bebek (21), fitness_saglik (9), evcil_hayvan (8), otomotiv (4) |
| 6 | 34 | 0.1006 | ev_yasam (34), egitim_kariyer (26), dekorasyon_mobilya (4), seyahat_gezi (3), kitap_kultur (2) |
| 7 | 32 | 0.0947 | finans_is (20), teknoloji (14), kitap_kultur (2), oyun_espor (2), seyahat_gezi (1) |
| 8 | 27 | 0.0799 | anne_bebek (27), oyuncak_hobi (3), egitim_kariyer (2), otomotiv (2), fitness_saglik (1) |

Topluluklar anlamsiz rastgele bolunmeler yerine kategori eksenlerine gore toparlanmistir. Bu durum modularity skorunun 0.630465 olmasi ile de desteklenmektedir. En belirgin topluluklar arasi kopru dugum `asralfotografcilik` olarak gorunmektedir.

## 7. Gorsellestirme

Olusturulan gorseller:

1. Genel ag grafigi: `C:\Users\emirh\OneDrive\Desktop\Project_SNA\docs\sna_project_outputs\figures\01_network_overview.png`
2. Merkezilik degerlerine gore ag grafigi: `C:\Users\emirh\OneDrive\Desktop\Project_SNA\docs\sna_project_outputs\figures\02_betweenness_centrality_network.png`
3. Topluluklara gore renklendirilmis ag grafigi: `C:\Users\emirh\OneDrive\Desktop\Project_SNA\docs\sna_project_outputs\figures\03_louvain_communities.png`
4. Derece dagilimi: `C:\Users\emirh\OneDrive\Desktop\Project_SNA\docs\sna_project_outputs\figures\04_degree_distribution.png`

## 8. Kisa Dayaniklilik Analizi

Dayaniklilik tablosu:

| nodes | edges | components | largest_component_size | density | average_degree | diameter_lcc | scenario |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 389.0 | 6711.0 | 2.0 | 338.0 | 0.0889 | 34.5039 | 6.0 | Baseline |
| 388.0 | 6650.0 | 2.0 | 337.0 | 0.0886 | 34.2784 | 6.0 | Highest degree node removed (annevebebek2025) |
| 388.0 | 6657.0 | 2.0 | 337.0 | 0.0887 | 34.3144 | 6.0 | Highest betweenness node removed (studyconkris) |
| 369.0 | 6015.0 | 2.0 | 318.0 | 0.0886 | 32.6016 | 7.0 | Top 20 betweenness nodes removed |
| 369.0 | 6047.7333 | 2.0 | 320.4 | 0.0891 | 32.779 | 6.4667 | Average of 30 random 20-node removals |

Tek bir en yuksek degree dugumunun cikmasi agi dramatik bicimde parcalamamistir. Buna karsin en yuksek betweenness dugumleri hedefli bicimde cikarildiginda cap degeri `6.0`'den `7.0`'e cikmistir. Rastgele 20 dugum cikarildiginda ortalama cap `6.4667` seviyesinde kalmistir. Bu da agin bagli kalma acisindan dayanikli, fakat kopru dugumler kaybedildiginde ulasim verimliligi acisindan hassas oldugunu gostermektedir.

## 9. Sonuc

Bu agda creator hesaplari konu benzerligine gore belirgin alt topluluklar olusturmaktadir. Bu yapi, urun odakli influencer onerisi yapan sistemin omurgasini olusturur. En onemli dugumler tek bir olcekte degil, farkli merkezilik olcutlerinde farkli roller ustlenmektedir: bazi hesaplar alan otoritesi, bazi hesaplar ise topluluklar arasi koprudur. Ag yapisi yogun ve yuksek kumeleme katsayisina sahiptir; bu da benzer temalara sahip creatorlarin kendi iclerinde guclu kumeleme egilimi gosterdigini dusundurmektedir.

Bu nedenle proje yalnizca urun-kelime eslestirmesi yapan bir yapi degildir. Urun sorgusu once urun sinyallerine ayrilir, ardindan bu sinyaller creator graph uzerindeki merkezilik, topluluk ve kopru olculeri ile birlestirilerek son tavsiye uretilir.

Calismanin temel sinirliliklari sunlardir:

- Ag benzerlik temelli kuruldugu icin gercek takip/friend iliskilerini dogrudan temsil etmez.
- Hashtag verisi paylasimlardan turetildigi icin profilin tum icerik stratejisini tam yansitmayabilir.
- Veri seti belirli hashtag ve profil taramalarina dayanmaktadir; tum Instagram ekosistemini kapsamaz.
