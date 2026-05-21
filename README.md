# Sosyal Ag Analizi Tabanli Urun-Influencer Esleme Sistemi

Bu repo, influencer hesaplari arasindaki kategori ve hashtag benzerliklerinden uretilen agirlikli bir creator graph uzerinde calisan urun odakli influencer onerme sistemini icerir.

Sistem iki ana katmandan olusur:

- Urun sinyali ve kategori cikarimi: Girilen urun sorgusu normalize edilir, kategori ve kullanim baglami sinyalleri cikarilir.
- Graph tabanli influencer secimi: Creator graph uzerinde authority, bridge, engagement ve relevance sinyalleri birlestirilerek en uygun adaylar onerilir.

Proje kapsaminda:

- creator similarity graph kurulmustur
- temel ag olcutleri hesaplanmistir
- degree, betweenness, closeness, eigenvector ve PageRank merkezilikleri incelenmistir
- Louvain yontemi ile topluluk analizi yapilmistir
- dayaniklilik analizi uygulanmistir
- urun sorgusuna gore influencer onerisi ureten uygulamali bir sistem gelistirilmistir

Proje, Emirhan Akyuzlu ve Ahmet Selcuk Kirimli'nin katkilarıyla gelistirilmistir.

## Repo Icerigi

- `sna_project.py`: Ag kurma, analiz, tablo ve gorsel uretimi
- `taxonomy.py`: Urun sinyali ve kategori cikarimi
- `recommender.py`: Graph tabanli influencer onerme mantigi
- `app.py`: Uygulama giris noktasi
- `docs/`: Rapor, notebook, gorseller ve ciktilar
- `data/`: Veri seti ve taksonomi dosyalari

## Ana Ciktilar

- `docs/sna_project_report.docx`
- `docs/sna_project_report.md`
- `docs/sna_creator_network.ipynb`
- `docs/sna_project_outputs/figures/`
- `docs/sna_project_outputs/tables/`

## Ozet

Bu sistem, sadece takipci sayisina dayali bir secim yapmak yerine, urun ile creator uyumunu ve ag yapisindaki yapisal rolleri birlikte degerlendirir. Boylece hem alan otoritesi yuksek hem de gerektiginde farkli topluluklar arasinda kopru kurabilen influencerlar onerilebilir.
