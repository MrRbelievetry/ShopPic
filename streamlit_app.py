
import io
import re
import unicodedata
from pathlib import Path

import streamlit as st
from PIL import Image, ImageOps, ImageFilter

st.set_page_config(
    page_title="Shop Pic",
    page_icon="🖼️",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
#MainMenu, footer, header {visibility:hidden;}

.stApp {
    background:#f6f1e8;
}

.block-container{
    max-width:980px;
    padding-top:1.4rem;
}

.hero{
    background:white;
    border:1px solid #dfcfad;
    border-radius:24px;
    padding:28px;
    box-shadow:0 10px 25px rgba(0,0,0,.05);
    margin-bottom:20px;
}

.badge{
    display:inline-block;
    background:#ead8aa;
    color:#2c2417 !important;
    padding:8px 14px;
    border-radius:999px;
    font-size:13px;
    font-weight:800;
    margin-right:8px;
    margin-bottom:8px;
}

.hero-title{
    font-size:42px;
    font-weight:900;
    color:#1f1a14 !important;
    margin-top:10px;
    margin-bottom:8px;
}

.hero-sub{
    color:#4d4337 !important;
    font-size:18px;
    line-height:1.5;
}

.card{
    background:white;
    border:1px solid #dfcfad;
    border-radius:22px;
    padding:22px;
    margin-bottom:18px;
    box-shadow:0 8px 20px rgba(0,0,0,.04);
}

h1,h2,h3,p,label,div,span{
    color:#1f1a14;
}

.small{
    color:#5c5246 !important;
    font-size:14px;
}

div.stButton > button:first-child{
    background:linear-gradient(135deg,#c79b36,#e7ca79);
    color:#20180d !important;
    border:none;
    border-radius:14px;
    font-weight:900;
    padding:.8rem 1rem;
}

div.stDownloadButton > button:first-child{
    background:#201a14;
    color:white !important;
    border:none;
    border-radius:14px;
    font-weight:900;
    padding:.85rem 1rem;
}

div.stDownloadButton > button:first-child p{
    color:white !important;
}

[data-testid="stFileUploader"]{
    border:2px dashed #c79b36;
    border-radius:20px;
    padding:14px;
    background:#fffaf0;
}

[data-testid="stFileUploader"] *{
    color:#1f1a14 !important;
}

.result{
    background:#eef8ef;
    border:1px solid #bfdabf;
    padding:16px;
    border-radius:18px;
    margin-top:14px;
    color:#1f1a14 !important;
}

.error{
    background:#fff0f0;
    border:1px solid #e5b8b8;
    padding:16px;
    border-radius:18px;
    margin-top:14px;
    color:#1f1a14 !important;
}

.download-title{
    background:#201a14;
    color:white !important;
    padding:16px;
    border-radius:18px;
    margin:18px 0 12px 0;
    font-size:17px;
    font-weight:900;
    text-align:center;
}

.download-title *{
    color:white !important;
}

input {
    border-radius:12px !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
<span class="badge">Compression forte</span>
<span class="badge">800×800 / 1200×1200</span>
<span class="badge">Métadonnées supprimées</span>

<div class="hero-title">Shop Pic</div>

<div class="hero-sub">
Redimensionne, corrige le format et compresse automatiquement vos images produits.
</div>
</div>
""", unsafe_allow_html=True)

MAX_FILES = 10
MAX_SIZE_MB = 5
QUALITY = 72

def clean_name(name):
    name = unicodedata.normalize("NFD", name.lower().strip())
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = re.sub(r"[^a-z0-9]+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name or "image-produit"

def format_size(size):
    if size > 1024*1024:
        return f"{size/(1024*1024):.2f} Mo"
    return f"{size/1024:.0f} Ko"

def optimize_image(data, target):
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)

    w,h = img.size
    if w != h:
        raise ValueError(f"image non carrée ({w}×{h}px)")

    img = img.convert("RGB")
    img = img.resize((target,target), Image.Resampling.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))

    out = io.BytesIO()
    img.save(
        out,
        format="JPEG",
        quality=QUALITY,
        optimize=True,
        progressive=True,
        subsampling=2
    )
    return out.getvalue()

col1,col2 = st.columns(2)

with col1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    files = st.file_uploader(
        "Ajouter vos images",
        type=["jpg","jpeg","png"],
        accept_multiple_files=True
    )
    st.markdown('<div class="small">Images carrées uniquement. Maximum 10 images, 5 Mo par image.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    mode = st.radio(
        "Format de sortie",
        ["PrestaShop 800×800", "Amazon 1200×1200"]
    )
    st.markdown('</div>', unsafe_allow_html=True)

target_size = 800 if "800" in mode else 1200

if files:
    selected_files = files[:MAX_FILES]

    if len(files) > MAX_FILES:
        st.warning(f"Maximum {MAX_FILES} images. Seules les {MAX_FILES} premières seront traitées.")

    names = []

    for i, f in enumerate(selected_files):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.image(f, width=260)
        names.append(
            st.text_input(
                f"Nom final image {i+1}",
                value=clean_name(Path(f.name).stem),
                key=f"name{i}"
            )
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Générer les images optimisées", use_container_width=True):

        generated_files = []
        errors = []
        total_before = 0
        total_after = 0
        used_names = set()

        for i, f in enumerate(selected_files):
            try:
                original = f.getvalue()

                if len(original) > MAX_SIZE_MB * 1024 * 1024:
                    raise ValueError(f"fichier supérieur à {MAX_SIZE_MB} Mo")

                filename = clean_name(names[i]) + ".jpg"

                if filename in used_names:
                    raise ValueError(f"nom en double : {filename}")

                used_names.add(filename)

                final = optimize_image(original, target_size)

                total_before += len(original)
                total_after += len(final)

                generated_files.append({
                    "filename": filename,
                    "data": final,
                    "before": len(original),
                    "after": len(final),
                })

            except Exception as e:
                errors.append(f"{f.name} : {e}")

        st.session_state["generated_files"] = generated_files
        st.session_state["errors"] = errors
        st.session_state["total_before"] = total_before
        st.session_state["total_after"] = total_after

if "generated_files" in st.session_state and st.session_state["generated_files"]:
    generated_files = st.session_state["generated_files"]
    total_before = st.session_state.get("total_before", 0)
    total_after = st.session_state.get("total_after", 0)

    reduction = 100 - ((total_after / total_before) * 100) if total_before else 0

    st.markdown(f"""
<div class="result">
<b>Compression terminée avec succès.</b><br><br>
Fichiers générés : {len(generated_files)}<br>
Poids avant : {format_size(total_before)}<br>
Poids après : {format_size(total_after)}<br>
Réduction moyenne : {reduction:.1f} %
</div>
""", unsafe_allow_html=True)

    st.markdown(
        '<div class="download-title">Télécharger le ou les fichiers prêts à être publiés</div>',
        unsafe_allow_html=True
    )

    if len(generated_files) == 1:
        file = generated_files[0]
        st.download_button(
            "Télécharger l’image optimisée",
            data=file["data"],
            file_name=file["filename"],
            mime="image/jpeg",
            use_container_width=True
        )
    else:
        for file in generated_files:
            st.download_button(
                f"Télécharger {file['filename']} — {format_size(file['after'])}",
                data=file["data"],
                file_name=file["filename"],
                mime="image/jpeg",
                use_container_width=True,
                key=f"download_{file['filename']}"
            )

    st.markdown("### Détail")
    for file in generated_files:
        reduction_file = 100 - ((file["after"] / file["before"]) * 100)
        st.write(
            f"**{file['filename']}** — {format_size(file['before'])} → {format_size(file['after'])} — réduction {reduction_file:.1f} %"
        )

if st.session_state.get("errors"):
    st.markdown(
        "<div class='error'><b>Images refusées :</b><br>" + "<br>".join(st.session_state["errors"]) + "</div>",
        unsafe_allow_html=True
    )

if not files:
    st.info("Ajoutez une ou plusieurs images pour commencer.")
