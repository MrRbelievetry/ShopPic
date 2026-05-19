
import io
import re
import unicodedata
from zipfile import ZipFile
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
    color:#2c2417;
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
    color:#1f1a14;
    margin-top:10px;
    margin-bottom:8px;
}

.hero-sub{
    color:#4d4337;
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

h1,h2,h3,p,label,div{
    color:#1f1a14;
}

.small{
    color:#5c5246;
    font-size:14px;
}

div.stButton > button:first-child{
    background:linear-gradient(135deg,#c79b36,#e7ca79);
    color:#20180d;
    border:none;
    border-radius:14px;
    font-weight:900;
    padding:.8rem 1rem;
}

div.stDownloadButton > button:first-child{
    background:#201a14;
    color:white;
    border:none;
    border-radius:14px;
    font-weight:900;
    padding:.8rem 1rem;
}

[data-testid="stFileUploader"]{
    border:2px dashed #c79b36;
    border-radius:20px;
    padding:14px;
    background:#fffaf0;
}

.result{
    background:#eef8ef;
    border:1px solid #bfdabf;
    padding:16px;
    border-radius:18px;
    margin-top:14px;
}

.error{
    background:#fff0f0;
    border:1px solid #e5b8b8;
    padding:16px;
    border-radius:18px;
    margin-top:14px;
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
QUALITY = 72

def clean_name(name):
    name = unicodedata.normalize("NFD", name.lower())
    name = "".join(c for c in name if unicodedata.category(c) != "Mn")
    name = re.sub(r"[^a-z0-9]+", "-", name)
    return re.sub(r"-+", "-", name).strip("-")

def format_size(size):
    if size > 1024*1024:
        return f"{size/(1024*1024):.2f} Mo"
    return f"{size/1024:.0f} Ko"

def optimize_image(data, target):
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)

    w,h = img.size
    if w != h:
        raise ValueError(f"Image non carrée ({w}x{h})")

    img = img.convert("RGB")
    img = img.resize((target,target), Image.Resampling.LANCZOS)
    img = img.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110))

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
    st.markdown('<div class="small">Images carrées uniquement pour éviter les déformations.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    mode = st.radio(
        "Format de sortie",
        ["PrestaShop 800×800","Amazon 1200×1200"]
    )
    st.markdown('</div>', unsafe_allow_html=True)

size = 800 if "800" in mode else 1200

if files:
    names = []

    for i,f in enumerate(files[:MAX_FILES]):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.image(f, width=240)
        names.append(
            st.text_input(
                f"Nom image {i+1}",
                value=clean_name(Path(f.name).stem),
                key=f"name{i}"
            )
        )
        st.markdown('</div>', unsafe_allow_html=True)

    if st.button("Générer les images optimisées", use_container_width=True):

        zip_buffer = io.BytesIO()
        total_before = 0
        total_after = 0
        errors = []

        with ZipFile(zip_buffer, "w") as zipf:
            for i,f in enumerate(files[:MAX_FILES]):
                try:
                    original = f.getvalue()
                    final = optimize_image(original, size)

                    total_before += len(original)
                    total_after += len(final)

                    filename = clean_name(names[i]) + ".jpg"
                    zipf.writestr(filename, final)

                except Exception as e:
                    errors.append(f"{f.name} : {e}")

        reduction = 100 - ((total_after / total_before) * 100)

        st.markdown(f"""
<div class="result">
<b>Compression terminée avec succès.</b><br><br>
Poids avant : {format_size(total_before)}<br>
Poids après : {format_size(total_after)}<br>
Réduction moyenne : {reduction:.1f}%
</div>
""", unsafe_allow_html=True)

        st.download_button(
            "Télécharger le ZIP optimisé",
            zip_buffer.getvalue(),
            file_name="images-produits.zip",
            mime="application/zip",
            use_container_width=True
        )

        if errors:
            st.markdown("<div class='error'>" + "<br>".join(errors) + "</div>", unsafe_allow_html=True)

else:
    st.info("Ajoutez une ou plusieurs images pour commencer.")
