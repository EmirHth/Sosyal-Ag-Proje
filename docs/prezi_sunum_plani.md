# 7 Slaytlik Prezi Sunum Plani

## Sunum Basligi
**Sosyal Ag Analizi Tabanli Urun-Influencer Esleme Sistemi**

## Genel Kurgu
Bu sunum 7 ana frame olarak tasarlanmistir. Prezi'de merkezde kapak yer alir; diger 6 frame etrafina yerlestirilir. Zoom akisi problemden uygulamaya dogru ilerler.

## 7 Frame Zoom Akisi
1. Kapak ve problem
2. Veri seti + urun sinyali / kategori cikarimi
3. Ag modelleme + temel ag olcutleri
4. Merkezilik analizi
5. Topluluk + dayaniklilik analizi
6. Urun odakli onerme mekanizmasi
7. Ornek sorgular + sonuc

---

## Frame 1 - Kapak ve Problem
**Baslik:** Sosyal Ag Analizi Tabanli Urun-Influencer Esleme Sistemi

**Kisa metin:**
- Influencer secimi sadece takipci sayisina gore yapilmamalidir.
- Bazi urunlerde alan otoritesi, bazilarinda ise kopru rolunde creator gerekir.
- Bu nedenle creatorlar arasi benzerlik agi kurulmustur.

**Arastirma sorusu:**
Bir urun sorgusu girildiginde, sistem hangi influencer'i alan otoritesi, etkilesim ve gerekirse kopru rolu uzerinden one cikarmalidir?

**Konusma metni:**
Bu projede sosyal ag analizini sadece olcum yapmak icin degil, urune gore daha mantikli influencer secmek icin kullandik.

**Gorsel:**
- [analiz mantigi](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/excalidraw/exports/04_analiz_ve_kullanim_mantigi.png)

---

## Frame 2 - Veri Seti ve Urun Sinyali
**Baslik:** Veri Seti ve Urun Sinyali / Kategori Cikarimi

**Kisa metin:**
- Veri kaynagi: Instagram profil ve hashtag taramasi
- Dugum: creator / influencer hesabi
- Kenar: kategori + hashtag benzerligi
- Dugum sayisi: 389
- Kenar sayisi: 6711

**Urun sinyali mantigi:**
- Sorgu normalize edilir
- Keyword ve ifadeler kategori sozlugu ile eslestirilir
- Yardimci sinyaller puanlanir
- En uygun kategori veya kategori kombinasyonu secilir

**Ornekler:**
- `kadin yuz serumu` -> `guzellik_kozmetik`
- `spor matarasi` -> `fitness_saglik`, `yemek_mutfak`
- `kamp termosu` -> `seyahat_gezi`, `yemek_mutfak`

**Konusma metni:**
Bu katman graph degildir; urunun ne istedigini anlamaya yarar. Keywordler, kullanim baglami ve urun tipi birlikte okunur; asil influencer secimi daha sonra creator graph uzerinde yapilir.

**Gorsel:**
- [veri hazirlama](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/excalidraw/exports/02_graf_icin_veri_hazirlama.png)

---

## Frame 3 - Ag Modelleme ve Temel Olcutler
**Baslik:** Graph Modeli ve Temel Ag Olcutleri

**Kisa metin:**
**G = (V, E)**

- V: creator hesaplari
- E: iki creator arasindaki benzerlik kenarlari
- Ag tipi: yonlusuz ve agirlikli
- Yogunluk: 0.0889
- Ortalama derece: 34.50
- Kumeleme katsayisi: 0.6899
- Cap: 6

**Yorum:**
Ag orta yogunlukta, yuksek kumeleme egilimli ve kompakt cekirdek yapida bir creator omurgasi sunuyor.

**Konusma metni:**
Bu ag takip agi degil, similarity graph. Yani creatorlar arasindaki icerik yakinligini yapi olarak modelliyoruz.

**Gorseller:**
- [genel ag](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/05_network_overview_polished.png)
- [derece dagilimi](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/08_degree_distribution_polished.png)

---

## Frame 4 - Merkezilik Analizi
**Baslik:** Merkezilik Analizi

**Kisa metin:**
- Yontem: NetworkX merkezilik olcutleri
- `annevebebek2025` degree ve PageRank'te one cikti; bu dugum anne-bebek ekseninde cok baglantili ve otorite benzeri bir merkezdir.
- `emine.bites` eigenvector tarafinda one cikti; yani yalnizca baglantili degil, etkili dugumlere de bagli bir creator konumundadir.
- `itssyamaan` closeness tarafinda one cikti; cekirdek ag icinde diger dugumlere daha hizli ulasabilmektedir.
- `studyconkris` betweenness'te en yuksek dugumlerden biridir; egitim, ev_yasam ve evcil_hayvan eksenleri arasinda yapisal kopru rolundedir.

