import streamlit as st
import pandas as pd
from PIL import Image
import database as db
import numpy as np

# pyzbarがない場合のエラー回避
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

# Session State
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
    
    # Highlight low stock function
    def highlight_low_stock(row):
        # 在庫数(stock)が基準値(min_stock)以下の場合は赤くする
        # データがない場合の安全策として .get を使用
        current_stock = row.get('stock', 0)
        min_limit = row.get('min_stock', 0)
        
        if current_stock <= min_limit:
            return ['background-color: #ffcccc'] * len(row)
        return [''] * len(row)

    if not df.empty:
        # データフレームを表示（column_configで表示名だけ日本語に変える）
        st.dataframe(
            df.style.apply(highlight_low_stock, axis=1),
            column_config={
                "name": "商品名",
                "manufacturer": "メーカー",
                "stock": "在庫数",
                "expiry": "期限",
                "barcode": "バーコード",
                "min_stock": None, # 画面には表示しない
                "id": None,        # 画面には表示しない
                "image_path": None # 画面には表示しない
            },
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
        st.warning("⚠️ サーバー環境にバーコード読取ライブラリがありません。手動検索を使用してください。")
        # ヒント: packages.txt に libzbar0 が必要です
    else:
        img_file_buffer = st.camera_input("カメラでバーコードを読み取る")
        if img_file_buffer:
            try:
                image = Image.open(img_file_buffer)
                decoded_objects = decode(image)
                
                if decoded_objects:
                    for obj in decoded_objects:
                        code = obj.data.decode("utf-8")
                        st.session_state.scanned_code = code
                        st.success(f"読み取り成功: {code}")
                else:
                    st.warning("バーコードを検出できませんでした。")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

    # 2. Manual Search
    st.subheader("⌨️ 手動検索")
    
    # スキャン結果があればそれを初期値にする
    default_val = st.session_state.scanned_code if st.session_state.scanned_code else ""
    search_query = st.text_input("商品名またはバーコードを入力", value=default_val)
    
    target_product = None
    if search_query:
        # バーコードで検索
        target_product = db.get_product_by_barcode(search_query)
        
        # 見つからなければ名前で部分一致検索
        if not target_product:
            all_products = db.get_inventory()
            # 大文字小文字を区別せずに検索
            filtered = all_products[all_products['name'].str.contains(search_query, case=False, na=False)]
            if not filtered.empty:
                # 検索候補が複数ある場合は簡易的に先頭を表示
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
            order_qty = st.number_input("発注数", min_value=1, value=5, key="order_qty") 
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
        # 表示設定
        st.dataframe(
            orders,
            column_config={
                "name": "商品名",
                "manufacturer": "メーカー",
                "quantity": "発注数",
                "created_at": "登録日時",
                "id": None,
                "product_id": None,
                "status": None
            },
            use_container_width=True
        )
        
        if st.button("✅ 発注完了とする (リストをクリア)", type="primary", use_container_width=True):
            db.clear_orders()
            st.session_state.last_action = "発注リストをクリアしました。"
            st.rerun()
    else:
        st.info("現在、発注待ちの商品はありません。")
