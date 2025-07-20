import os
import streamlit as st
import pandas as pd
import random
import smtplib
from email.message import EmailMessage
from datetime import datetime

RAW_IMG_DIR = "raw_img"
GUIDE_IMG_PATH = "gScoreGuide.png"


def get_cache_path(author):
    output_dir = os.path.join(os.getcwd(), "gScorer-output")
    os.makedirs(output_dir, exist_ok=True)
    return os.path.join(output_dir, f"{author}_scores_tmp.csv")

def get_image_files():
    exts = (".png", ".jpg", ".jpeg", ".bmp", ".gif")
    return [f for f in os.listdir(RAW_IMG_DIR) if f.lower().endswith(exts)]

def get_randomized_images(image_order):
    files = get_image_files()  # Use all images
    if not image_order or len(image_order) != len(files):
        image_order = files.copy()
        random.shuffle(image_order)
    return image_order


# --- Session state variables ---
if "scores" not in st.session_state:
    st.session_state.scores = []
if "img_idx" not in st.session_state:
    st.session_state.img_idx = 0
if "image_order" not in st.session_state:
    st.session_state.image_order = []
if "batch_size" not in st.session_state:
    st.session_state.batch_size = 0
if "batch_start" not in st.session_state:
    st.session_state.batch_start = 0

st.title("gScorer v0.1 - Graft Image Scoring")



# Author selection
author_options = ["Select author...", "Fadi", "Joanna", "Helen", "George", "Naeem", "Audrey", "Others (Please Specify)"]

# Session recovery logic
import json
def load_session_cache(author):
    cache_path = get_cache_path(author)
    if os.path.exists(cache_path):
        try:
            df = pd.read_csv(cache_path)
            scores = df.to_dict("records")
            img_idx = len(scores)
            # Optionally, store batch_size, batch_start, image_order in cache as well
            return {
                "scores": scores,
                "img_idx": img_idx,
                "image_order": None,  # Not cached yet
                "batch_size": 0,
                "batch_start": 0
            }
        except Exception:
            return None
    return None

if "author_name" not in st.session_state:
    selected_author = st.selectbox("Select your name to begin scoring:", author_options)
    if selected_author == "Others (Please Specify)":
        custom_name = st.text_input("Please enter your name:")
        author_name = custom_name.strip()
    elif selected_author == "Select author...":
        author_name = ""
    else:
        author_name = selected_author
    if author_name:
        cache_data = load_session_cache(author_name)
        if cache_data:
            st.markdown(f"**Previous Session Recovered for {author_name}.**")
            if st.button(f"Continue from previous session for {author_name}"):
                st.session_state.author_name = author_name
                st.session_state.scores = cache_data["scores"]
                st.session_state.img_idx = cache_data["img_idx"]
                st.session_state.image_order = get_randomized_images([])
                st.session_state.batch_size = cache_data["batch_size"]
                st.session_state.batch_start = cache_data["batch_start"]
                st.session_state.last_author = author_name
                st.rerun()
            if st.button("Start a new session (discard previous)"):
                os.remove(get_cache_path(author_name))
                st.session_state.author_name = author_name
                st.session_state.scores = []
                st.session_state.img_idx = 0
                st.session_state.image_order = get_randomized_images([])
                st.session_state.batch_size = 0
                st.session_state.batch_start = 0
                st.session_state.last_author = author_name
                st.rerun()
            st.stop()
        else:
            st.session_state.author_name = author_name
            st.session_state.scores = []
            st.session_state.img_idx = 0
            st.session_state.image_order = get_randomized_images([])
            st.session_state.batch_size = 0
            st.session_state.batch_start = 0
            st.session_state.last_author = author_name
            st.rerun()
    else:
        st.stop()
else:
    author_name = st.session_state.author_name
    st.markdown(f"**Author:** {author_name}")
    # Reset session state when author changes
    if ("last_author" not in st.session_state) or (st.session_state.last_author != author_name):
        st.session_state.scores = []
        st.session_state.img_idx = 0
        st.session_state.image_order = get_randomized_images([])
        st.session_state.batch_size = 0
        st.session_state.batch_start = 0
        st.session_state.last_author = author_name
    # Get randomized images after author selection
    if not st.session_state.image_order:
        st.session_state.image_order = get_randomized_images([])
    image_files = st.session_state.image_order
    total_images = len(image_files)

# Always initialize image_files and total_images before use
image_files = st.session_state.image_order if "image_order" in st.session_state and st.session_state.image_order else []
total_images = len(image_files)


# Progress bar
st.progress(st.session_state.img_idx / total_images if total_images > 0 else 0, text=f"Progress: {st.session_state.img_idx}/{total_images} images scored")