**Konusma metni:**
Bizim projede Degree, Eigenvector ve PageRank ayni rolu gostermiyor; ama birlikte okunduklarinda hangi creatorlarin alan icinde guclu otorite oldugu anlasiliyor. Betweenness ise farkli topluluklari baglayan creatorlari ortaya cikariyor. Bu fark, oneride authority ve bridge modlarini ayirmamizi sagladi.

**Gorseller:**
- [merkezilik karsilastirma](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/10_top_centrality_comparison.png)
- [kopru dugumler](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/16_bridge_focus_compact.png)

---

## Frame 5 - Topluluk ve Dayaniklilik
**Baslik:** Topluluklar ve Ag Dayanikliligi

**Kisa metin:**
- Yontem: Louvain community detection
- Topluluk sayisi: 8
- Modularity: 0.630465
- En buyuk topluluk: 69 dugum
- Topluluklar otomotiv, yemek_mutfak, egitim_kariyer ve anne_bebek gibi tema eksenlerinde dogal olarak ayrismistir.

**Dayaniklilik bulgusu:**
- Tek bir yuksek degree dugumu cikinca ag dramatik sekilde parcalanmadi.
- Ancak yuksek betweenness dugumleri hedefli cikarildiginda diameter 6'dan 7'ye cikti.

**Konusma metni:**
Louvain sonucu, creatorlarin rastgele degil anlamli tema gruplari halinde toplandigini gosterdi. Dayaniklilik analizi ise bu topluluklari birbirine baglayan kopru dugumlerin kaybi halinde agin erisim verimliliginin bozuldugunu ortaya koydu.

**Gorseller:**
- [topluluklar](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/07_louvain_communities_polished.png)
- [meta graph](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/13_community_meta_graph.png)
- [dayaniklilik](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/14_robustness_comparison.png)

---

## Frame 6 - Urun Odakli Onerme Mekanizmasi
**Baslik:** Urun Girisi -> Influencer Onerisi

**Kisa metin:**
Sistem iki katmanda calisir:

1. **Urun anlama katmani**
- keyword
- kategori sinyali
- kullanim baglami

2. **Graph tabanli secim katmani**
- relevance_score
- authority_score
- bridge_score
- engagement_score
- follower_score

**Senaryo farki:**
- `authority`: tek kategoriye yakin urunler
- `bridge`: cok kategorili veya farkli topluluklari baglayan urunler

**Konusma metni:**
Yani urun sinyali katmani talebi tanimlar, creator graph ise bu talebi yapisal olarak en uygun hesaplarla eslestirir. Projenin asil farki, sosyal ag analizini dogrudan onerme mekanizmasina baglamasidir.

**Gorsel:**
- [gercek graph modeli](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/excalidraw/exports/03_gercek_graph_modeli.png)

---

## Frame 7 - Ornek Ciktilar ve Sonuc
**Baslik:** Ornek Sorgular ve Sonuc

**Kisa metin:**
Ornek sorgular:
- `kadin yuz serumu`
- `spor matarasi`
- `kamp termosu`

**Mesaj:**
- Net urunlerde authority modu one cikar
- Yan kategori sinyali tasiyan urunlerde bridge / topluluk baglantilari deger kazanir

**Sonuc:**
Bu proje sosyal ag analizi isterlerini karsilarken, bu analizleri urune gore mantikli influencer secen uygulamali bir sisteme donusturmektedir.

**Konusma metni:**
Boylece proje sadece raporluk bir graph analizi degil; urun bazli karar uretebilen graph tabanli bir onerme sistemine donusmus oldu.

**Gorsel:**
- [ornek oneriler](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/15_recommendation_examples.png)

---

## Prezi Yerlesim Onerisi
- Frame 1 merkeze
- Frame 2 sol ust
- Frame 3 sag ust
- Frame 4 orta sol
- Frame 5 orta sag
- Frame 6 alt sol
- Frame 7 alt sag

## Finalde Kullanilacak En Guclu Gorseller
- [05_network_overview_polished.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/05_network_overview_polished.png)
- [07_louvain_communities_polished.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/07_louvain_communities_polished.png)
- [10_top_centrality_comparison.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/10_top_centrality_comparison.png)
- [13_community_meta_graph.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/13_community_meta_graph.png)
- [14_robustness_comparison.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/14_robustness_comparison.png)
- [15_recommendation_examples.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/15_recommendation_examples.png)
- [16_bridge_focus_compact.png](/C:/Users/emirh/OneDrive/Desktop/Project_SNA/docs/sna_project_outputs/figures/16_bridge_focus_compact.png)
