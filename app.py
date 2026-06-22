import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, timedelta
import io

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Rama Kawula Coffee – Admin",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS – Coffee & Earth Tones
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;500;600&display=swap');

/* ── Root palette ── */
:root {
    --espresso:   #2C1A0E;
    --roast:      #5C3317;
    --caramel:    #A0522D;
    --latte:      #C8956C;
    --cream:      #F5ECD7;
    --parchment:  #FAF4E8;
    --foam:       #FDFAF3;
    --moss:       #4A6741;
    --rust:       #B84A2F;
    --gold:       #C9973A;
}

/* ── Global background ── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: var(--parchment) !important;
    font-family: 'Inter', sans-serif;
    color: var(--espresso);
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--espresso) 0%, var(--roast) 100%) !important;
    border-right: 3px solid var(--caramel);
}
[data-testid="stSidebar"] * {
    color: var(--cream) !important;
}
[data-testid="stSidebar"] .stRadio label {
    font-size: 0.95rem;
    padding: 6px 0;
    cursor: pointer;
    transition: color 0.2s;
}
[data-testid="stSidebar"] .stRadio label:hover {
    color: var(--latte) !important;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--latte) !important;
    font-family: 'Playfair Display', serif;
}

/* ── Main headings ── */
h1, h2, h3 {
    font-family: 'Playfair Display', serif;
    color: var(--espresso) !important;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
    background: var(--foam);
    border: 1px solid var(--latte);
    border-left: 5px solid var(--caramel);
    border-radius: 10px;
    padding: 18px 20px !important;
    box-shadow: 0 2px 8px rgba(44,26,14,0.08);
}
[data-testid="stMetricLabel"] {
    font-size: 0.8rem !important;
    font-weight: 600;
    color: var(--roast) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: var(--espresso) !important;
    font-family: 'Playfair Display', serif;
    font-size: 1.5rem !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--cream);
    border-radius: 8px 8px 0 0;
    border-bottom: 2px solid var(--caramel);
    gap: 4px;
    padding: 4px 6px 0;
}
.stTabs [data-baseweb="tab"] {
    color: var(--roast) !important;
    font-weight: 600;
    border-radius: 6px 6px 0 0;
    padding: 8px 18px;
    transition: background 0.2s;
}
.stTabs [aria-selected="true"] {
    background: var(--caramel) !important;
    color: var(--foam) !important;
}

/* ── Forms / containers ── */
[data-testid="stForm"] {
    background: var(--foam);
    border: 1px solid var(--latte);
    border-radius: 10px;
    padding: 20px 24px;
    box-shadow: 0 2px 6px rgba(44,26,14,0.06);
}

/* ── Buttons ── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
    background: linear-gradient(135deg, var(--caramel), var(--roast)) !important;
    color: var(--foam) !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600;
    padding: 10px 24px;
    letter-spacing: 0.03em;
    transition: opacity 0.2s, transform 0.1s;
}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {
    opacity: 0.88;
    transform: translateY(-1px);
}

/* ── Selectbox / inputs ── */
[data-baseweb="select"] > div, [data-baseweb="input"] > div {
    background: var(--parchment) !important;
    border-color: var(--latte) !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--latte);
    border-radius: 8px;
    overflow: hidden;
}

/* ── Success / info alerts ── */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ── Divider ── */
hr {
    border-color: var(--latte);
    opacity: 0.4;
    margin: 16px 0;
}

