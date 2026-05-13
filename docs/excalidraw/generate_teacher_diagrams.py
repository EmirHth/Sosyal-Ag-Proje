from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "exports"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_REGULAR = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(FONT_BOLD if bold else FONT_REGULAR), size=size)
    except Exception:
        return ImageFont.load_default()


def rounded(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], fill: str, outline: str, width: int = 3, radius: int = 24) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, width: int, font: ImageFont.ImageFont) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}".strip()
            if draw.textlength(trial, font=font) <= width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines


def draw_paragraph(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: str = "#334155",
    line_spacing: int = 8,
) -> int:
    x, y, w, h = box
    current_y = y
    for line in wrap_text(draw, text, w, font):
        draw.text((x, current_y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, current_y), line or " ", font=font)
        current_y += (bbox[3] - bbox[1]) + line_spacing
        if current_y > y + h:
            break
    return current_y


def title_canvas(title: str, subtitle: str, size: tuple[int, int], bg: str) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", size, bg)
    draw = ImageDraw.Draw(image)
    draw.text((70, 38), title, font=load_font(44, bold=True), fill="#0f172a")
    draw_paragraph(draw, subtitle, (70, 100, size[0] - 140, 80), load_font(24), fill="#334155")
    return image, draw


def section_tag(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, fill: str) -> None:
    rounded(draw, (x, y, x + 360, y + 56), fill, fill, width=1, radius=20)
    draw.text((x + 18, y + 12), text, font=load_font(26, bold=True), fill="white")


