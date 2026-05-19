import io
import re
import unicodedata
from zipfile import ZipFile, ZIP_DEFLATED

import streamlit as st
from PIL import Image, ImageOps, ImageFilter

st.set_page_config(page_title="Shop Pic", page_icon="🖼️", layout="centered")

MAX_FILES = 10
MAX_SIZE_MB = 5
ALLOWED_TYPES = ["jpg", "jpeg", "png"]

CSS = """
<style>
    .stApp { background: #f7f1e8; }
    .block-container { padding-top: 2rem; max-width: 920px; }
    .shop-card {
        background: #ffffff;
        border: 1px solid #e3d6c4;
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 6px 20px rgba(67, 55, 39, 0.08);
        margin-bottom: 18px;
    }
    .shop-title {
        font-size: 34px;
        font-weight: 800;
        color: #2b2926;
        margin-bottom: 2px;
    }
    .shop-subtitle {
        color: #6f6558;
        font-size: 16px;
        margin-bottom: 14px;
    }
    div.stButton > button:first-child {
        background: #c6a15b;
        color: white;
        border: 0;
        border-radius: 12px;
        padding: 0.7rem 1.2rem;
        font-weight: 700;
        width: 100%;
    }
    div.stDownloadButton > button:first-child {
        background: #2f2d2a;
        color: white;
        border: 0;
        border-radius: 12px;
        padding: 0.7rem 1.2rem;
        font-weight: 700;
        width: 100%;
    }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

st.markdown('<div class="shop-title">Shop Pic</div>', unsafe_allow_html=True)
st.markdown('<div class="shop-subtitle">Préparez vos images produits en JPG optimisé, carré et sans métadonnées.</div>', unsafe_allow_html=True)

st.markdown('<div class="shop-card">', unsafe_allow_html=True)
st.write("**1. Ajoutez jusqu’à 10 images carrées**")
uploaded_files = st.file_uploader(
    "Formats acceptés : JPG, JPEG, PNG — 5 Mo maximum par image",
    type=ALLOWED_TYPES,
    accept_multiple_files=True,
)

format_choice = st.radio(
    "2. Choisissez le format final",
    ["PrestaShop — 800 × 800 px", "Amazon — 1200 × 1200 px"],
    horizontal=True,
)
target_size = 800 if format_choice.startswith("PrestaShop") else 1200
st.markdown('</div>', unsafe_allow_html=True)


def clean_filename(name: str) -> str:
    name = name.strip().lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "image-produit"


def human_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / (1024 * 1024):.2f} Mo"
    return f"{num_bytes / 1024:.0f} Ko"


def optimize_image(file, final_name: str, size_px: int):
    original_bytes = file.getvalue()
    original_size = len(original_bytes)

    image = Image.open(io.BytesIO(original_bytes))
    image = ImageOps.exif_transpose(image)

    if image.width != image.height:
        raise ValueError(f"Image non carrée : {image.width} × {image.height} px")

    # Conversion propre vers RGB, fond blanc si PNG transparent.
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        background = Image.new("RGB", image.size, "white")
        rgba = image.convert("RGBA")
        background.paste(rgba, mask=rgba.split()[-1])
        image = background
    else:
        image = image.convert("RGB")

    # Redimensionnement haute qualité.
    image = image.resize((size_px, size_px), Image.Resampling.LANCZOS)

    # Netteté douce, non agressive.
    image = image.filter(ImageFilter.UnsharpMask(radius=1.1, percent=115, threshold=3))

    # Compression intelligente : on cherche un bon poids sans descendre trop bas en qualité.
    best_data = None
    for quality in [92, 90, 88, 86, 84, 82]:
        buffer = io.BytesIO()
        image.save(
            buffer,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=2,
        )
        data = buffer.getvalue()
        best_data = data
        # Objectif raisonnable : 800px <= 280 Ko, 1200px <= 520 Ko si possible.
        target_kb = 280 if size_px == 800 else 520
        if len(data) <= target_kb * 1024:
            break

    final_size = len(best_data)
    reduction = 0 if original_size == 0 else (1 - final_size / original_size) * 100
    output_name = clean_filename(final_name) + ".jpg"
    return output_name, best_data, original_size, final_size, reduction


if uploaded_files:
    if len(uploaded_files) > MAX_FILES:
        st.error(f"Vous avez ajouté {len(uploaded_files)} images. Le maximum est {MAX_FILES}.")
        uploaded_files = uploaded_files[:MAX_FILES]

    st.markdown('<div class="shop-card">', unsafe_allow_html=True)
    st.write("**3. Donnez un nom final à chaque image**")

    names = []
    errors = []
    seen_names = set()

    for i, file in enumerate(uploaded_files, start=1):
        size_mb = len(file.getvalue()) / (1024 * 1024)
        cols = st.columns([1, 2])
        with cols[0]:
            try:
                preview = Image.open(file)
                st.image(preview, caption=file.name, width=130)
                file.seek(0)
            except Exception:
                st.warning("Aperçu impossible")
        with cols[1]:
            default_name = clean_filename(file.name.rsplit(".", 1)[0])
            final_name = st.text_input(f"Nom final image {i}", value=default_name, key=f"name_{i}")
            cleaned = clean_filename(final_name) + ".jpg"
            st.caption(f"Sortie : {cleaned} — poids origine : {human_size(len(file.getvalue()))}")

            if size_mb > MAX_SIZE_MB:
                errors.append(f"{file.name} dépasse 5 Mo.")
            if cleaned in seen_names:
                errors.append(f"Nom en double : {cleaned}")
            seen_names.add(cleaned)
            names.append(final_name)

    st.markdown('</div>', unsafe_allow_html=True)

    if errors:
        for err in errors:
            st.error(err)

    if st.button("Générer les images JPG optimisées", disabled=bool(errors)):
        results = []
        zip_buffer = io.BytesIO()
        total_before = 0
        total_after = 0

        with ZipFile(zip_buffer, "w", ZIP_DEFLATED) as zip_file:
            for file, name in zip(uploaded_files, names):
                try:
                    out_name, data, before, after, reduction = optimize_image(file, name, target_size)
                    zip_file.writestr(out_name, data)
                    total_before += before
                    total_after += after
                    results.append((out_name, before, after, reduction, None))
                except Exception as exc:
                    results.append((file.name, 0, 0, 0, str(exc)))

        successful = [r for r in results if r[4] is None]
        failed = [r for r in results if r[4] is not None]

        if successful:
            average_reduction = 0 if total_before == 0 else (1 - total_after / total_before) * 100
            st.success(
                f"{len(successful)} image(s) générée(s) avec succès. "
                f"Poids avant : {human_size(total_before)} — poids après : {human_size(total_after)} — "
                f"réduction : {average_reduction:.1f} %."
            )

            for out_name, before, after, reduction, _ in successful:
                st.write(f"✅ **{out_name}** — {human_size(before)} → {human_size(after)} — réduction {reduction:.1f} %")

            st.download_button(
                "Télécharger les images optimisées",
                data=zip_buffer.getvalue(),
                file_name="images-produits.zip",
                mime="application/zip",
            )

        for name, _, _, _, error in failed:
            st.error(f"{name} refusée : {error}")
else:
    st.info("Ajoutez vos images pour commencer.")

st.caption("Shop Pic — JPG optimisé, carré obligatoire, métadonnées supprimées.")