/* ── Section headers ── */
.section-header {
    font-family: 'Playfair Display', serif;
    font-size: 1.1rem;
    color: var(--roast);
    border-bottom: 2px solid var(--caramel);
    padding-bottom: 6px;
    margin-bottom: 14px;
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  DATABASE
# ─────────────────────────────────────────────
DB_PATH = "rama_kawula_coffee.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal     DATE,
            tipe        TEXT CHECK(tipe IN ('MASUK','KELUAR')),
            kategori    TEXT,
            nominal     REAL,
            keterangan  TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name   TEXT UNIQUE,
            quantity    INTEGER DEFAULT 0
        )
    """)

    default_items = ["Kopi", "Susu", "Gelas", "Botol", "Stiker"]
    for item in default_items:
        c.execute(
            "INSERT OR IGNORE INTO inventory (item_name, quantity) VALUES (?, 0)",
            (item,)
        )

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def fmt_rp(amount: float) -> str:
    """Format number to Indonesian Rupiah: Rp 1.250.000"""
    if pd.isna(amount):
        return "Rp 0"
    amount = int(amount)
    return "Rp " + "{:,}".format(amount).replace(",", ".")

def load_transactions() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY tanggal DESC, id DESC",
        conn,
        parse_dates=["tanggal"],
    )
    conn.close()
    return df

def load_inventory() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT item_name AS 'Bahan', quantity AS 'Stok' FROM inventory", conn)
    conn.close()
    return df

# ─────────────────────────────────────────────
#  INIT
# ─────────────────────────────────────────────
init_db()

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style='text-align:center; padding: 10px 0 4px;'>
            <span style='font-size:2.4rem;'>☕</span>
            <h2 style='margin:4px 0 0; font-size:1.25rem;'>Rama Kawula Coffee</h2>
            <p style='font-size:0.78rem; opacity:0.7; margin:2px 0 14px;'>Panel Admin</p>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio(
        "Navigasi",
        ["📊 Dashboard", "💳 Input Transaksi", "📦 Manajemen Stok", "📋 Laporan Keuangan"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(
        f"<p style='font-size:0.72rem; opacity:0.55; text-align:center;'>© 2025 Rama Kawula Coffee</p>",
        unsafe_allow_html=True,
    )

page = menu.split(" ", 1)[1].strip()

# ═══════════════════════════════════════════════════════════
#  1. DASHBOARD
# ═══════════════════════════════════════════════════════════
if page == "Dashboard":
    st.title("📊 Dashboard")
    st.caption("Ringkasan keuangan dan stok hari ini.")

    df = load_transactions()

    # ── KPIs ────────────────────────────────
    total_masuk_cash = df[
        (df["tipe"] == "MASUK") &
        (df["kategori"].isin(["SALDO_AWAL", "PENJUALAN_CASH"]))
    ]["nominal"].sum()

    total_keluar = df[df["tipe"] == "KELUAR"]["nominal"].sum()
    total_qris   = df[(df["tipe"] == "MASUK") & (df["kategori"] == "PENJUALAN_QRIS")]["nominal"].sum()
    laba_cash    = total_masuk_cash - total_keluar

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💰 Total Keuntungan Cash", fmt_rp(laba_cash))
    with col2:
        st.metric("📱 Total QRIS", fmt_rp(total_qris))
    with col3:
        st.metric("🧾 Total Pengeluaran", fmt_rp(total_keluar))
    with col4:
        total_omset = total_masuk_cash + total_qris
        st.metric("☕ Total Omset", fmt_rp(total_omset))

    st.markdown("---")

    # ── Chart ───────────────────────────────
    st.markdown("<div class='section-header'>Grafik Pemasukan vs Pengeluaran (7 Hari Terakhir)</div>",
                unsafe_allow_html=True)

    if df.empty:
        st.info("Belum ada data transaksi. Silakan tambahkan transaksi terlebih dahulu.")
    else:
        df["tanggal"] = pd.to_datetime(df["tanggal"])
        cutoff = pd.Timestamp(date.today()) - timedelta(days=6)
        df_week = df[df["tanggal"] >= cutoff].copy()

        if df_week.empty:
            st.info("Tidak ada transaksi dalam 7 hari terakhir.")
        else:
            df_week["tgl_str"] = df_week["tanggal"].dt.strftime("%d/%m")
            masuk_daily = (
                df_week[df_week["tipe"] == "MASUK"]
                .groupby("tgl_str")["nominal"].sum()
                .rename("Pemasukan")
            )
            keluar_daily = (
                df_week[df_week["tipe"] == "KELUAR"]
                .groupby("tgl_str")["nominal"].sum()
                .rename("Pengeluaran")
            )
            chart_df = pd.concat([masuk_daily, keluar_daily], axis=1).fillna(0)

            # Reindex by sorted date labels
            all_dates = sorted(df_week["tgl_str"].unique())
            chart_df = chart_df.reindex(all_dates).fillna(0)

            st.bar_chart(chart_df, color=["#A0522D", "#B84A2F"])

    st.markdown("---")

    # ── Inventory ───────────────────────────
    st.markdown("<div class='section-header'>Status Stok Bahan Baku</div>", unsafe_allow_html=True)
    inv_df = load_inventory()
    st.dataframe(inv_df, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
#  2. INPUT TRANSAKSI
# ═══════════════════════════════════════════════════════════
elif page == "Input Transaksi":
    st.title("💳 Input Transaksi")

    tab1, tab2, tab3 = st.tabs(["🏦 Saldo Awal", "☕ Penjualan Kopi", "🛒 Pembelian Bahan Baku"])

    # ── Tab 1: Saldo Awal ─────────────────
    with tab1:
        st.markdown("**Catat saldo awal kas.**")
        with st.form("form_saldo_awal", clear_on_submit=True):
            tanggal   = st.date_input("Tanggal", value=date.today())
            nominal   = st.number_input("Jumlah Uang (Rp)", min_value=0, step=1000, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Saldo awal senin pagi")
            submitted = st.form_submit_button("💾 Simpan Saldo Awal")

        if submitted:
            if nominal <= 0:
                st.error("Jumlah uang harus lebih dari 0.")
            else:
                conn = get_conn()
                conn.execute(
                    "INSERT INTO transactions (tanggal, tipe, kategori, nominal, keterangan) VALUES (?,?,?,?,?)",
                    (str(tanggal), "MASUK", "SALDO_AWAL", float(nominal), keterangan),
                )
                conn.commit()
                conn.close()
                st.success(f"✅ Saldo awal {fmt_rp(nominal)} berhasil disimpan!")

    # ── Tab 2: Penjualan Kopi ─────────────
    with tab2:
        st.markdown("**Catat penjualan kopi harian.**")
        with st.form("form_penjualan", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today(), key="tgl_jual")
            jumlah_cup = st.number_input("Jumlah Beli (Cup)", min_value=0, step=1, format="%d")
            nominal    = st.number_input("Total Uang (Rp)", min_value=0, step=1000, format="%d")
            pembayaran = st.selectbox("Metode Pembayaran", ["Cash", "QRIS"])
            keterangan = st.text_input("Keterangan", placeholder="mis. Penjualan sore")
            submitted  = st.form_submit_button("💾 Simpan Penjualan")

        if submitted:
            if nominal <= 0:
                st.error("Total uang harus lebih dari 0.")
            else:
                kategori = "PENJUALAN_CASH" if pembayaran == "Cash" else "PENJUALAN_QRIS"
                ket_full = f"{jumlah_cup} cup | {keterangan}".strip(" |")
                conn = get_conn()
                conn.execute(
                    "INSERT INTO transactions (tanggal, tipe, kategori, nominal, keterangan) VALUES (?,?,?,?,?)",
                    (str(tanggal), "MASUK", kategori, float(nominal), ket_full),
                )
                conn.commit()
                conn.close()
                st.success(f"✅ Penjualan {jumlah_cup} cup ({pembayaran}) senilai {fmt_rp(nominal)} tersimpan!")

    # ── Tab 3: Pembelian Bahan Baku ───────
    with tab3:
        st.markdown("**Catat pembelian bahan baku.**")
        KATEGORI_OPTIONS = ["Botol", "Gelas", "Stiker", "Susu", "Kopi", "Lainnya"]
        with st.form("form_bahan_baku", clear_on_submit=True):
            tanggal  = st.date_input("Tanggal", value=date.today(), key="tgl_bahan")
            kategori = st.selectbox("Kategori Bahan", KATEGORI_OPTIONS)
            nama_lain = st.text_input("Nama Bahan (jika Lainnya)", placeholder="mis. Tisu, Sendok")
            jumlah   = st.number_input("Jumlah", min_value=0, step=1, format="%d")
            nominal  = st.number_input("Total Harga (Rp)", min_value=0, step=500, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Beli di toko X")
            submitted = st.form_submit_button("💾 Simpan Pembelian")

        if submitted:
            if nominal <= 0:
                st.error("Total harga harus lebih dari 0.")
            else:
                cat_final = nama_lain.strip() if (kategori == "Lainnya" and nama_lain.strip()) else kategori
                ket_full  = f"{cat_final} {jumlah} pcs | {keterangan}".strip(" |")
                conn = get_conn()
                conn.execute(
                    "INSERT INTO transactions (tanggal, tipe, kategori, nominal, keterangan) VALUES (?,?,?,?,?)",
                    (str(tanggal), "KELUAR", "PEMBELIAN_BAHAN", float(nominal), ket_full),
                )
                conn.commit()
                conn.close()
                st.success(f"✅ Pembelian {cat_final} senilai {fmt_rp(nominal)} tersimpan!")


# ═══════════════════════════════════════════════════════════
#  3. MANAJEMEN STOK
# ═══════════════════════════════════════════════════════════
elif page == "Manajemen Stok":
    st.title("📦 Manajemen Stok")

    inv_df = load_inventory()

    # ── Section 1: Stok Awal ──────────────
    st.markdown("<div class='section-header'>⚙️ Atur Stok Awal (Override Manual)</div>",
                unsafe_allow_html=True)
    st.caption("Gunakan bagian ini untuk menyetel jumlah stok secara langsung.")

    with st.form("form_stok_awal", clear_on_submit=False):
        stok_inputs = {}
        items = ["Kopi", "Susu", "Gelas", "Botol", "Stiker"]
        cols  = st.columns(len(items))
        for i, item in enumerate(items):
            cur = int(inv_df[inv_df["Bahan"] == item]["Stok"].values[0]) if not inv_df[inv_df["Bahan"] == item].empty else 0
            with cols[i]:
                stok_inputs[item] = st.number_input(
                    item, min_value=0, value=cur, step=1, format="%d", key=f"stok_awal_{item}"
                )
        submitted_awal = st.form_submit_button("💾 Simpan Stok Awal")

    if submitted_awal:
        conn = get_conn()
        for item, qty in stok_inputs.items():
            conn.execute(
                "UPDATE inventory SET quantity = ? WHERE item_name = ?", (qty, item)
            )
        conn.commit()
        conn.close()
        st.success("✅ Stok awal berhasil diperbarui!")
        st.rerun()

    st.markdown("---")

    # ── Section 2: Update Stok Harian ─────
    st.markdown("<div class='section-header'>🔄 Update Stok Harian</div>", unsafe_allow_html=True)

    semua_item = ["Kopi", "Susu", "Gelas", "Botol", "Stiker"]
    pilih_item = st.selectbox("Pilih Item", semua_item, key="pilih_item_harian")

    # ── PRODUKSI KOPI ──────────────────────
    if pilih_item == "Kopi":
        st.info("☕ **Mode Produksi Kopi** — stok bahan akan dikurangi sesuai pemakaian.")
        with st.form("form_produksi", clear_on_submit=True):
            tanggal       = st.date_input("Tanggal Produksi", value=date.today(), key="tgl_prod")
            jumlah_buat   = st.number_input("Jumlah Buat (Cup)", min_value=0, step=1, format="%d")
            susu_pakai    = st.number_input("Susu Terpakai (ml / unit)", min_value=0, step=1, format="%d")
            kopi_pakai    = st.number_input("Kopi Terpakai (gr / unit)", min_value=0, step=1, format="%d")
            gelas_pakai   = st.number_input("Gelas Terpakai (pcs)", min_value=0, step=1, format="%d")
            keterangan    = st.text_input("Keterangan", placeholder="mis. Produksi sore hari")
            submitted_prod = st.form_submit_button("💾 Simpan Produksi")

        if submitted_prod:
            conn = get_conn()
            updates = [("Susu", susu_pakai), ("Kopi", kopi_pakai), ("Gelas", gelas_pakai)]
            errors = []
            for item_name, kurang in updates:
                row = conn.execute(
                    "SELECT quantity FROM inventory WHERE item_name = ?", (item_name,)
                ).fetchone()
                if row and row[0] < kurang:
                    errors.append(f"Stok **{item_name}** tidak cukup (tersisa {row[0]}, dibutuhkan {kurang}).")

            if errors:
                conn.close()
                for e in errors:
                    st.error(e)
            else:
                for item_name, kurang in updates:
                    conn.execute(
                        "UPDATE inventory SET quantity = quantity - ? WHERE item_name = ?",
                        (kurang, item_name)
                    )
                conn.commit()
                conn.close()
                st.success(
                    f"✅ Produksi {jumlah_buat} cup dicatat. "
                    f"Susu -{susu_pakai}, Kopi -{kopi_pakai}, Gelas -{gelas_pakai}."
                )
                st.rerun()

    # ── RESTOCK Bahan Lain ─────────────────
    else:
        st.info(f"📦 **Mode Restock {pilih_item}** — stok akan ditambah dan pengeluaran dicatat.")
        with st.form("form_restock", clear_on_submit=True):
            tanggal     = st.date_input("Tanggal Restock", value=date.today(), key="tgl_restock")
            jumlah_beli = st.number_input("Jumlah Beli", min_value=0, step=1, format="%d")
            harga_total = st.number_input("Harga Total (Rp)", min_value=0, step=500, format="%d")
            keterangan  = st.text_input("Keterangan", placeholder="mis. Beli di toko X")
            submitted_restock = st.form_submit_button("💾 Simpan Restock")

        if submitted_restock:
            if jumlah_beli <= 0:
                st.error("Jumlah beli harus lebih dari 0.")
            else:
                conn = get_conn()
                conn.execute(
                    "UPDATE inventory SET quantity = quantity + ? WHERE item_name = ?",
                    (jumlah_beli, pilih_item)
                )
                if harga_total > 0:
                    ket_full = f"Restock {pilih_item} {jumlah_beli} pcs | {keterangan}".strip(" |")
                    conn.execute(
                        "INSERT INTO transactions (tanggal, tipe, kategori, nominal, keterangan) VALUES (?,?,?,?,?)",
                        (str(tanggal), "KELUAR", "RESTOCK", float(harga_total), ket_full),
                    )
                conn.commit()
                conn.close()
                st.success(
                    f"✅ Restock {pilih_item} +{jumlah_beli} pcs "
                    + (f"| Pengeluaran {fmt_rp(harga_total)} dicatat." if harga_total > 0 else "")
                )
                st.rerun()

    # ── Tabel stok terkini ─────────────────
    st.markdown("---")
    st.markdown("<div class='section-header'>📋 Stok Saat Ini</div>", unsafe_allow_html=True)
    inv_now = load_inventory()
    st.dataframe(inv_now, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
#  4. LAPORAN KEUANGAN
# ═══════════════════════════════════════════════════════════
elif page == "Laporan Keuangan":
    st.title("📋 Laporan Keuangan")

    df = load_transactions()

    if df.empty:
        st.info("Belum ada data transaksi.")
        st.stop()

    df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date

    # ── Filter Tanggal ────────────────────
    st.markdown("<div class='section-header'>🔎 Filter Periode</div>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input(
            "Dari Tanggal",
            value=date.today() - timedelta(days=6),
            key="lap_start",
        )
    with col_b:
        end_date = st.date_input(
            "Sampai Tanggal",
            value=date.today(),
            key="lap_end",
        )

    if start_date > end_date:
        st.error("Tanggal mulai tidak boleh melebihi tanggal akhir.")
        st.stop()

    mask = (df["tanggal"] >= start_date) & (df["tanggal"] <= end_date)
    df_filtered = df[mask].copy()

    st.markdown("---")

    # ── Ringkasan Periode ─────────────────
    total_m = df_filtered[df_filtered["tipe"] == "MASUK"]["nominal"].sum()
    total_k = df_filtered[df_filtered["tipe"] == "KELUAR"]["nominal"].sum()
    saldo   = total_m - total_k

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Pemasukan", fmt_rp(total_m))
    c2.metric("Total Pengeluaran", fmt_rp(total_k))
    c3.metric("Saldo Bersih", fmt_rp(saldo))

    st.markdown("---")

    # ── Tabel Transaksi ───────────────────
    st.markdown(
        f"<div class='section-header'>📄 Detail Transaksi "
        f"({start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')})</div>",
        unsafe_allow_html=True,
    )

    if df_filtered.empty:
        st.info("Tidak ada transaksi pada periode yang dipilih.")
    else:
        display_df = df_filtered.drop(columns=["id"]).copy()
        display_df["tanggal"] = display_df["tanggal"].astype(str)
        display_df["nominal"] = display_df["nominal"].apply(fmt_rp)
        display_df.columns = ["Tanggal", "Tipe", "Kategori", "Nominal", "Keterangan"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── Export CSV ────────────────────────
    st.markdown("---")
    st.markdown("<div class='section-header'>⬇️ Ekspor Data</div>", unsafe_allow_html=True)

    export_df = df_filtered.drop(columns=["id"]).copy() if not df_filtered.empty else df.drop(columns=["id"]).head(0)
    export_df["tanggal"] = export_df["tanggal"].astype(str)

    csv_buffer = io.BytesIO()
    export_df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_bytes = csv_buffer.getvalue()

    filename = f"laporan_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
    st.download_button(
        label="⬇️ Unduh CSV",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        help="Unduh laporan transaksi periode yang dipilih dalam format CSV.",
    )