def bullet_list(
    draw: ImageDraw.ImageDraw,
    items: list[str],
    origin: tuple[int, int],
    width: int,
    font: ImageFont.ImageFont,
    bullet_fill: str = "#ea580c",
    text_fill: str = "#334155",
    row_gap: int = 10,
) -> int:
    x, y = origin
    current_y = y
    for item in items:
        draw.ellipse((x, current_y + 8, x + 12, current_y + 20), fill=bullet_fill)
        end_y = draw_paragraph(draw, item, (x + 26, current_y, width - 26, 120), font, fill=text_fill)
        current_y = end_y + row_gap
    return current_y


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int], fill: str = "#64748b", width: int = 6) -> None:
    import math

    draw.line([start, end], fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    head = 18
    p1 = (end[0] - head * math.cos(angle - math.pi / 6), end[1] - head * math.sin(angle - math.pi / 6))
    p2 = (end[0] - head * math.cos(angle + math.pi / 6), end[1] - head * math.sin(angle + math.pi / 6))
    draw.polygon([end, p1, p2], fill=fill)


def box(draw: ImageDraw.ImageDraw, bounds: tuple[int, int, int, int], title: str, body: str, fill: str, outline: str) -> None:
    rounded(draw, bounds, fill, outline, width=3, radius=24)
    x1, y1, x2, _ = bounds
    draw.text((x1 + 20, y1 + 16), title, font=load_font(29, bold=True), fill="#0f172a")
    draw_paragraph(draw, body, (x1 + 20, y1 + 62, x2 - x1 - 40, 220), load_font(23), fill="#334155")


def code_card(draw: ImageDraw.ImageDraw, bounds: tuple[int, int, int, int], title: str, lines: list[str]) -> None:
    rounded(draw, bounds, "#111827", "#0f172a", width=2, radius=22)
    x1, y1, x2, _ = bounds
    draw.text((x1 + 18, y1 + 14), title, font=load_font(26, bold=True), fill="#f8fafc")
    draw_paragraph(draw, "\n".join(lines), (x1 + 18, y1 + 56, x2 - x1 - 36, 220), load_font(21), fill="#cbd5e1", line_spacing=6)


def diagram_1() -> None:
    image, draw = title_canvas(
        "Proje Omurgasi: Urun Sorgusundan Influencer Onerisine",
        "Bu gorsel, projenin yalnizca kelime eslestirmesi olmadigini; urun sinyallerini creator graph ile birlestiren sosyal ag tabanli karar sistemi oldugunu gosterir.",
        (2200, 1500),
        "#f8f5ef",
    )

    section_tag(draw, 70, 180, "1. Uygulama Akisi", "#c96f4a")
    box(
        draw,
        (70, 250, 470, 620),
        "Urun Girdisi",
        "Kullanici bir urun sorgusu girer.\n\nOrnekler:\n- kadin yuz serumu\n- pipetli bardak\n- anne bebek ve cilt bakim urunu",
        "#fff7ed",
        "#fb923c",
    )
    box(
        draw,
        (540, 250, 980, 620),
        "Urun Sinyalleri",
        "taxonomy.py urunu tek bir kelime gibi degil, urun sinyalleri olarak yorumlar.\n\n- kategori niyeti\n- hedef kullanici\n- kullanim baglami\n- urun tipi",
        "#eff6ff",
        "#60a5fa",
    )
    box(
        draw,
        (1050, 250, 1540, 620),
        "Creator Graph",
        "recommender.py, creator graph icindeki yapisal bilgileri kullanir.\n\n- authority_score\n- bridge_score\n- engagement_score\n- category fit",
        "#ecfeff",
        "#14b8a6",
    )
    box(
        draw,
        (1610, 250, 2100, 620),
        "Top-K Oneri",
        "Son adimda en uygun influencer listesi uretilir.\n\nCikti:\n- username\n- neden secildi\n- skor dagilimi\n- alan otoritesi veya kopru rolu",
        "#f0fdf4",
        "#22c55e",
    )
    arrow(draw, (470, 435), (540, 435))
    arrow(draw, (980, 435), (1050, 435))
    arrow(draw, (1540, 435), (1610, 435))

    section_tag(draw, 70, 700, "2. Neden Sosyal Ag Projesi?", "#2563eb")
    rounded(draw, (70, 770, 2100, 980), "#ffffff", "#94a3b8", width=2, radius=24)
    bullet_list(
        draw,
        [
            "Dugumler influencer / creator hesaplaridir.",
            "Kenarlar kategori ve hashtag benzerliginden uretilen agirlikli iliskilerdir.",
            "Merkezilik, topluluk analizi ve dayaniklilik dogrudan bu creator graph uzerinde hesaplanir.",
            "Urun sorgusu sadece karar baglamini verir; son secim graph metrikleriyle guclendirilir.",
        ],
        (105, 810),
        1880,
        load_font(25),
        bullet_fill="#2563eb",
    )

    section_tag(draw, 70, 1040, "3. Karar Mantigi", "#059669")
    box(
        draw,
        (70, 1110, 1010, 1400),
        "Authority Modu",
        "Tek baskin niyetli urunlerde secilir.\n\nOdak:\n- kategori uyumu\n- PageRank / authority_score\n- etkilesim\n\nOrnek: kadin yuz serumu",
        "#ecfdf5",
        "#34d399",
    )
    box(
        draw,
        (1090, 1110, 2100, 1400),
        "Bridge Modu",
        "Birden fazla anlamli kategori ayni anda guclu sinyal verirse secilir.\n\nOdak:\n- kategori uyumu\n- betweenness tabanli bridge_score\n- topluluklar arasi gecis rolu\n\nOrnek: cilt bakimi + anne bebek ekseni",
        "#fff7ed",
        "#f59e0b",
    )

    image.save(OUT_DIR / "01_veri_yapisi_ve_ozellikler.png")


def diagram_2() -> None:
    image, draw = title_canvas(
        "Creator Graph Nasil Kuruluyor?",
        "Bu diyagram, analiz edilen ana agin heterojen urun grafi degil; creatorlar arasindaki benzerlik omurgasi oldugunu netlestirir.",
        (2200, 1500),
        "#f4f7fb",
    )

    section_tag(draw, 70, 180, "1. Girdi Verisi", "#9333ea")
    box(
        draw,
        (70, 250, 700, 720),
        "Clean Creator Dataset",
        "Temel veri dosyasi:\nclean_creator_dataset.csv\n\nHer satirda ozet bilgiler bulunur:\n- username\n- followers\n- avg_likes\n- avg_comments\n- categories\n- top hashtags",
        "#faf5ff",
        "#a855f7",
    )
    code_card(
        draw,
        (110, 500, 660, 690),
        "Python ile yukleme",
        [
            "import pandas as pd",
            "df = pd.read_csv(",
            "    'data/processed/clean_creator_dataset.csv'",
            ")",
            "print(df[['username', 'categories']].head())",
        ],
    )

    section_tag(draw, 785, 180, "2. Dugum ve Kenarlar", "#0ea5e9")
    box(
        draw,
        (785, 250, 1430, 720),
        "Graph Modeli",
        "Dugum = tek bir creator hesabi\nKenar = iki creator arasindaki icerik benzerligi\n\nAg turu:\n- yonlusuz\n- agirlikli\n- creator similarity backbone",
        "#f0f9ff",
        "#38bdf8",
    )
    box(
        draw,
        (785, 760, 1430, 1230),
        "Kenar Agirligi",
        "Agirlik, kategori ve hashtag benzerliginden uretilir.\n\nweight = 0.75 x category similarity\n       + 0.25 x hashtag similarity\n\nEsik degeri alti zayif iliskiler agdan dislanir.",
        "#ecfeff",
        "#22d3ee",
    )

    section_tag(draw, 1515, 180, "3. Uretilen Ciktilar", "#16a34a")
    box(
        draw,
        (1515, 250, 2100, 720),
        "Ag Ciktilari",
        "sna_project.py otomatik olarak sunlari uretir:\n- node_list.csv\n- edge_list.csv\n- adjacency_matrix.csv\n- creator_similarity_graph.graphml\n- merkeziyet ve topluluk tablolari",
        "#f0fdf4",
        "#4ade80",
    )
    code_card(
        draw,
        (1550, 790, 2060, 980),
        "Calistirma komutu",
        [
            "python sna_project.py",
            "",
            "Cikti klasoru:",
            "docs/sna_project_outputs/",
        ],
    )
    box(
        draw,
        (1515, 1030, 2100, 1290),
        "Neden Bu Model?",
        "Cunku elimizde dogrudan urun-performans kampanya grafi yok. En temiz ve savunulabilir ag, creatorlar arasi benzerlik omurgasidir. Urun sorgusu sonradan bu ag ustunde karar baglami olarak kullanilir.",
        "#ffffff",
        "#86efac",
    )

    arrow(draw, (700, 485), (785, 485))
    arrow(draw, (1430, 485), (1515, 485))

    image.save(OUT_DIR / "02_graf_icin_veri_hazirlama.png")


def diagram_3() -> None:
    image, draw = title_canvas(
        "Ag Analizi ve Oneri Mantigi",
        "Bu gorsel, merkezilik ve topluluk analizlerinin rapor icin ek bilgi degil; onerinin karar mekanizmasi oldugunu aciklar.",
        (2200, 1500),
        "#fafaf9",
    )

    section_tag(draw, 70, 180, "1. Temel Ag Olcutleri", "#e11d48")
    box(
        draw,
        (70, 250, 700, 690),
        "Sayisal Omurga",
        "Guncel ag degerleri:\n- 389 dugum\n- 6711 kenar\n- yogunluk 0.0889\n- cap 6\n- 8 topluluk\n- modularity 0.630465",
        "#fff1f2",
        "#fb7185",
    )
    box(
        draw,
        (70, 740, 700, 1290),
        "Ne Anlatiyor?",
        "Ag orta yogunlukta ve belirgin topluluklara ayriliyor.\n\nBu da ayni alanda ureten creatorlarin dogal kumeler olusturdugunu, bazi hesaplarin da bu kumeler arasinda kopru oldugunu gosteriyor.",
        "#ffffff",
        "#fda4af",
    )

    section_tag(draw, 790, 180, "2. Merkezilik Rolleri", "#2563eb")
    box(
        draw,
        (790, 250, 1430, 520),
        "Authority / Otorite",
        "PageRank ve weighted degree benzeri olculer kullanilir.\n\nSoru: Bu alanda genel olarak guclu ve merkezi hesap kim?",
        "#eff6ff",
        "#60a5fa",
    )
    box(
        draw,
        (790, 560, 1430, 830),
        "Bridge / Kopru",
        "Betweenness centrality kullanilir.\n\nSoru: Farkli topluluklar arasinda gecis saglayan hesap kim?",
        "#eff6ff",
        "#60a5fa",
    )
    box(
        draw,
        (790, 870, 1430, 1140),
        "Topluluk Analizi",
        "Louvain ile dogal niş alanlar bulunur.\n\nSoru: Hangi creatorlar benzer tema gruplarinda toplanmis?",
        "#eff6ff",
        "#60a5fa",
    )
    box(
        draw,
        (790, 1180, 1430, 1400),
        "Dayaniklilik",
        "Hedefli dugum cikarma ile kopru kaybi olursa ag ne kadar bozuluyor?\n\nBu analiz betweenness dugumlerinin ne kadar kritik oldugunu destekler.",
        "#eff6ff",
        "#60a5fa",
    )

    section_tag(draw, 1515, 180, "3. Oneri Skoru", "#16a34a")
    box(
        draw,
        (1515, 250, 2100, 600),
        "Authority Senaryosu",
        "Skor daha cok su eksende kurulur:\n- relevance\n- category fit\n- authority_score\n- engagement_score\n\nTek kategori urunlerde kullanilir.",
        "#f0fdf4",
        "#4ade80",
    )
    box(
        draw,
        (1515, 660, 2100, 1010),
        "Bridge Senaryosu",
        "Skor daha cok su eksende kurulur:\n- relevance\n- category fit\n- bridge_score\n- authority_score\n\nCok eksenli urunlerde topluluklar arasi gecis rolune bakilir.",
        "#fff7ed",
        "#fb923c",
    )
    code_card(
        draw,
        (1545, 1080, 2065, 1290),
        "Kisa Python izi",
        [
            "betweenness = nx.betweenness_centrality(",
            "    creator_graph, weight='distance'",
            ")",
            "pagerank = nx.pagerank(",
            "    creator_graph, weight='weight'",
            ")",
        ],
    )

    image.save(OUT_DIR / "03_gercek_graph_modeli.png")


def diagram_4() -> None:
    image, draw = title_canvas(
        "Teslim Yapisi: Kod, Rapor, Notebook ve Gorseller",
        "Bu son gorsel, hocaya teslim edilen klasorde hangi dosyanin ne ise yaradigini ve Python kodunun projenin merkezinde oldugunu ozetler.",
        (2200, 1500),
        "#f8fafc",
    )

    section_tag(draw, 70, 180, "1. Ana Python Dosyalari", "#0f766e")
    box(
        draw,
        (70, 250, 1020, 780),
        "Proje Kodlari",
        "sna_project.py\nAgi kurar, metrikleri hesaplar, gorselleri ve raporu uretir.\n\nrecommender.py\nUrun sorgusundan sonra graph metrikleriyle influencer siralar.\n\ntaxonomy.py\nUrun sinyallerini kategori, baglam ve urun tipine donusturur.\n\napp.py\nWeb arayuzunu calistirir.",
        "#ecfeff",
        "#14b8a6",
    )
    code_card(
        draw,
        (110, 520, 960, 730),
        "Ornek calistirma",
        [
            "python sna_project.py",
            "python app.py",
            "",
            "# urun sorgusu",
            "recommend_influencers_from_dataset(",
            "    'kadin yuz serumu'",
            ")",
        ],
    )

    section_tag(draw, 1110, 180, "2. Teslim Dosyalari", "#7c3aed")
    box(
        draw,
        (1110, 250, 2100, 780),
        "Uretilen Dosyalar",
        "docs/sna_project_report.md\nYazili rapor\n\ndocs/sna_creator_network.ipynb\nKod + aciklama notebook'u\n\ndocs/sna_project_outputs/figures\nAg gorselleri\n\ndocs/sna_project_outputs/tables\nCSV ve metrik ciktilari",
        "#faf5ff",
        "#a78bfa",
    )

    section_tag(draw, 70, 860, "3. Sunumda Soylenecek Oz", "#dc2626")
    rounded(draw, (70, 930, 2100, 1280), "#ffffff", "#fca5a5", width=2, radius=26)
    bullet_list(
        draw,
        [
            "Bu proje basit bir urun-kelime eslestirmesi degildir.",
            "Once creatorlar arasinda agirlikli bir sosyal ag kurulmustur.",
            "Merkezilik, topluluk ve dayaniklilik analizleri bu graph uzerinde hesaplanmistir.",
            "Urun sorgusu ise bu ag ustunde karar baglami olusturur ve en uygun influencer graph olculeriyle secilir.",
        ],
        (110, 975),
        1880,
        load_font(27),
        bullet_fill="#dc2626",
    )

    section_tag(draw, 70, 1330, "4. Kisa Sonuc", "#1d4ed8")
    rounded(draw, (70, 1390, 2100, 1460), "#dbeafe", "#60a5fa", width=2, radius=18)
    draw_paragraph(
        draw,
        "En guvenli anlatim: Urun odakli influencer onerisi yapan, creator similarity graph uzerine kurulu bir sosyal ag analizi projesi.",
        (100, 1407, 1940, 40),
        load_font(25, bold=True),
        fill="#1e3a8a",
    )

    image.save(OUT_DIR / "04_analiz_ve_kullanim_mantigi.png")


if __name__ == "__main__":
    diagram_1()
    diagram_2()
    diagram_3()
    diagram_4()
