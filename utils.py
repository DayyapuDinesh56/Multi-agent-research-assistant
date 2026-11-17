import os
import requests
import urllib.parse
import streamlit as st

API_URL = "http://127.0.0.1:8000"

def encode_uri(text):
    return urllib.parse.quote(text)

def upload_file_to_backend(files):
    upload_url = f"{API_URL}/api/documents/upload"
    payload = []
    for file in files:
        payload.append(("files", (file.name, file.getvalue(), file.type)))
    try:
        res = requests.post(upload_url, files=payload)
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def delete_file_from_backend(filename):
    try:
        res = requests.delete(f"{API_URL}/api/documents/{encode_uri(filename)}")
        return res.json()
    except Exception as e:
        return {"error": str(e)}

def get_documents_from_backend():
    try:
        res = requests.get(f"{API_URL}/api/documents")
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def get_briefings_from_backend():
    try:
        res = requests.get(f"{API_URL}/api/briefings")
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def get_briefing_content(filename):
    try:
        res = requests.get(f"{API_URL}/api/briefings/{encode_uri(filename)}")
        if res.status_code == 200:
            return res.text
    except Exception:
        pass
    return ""

def load_custom_css():
    style_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            css_content = f.read()
        st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

def get_indexing_status_from_backend():
    try:
        res = requests.get(f"{API_URL}/api/documents/indexing-status")
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return {"is_indexing": False, "logs": []}
