
import io
import re
import unicodedata
from zipfile import ZipFile

import streamlit as st
from PIL import Image, ImageOps, ImageFilter

st.set_page_config(
    page_title="Shop Pic",
    page_icon="🖼️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

CUSTOM_CSS = """
<style>
#MainMenu, footer, header {visibility: hidden;}
.stApp {
    background: linear-gradient(180deg, #fbf7f0 0%, #ffffff 42%, #fbf7f0 100%);
}
.block-container {
    padding-top: 2rem;
    max-width: 1100px;
}
.hero {
    background: #ffffff;
    border: 1px solid #eadfcb;
    border-radius: 28px;
    padding: 28px 30px;
    box-shadow: 0 18px 45px rgba(69, 52, 27, 0.08);
    margin-bottom: 22px;
}
.hero-title {
    font-size: 42px;
    line-height: 1.05;
    font-weight: 800;
    color: #25211c;
    margin: 0;
}
.hero-subtitle {
    color: #6f6251;
    font-size: 17px;
    margin-top: 10px;
}
.badge {
    display: inline-block;
    background: #f1dfb8;
    color: #4c3b1d;
    border-radius: 999px;
    padding: 7px 12px;
    font-size: 13px;
    font-weight: 700;
    margin-right: 8px;
}
.card {
    background: #ffffff;
    border: 1px solid #eadfcb;
    border-radius: 24px;
    padding: 22px;
    box-shadow: 0 12px 30px rgba(69, 52, 27, 0.06);
    margin-bottom: 18px;
}
.card h3 {
    margin-top: 0;
    color: #25211c;
}
.small-muted {
    color: #7b705f;
    font-size: 14px;
}
.result-ok {
    background: #eef8ef;
    border: 1px solid #c9e8cd;
    color: #225b2d;
    border-radius: 18px;
    padding: 16px;
    margin-top: 14px;
}
.result-error {
    background: #fff0f0;
    border: 1px solid #f0c1c1;
    color: #7a1f1f;
    border-radius: 18px;
    padding: 16px;
    margin-top: 14px;
}
div.stButton > button:first-child {
    background: linear-gradient(135deg, #caa24a, #e4c46f);
    color: #211a0d;
    border: none;
    border-radius: 16px;
    padding: 0.7rem 1rem;
    font-weight: 800;
    box-shadow: 0 8px 18px rgba(139, 103, 28, .22);
}
div.stDownloadButton > button:first-child {
    background: #26211b;
    color: white;
    border: none;
    border-radius: 16px;
    padding: 0.7rem 1rem;
    font-weight: 800;
}
.stRadio > div {
    background: #fffaf0;
    border: 1px solid #eadfcb;
    border-radius: 18px;
    padding: 12px;
}
[data-testid="stFileUploader"] {
    background: #fffaf0;
    border: 1px dashed #d8b65e;
    border-radius: 22px;
    padding: 12px;
}
input {
    border-radius: 12px !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

MAX_FILES = 10
MAX_SIZE_MB = 5
JPEG_QUALITY = 88


def clean_filename(name: str) -> str:
    name = name.strip().lower()
    name = unicodedata.normalize("NFD", name)
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "image-produit"


def format_size(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024*1024):.2f} Mo"
    return f"{size / 1024:.0f} Ko"


def process_image(file_bytes: bytes, target_size: int):
    original_size = len(file_bytes)
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)

    width, height = img.size
    if width != height:
        raise ValueError(f"Image non carrée : {width}×{height}px")

    img = img.convert("RGB")
    img = img.resize((target_size, target_size), Image.Resampling.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3))

    out = io.BytesIO()
    img.save(
        out,
        format="JPEG",
        quality=JPEG_QUALITY,
        optimize=True,
        progressive=True,
        subsampling=0,
    )
    final = out.getvalue()
    reduction = 100 - (len(final) / original_size * 100)
    return final, original_size, len(final), reduction


st.markdown(
    """
<div class="hero">
  <div><span class="badge">JPG optimisé</span><span class="badge">800×800 / 1200×1200</span><span class="badge">Métadonnées supprimées</span></div>
  <h1 class="hero-title">Shop Pic</h1>
  <div class="hero-subtitle">Préparez vos images produits propres, légères et prêtes pour PrestaShop ou Amazon.</div>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([1, 1], gap="large")

with left:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("1. Ajouter les images")
    uploaded_files = st.file_uploader(
        "JPG, JPEG ou PNG — maximum 10 images, 5 Mo par image",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        label_visibility="visible",
    )
    st.markdown("<p class='small-muted'>Les images non carrées sont refusées pour éviter les déformations.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("2. Choisir le format")
    mode = st.radio(
        "Format de sortie",
        ["PrestaShop — 800×800 px", "Amazon — 1200×1200 px"],
        horizontal=False,
    )
    target_size = 800 if mode.startswith("PrestaShop") else 1200
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("3. Nommer les fichiers")
    st.markdown("<p class='small-muted'>Écrivez un nom par image. Le .jpg est ajouté automatiquement.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

if uploaded_files:
    files = uploaded_files[:MAX_FILES]
    if len(uploaded_files) > MAX_FILES:
        st.warning(f"Maximum {MAX_FILES} images. Seules les {MAX_FILES} premières seront prises en compte.")

    names = []
    preview_cols = st.columns(2)
    for i, f in enumerate(files):
        with preview_cols[i % 2]:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.image(f, caption=f.name, use_container_width=True)
            default_name = Path(f.name).stem
            name = st.text_input(
                f"Nom final image {i+1}",
                value=clean_filename(default_name),
                key=f"name_{i}",
            )
            names.append(name)
            st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Générer les images optimisées", use_container_width=True):
        used_names = set()
        results = []
        errors = []
        zip_buffer = io.BytesIO()

        with ZipFile(zip_buffer, "w") as zip_file:
            for i, f in enumerate(files):
                try:
                    if f.size > MAX_SIZE_MB * 1024 * 1024:
                        raise ValueError(f"Fichier supérieur à {MAX_SIZE_MB} Mo")

                    final_name = clean_filename(names[i]) + ".jpg"
                    if final_name in used_names:
                        raise ValueError(f"Nom en double : {final_name}")
                    used_names.add(final_name)

                    output, before, after, reduction = process_image(f.getvalue(), target_size)
                    zip_file.writestr(final_name, output)
                    results.append((final_name, before, after, reduction))
                except Exception as e:
                    errors.append((f.name, str(e)))

        if results:
            total_before = sum(r[1] for r in results)
            total_after = sum(r[2] for r in results)
            total_reduction = 100 - (total_after / total_before * 100)

            st.markdown(
                f"""
<div class="result-ok">
<strong>{len(results)} image(s) générée(s) avec succès.</strong><br>
Poids avant : {format_size(total_before)}<br>
Poids après : {format_size(total_after)}<br>
Réduction moyenne : {total_reduction:.1f} %
</div>
""",
                unsafe_allow_html=True,
            )

            st.download_button(
                "Télécharger le dossier images-produits.zip",
                data=zip_buffer.getvalue(),
                file_name="images-produits.zip",
                mime="application/zip",
                use_container_width=True,
            )

            st.markdown("### Détail")
            for filename, before, after, reduction in results:
                st.write(f"**{filename}** — {format_size(before)} → {format_size(after)} — réduction {reduction:.1f} %")

        if errors:
            st.markdown("<div class='result-error'><strong>Images refusées :</strong><br>" + "<br>".join([f"{n} — {e}" for n, e in errors]) + "</div>", unsafe_allow_html=True)
else:
    st.info("Ajoutez une ou plusieurs images pour commencer.")