# Prompt for batch size if not set, only after author is selected
if author_name and st.session_state.batch_size == 0:
    st.write("How many images can you score right now?")
    total_remaining = len(image_files) - st.session_state.img_idx
    batch_options = [5, 50, 100, 150, 200]
    batch_labels = [str(opt) for opt in batch_options] + [f"All ({total_remaining})"]
    cols = st.columns(len(batch_labels))
    for idx, col in enumerate(cols):
        if idx < len(batch_options):
            if col.button(batch_labels[idx], key=f"batch_{batch_options[idx]}_{author_name}"):
                st.session_state.batch_size = batch_options[idx]
                st.session_state.batch_start = st.session_state.img_idx
                st.rerun()
        else:
            if col.button(batch_labels[idx], key=f"batch_all_{author_name}"):
                st.session_state.batch_size = total_remaining
                st.session_state.batch_start = st.session_state.img_idx
                st.rerun()
    st.stop()

# Main scoring loop

batch_end = min(st.session_state.batch_start + st.session_state.batch_size, len(image_files))
if st.session_state.img_idx < batch_end:
    img_file = image_files[st.session_state.img_idx]
    st.image(os.path.join(RAW_IMG_DIR, img_file), use_container_width=True)
    st.write("Select a score for this image:")
    score_labels = [
        "0 🍃",
        "1 🌱",
        "2 🌸",
        "3 🌞",
        "4 🔥",
        "5 💥",
        "6 🌋"
    ]
    cols = st.columns(7)
    for i, col in enumerate(cols):
        if col.button(score_labels[i], key=f"score_{i}_{st.session_state.img_idx}", help=f"Score {i}", use_container_width=True):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            st.session_state.scores.append({"image": img_file, "score": i, "timestamp": timestamp})
            st.session_state.img_idx += 1
            # Save cache after each score
            df_tmp = pd.DataFrame(st.session_state.scores)
            cache_path = get_cache_path(author_name)
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            df_tmp.to_csv(cache_path, index=False)
            st.rerun()
    st.image(GUIDE_IMG_PATH, caption="gScore Guide", use_container_width=True)
elif st.session_state.img_idx < len(image_files):
    st.success(f"Batch of {st.session_state.batch_size} images scored!")
    # Email after every batch
    df = pd.DataFrame(st.session_state.scores)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.getcwd(), "gScorer-output")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"{author_name}_scores_{timestamp_str}.csv")
    df.to_csv(csv_path, index=False)
    def send_email_with_attachment(subject, body, to_email, attachment_path):
        SMTP_SERVER = st.secrets["SMTP_SERVER"]
        SMTP_PORT = int(st.secrets["SMTP_PORT"])
        SMTP_USER = st.secrets["SMTP_USER"]
        SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
        SENDER_NAME = st.secrets["SENDER_NAME"]
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg.set_content(body)
        with open(attachment_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            st.success("Batch results have been emailed.")
        except Exception as e:
            st.error(f"Failed to send email: {e}")
    RECIPIENT_EMAIL = st.secrets["RECIPIENT_EMAIL"]
    send_email_with_attachment(
        subject=f"gScorer Output Submitted by {author_name}",
        body=f"Scores for {author_name} (batch) are attached.",
        to_email=RECIPIENT_EMAIL,
        attachment_path=csv_path
    )
    if st.button("Another 50? Please?", key="next_batch"):
        st.session_state.batch_start = st.session_state.img_idx
        st.session_state.batch_size = 50
        st.rerun()
    if st.button("Finish & Email Results", key="finish_batch"):
        st.session_state.batch_size = 0
        st.session_state.batch_start = 0
        st.rerun()
    st.stop()
else:
    st.success("All images scored!")
    df = pd.DataFrame(st.session_state.scores)
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = os.path.join(os.getcwd(), "gScorer-output")
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, f"{author_name}_scores_{timestamp_str}.csv")
    df.to_csv(csv_path, index=False)
    # Remove cache after completion
    cache_path = get_cache_path(author_name)
    if os.path.exists(cache_path):
        os.remove(cache_path)
    st.write(f"Scores saved to {csv_path}")
    st.dataframe(df)
    # Email the CSV file (do not show email address)
    def send_email_with_attachment(subject, body, to_email, attachment_path):
        SMTP_SERVER = st.secrets["SMTP_SERVER"]
        SMTP_PORT = int(st.secrets["SMTP_PORT"])
        SMTP_USER = st.secrets["SMTP_USER"]
        SMTP_PASSWORD = st.secrets["SMTP_PASSWORD"]
        SENDER_NAME = st.secrets["SENDER_NAME"]
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg["To"] = to_email
        msg.set_content(body)
        with open(attachment_path, "rb") as f:
            file_data = f.read()
            file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)
        try:
            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
            st.success("Results have been emailed.")
        except Exception as e:
            st.error(f"Failed to send email: {e}")
    RECIPIENT_EMAIL = st.secrets["RECIPIENT_EMAIL"]
    send_email_with_attachment(
        subject=f"gScorer Output Submitted by {author_name}",
        body=f"Scores for {author_name} (final) are attached.",
        to_email=RECIPIENT_EMAIL,
        attachment_path=csv_path
    )