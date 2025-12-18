import streamlit as st
import pandas as pd
from PIL import Image
import database as db
import numpy as np
try:
    from pyzbar.pyzbar import decode
except ImportError:
    decode = None

# Page Config
st.set_page_config(page_title="オペ器械在庫管理", layout="wide")

# Initialize DB
db.init_db()

# Custom CSS for Mobile Friendliness
st.markdown("""
<style>
    .stButton>button {
        height: 3em; 
        font-size: 20px;
        width: 100%;
        border-radius: 10px;
    }
    .big-font {
        font-size: 20px !important;
    }
    .stock-warning {
        color: #ff4b4b;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏥 オペ器械・インプラント在庫管理")

# Session State for Scan Result
if 'scanned_code' not in st.session_state:
    st.session_state.scanned_code = None
if 'last_action' not in st.session_state:
    st.session_state.last_action = None

# Tabs
tab1, tab2, tab3 = st.tabs(["📦 在庫一覧", "🔍 検索・操作", "📋 発注リスト"])

# --- Tab 1: Inventory List ---
with tab1:
    st.header("在庫一覧")
    df = db.get_inventory()
    
    # Highlight low stock
    def highlight_low_stock(row):
        if row['stock'] <= row['min_stock']:
            return ['background-color: #ffcccc'] * len(row)
        return [''] * len(row)

    if not df.empty:
        # Display readable columns
        display_df = df[['name', 'manufacturer', 'stock', 'expiry', 'barcode']].copy()
        display_df.columns = ['商品名', 'メーカー', '在庫数', '期限', 'バーコード']
        
        st.dataframe(
            display_df.style.apply(highlight_low_stock, axis=1),
            use_container_width=True,
            height=500
        )
    else:
        st.info("在庫データがありません。")

    if st.button("🔄 更新"):
        st.rerun()

# --- Tab 2: Scan & Actions ---
with tab2:
    st.header("商品を検索 / 操作")

    # 1. Barcode Scanner
    st.subheader("📸 バーコードスキャン")
    if decode is None:
        st.warning("⚠️ pyzbarがインストールされていません。バーコード機能は使用できません。")
    else:
        img_file_buffer = st.camera_input("カメラでバーコードを読み取る")
        if img_file_buffer:
            # Process image
            image = Image.open(img_file_buffer)
            decoded_objects = decode(image)
            
            if decoded_objects:
                for obj in decoded_objects:
                    code = obj.data.decode("utf-8")
                    st.session_state.scanned_code = code
                    st.success(f"読み取り成功: {code}")
            else:
                st.warning("バーコードを検出できませんでした。")

    # 2. Manual Search
    st.subheader("⌨️ 手動検索")
    search_query = st.text_input("商品名またはバーコードを入力", value=st.session_state.scanned_code if st.session_state.scanned_code else "")
    
    target_product = None
    if search_query:
        # Try finding by barcode first
        target_product = db.get_product_by_barcode(search_query)
        # If not found, naive search by name (for this demo, simple match)
        if not target_product:
            all_products = db.get_inventory()
            filtered = all_products[all_products['name'].str.contains(search_query, na=False)]
            if not filtered.empty:
                # Just pick the first one for simplicity in this mobile UI
                target_product = filtered.iloc[0].to_dict()
    
    # 3. Action Area
    if target_product:
        st.divider()
        st.markdown(f"### 対象商品: **{target_product['name']}**")
        st.markdown(f"メーカー: {target_product['manufacturer']}")
        st.markdown(f"現在在庫: **{target_product['stock']}** (期限: {target_product['expiry']})")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info("納品 (在庫追加)")
            add_qty = st.number_input("追加数", min_value=1, value=1, key="add_qty")
            if st.button("📥 納品登録", use_container_width=True):
                db.update_stock(target_product['id'], add_qty)
                st.session_state.last_action = f"{target_product['name']} を {add_qty} 個 納品しました。"
                st.rerun()
                
        with col2:
            st.error("発注 (リスト追加)")
            order_qty = st.number_input("発注数", min_value=1, value=5, key="order_qty") # Default to reasonable order size
            if st.button("🛒 発注リストへ", use_container_width=True):
                db.add_to_order_list(target_product['id'], order_qty)
                st.session_state.last_action = f"{target_product['name']} を {order_qty} 個 発注リストに追加しました。"
                st.rerun()

    if st.session_state.last_action:
        st.success(st.session_state.last_action)

# --- Tab 3: Order List ---
with tab3:
    st.header("発注リスト (未発注)")
    
    orders = db.get_orders()
    if not orders.empty:
        st.dataframe(orders[['name', 'manufacturer', 'quantity', 'created_at']], use_container_width=True)
        
        if st.button("✅ 発注完了とする (リストをクリア)", type="primary", use_container_width=True):
            db.clear_orders()
            st.session_state.last_action = "発注リストをクリアしました。"
            st.rerun()
    else:
        st.info("現在、発注待ちの商品はありません。")
