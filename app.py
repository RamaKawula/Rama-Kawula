import streamlit as st
import pandas as pd
from datetime import date, timedelta
import io
from supabase import create_client, Client

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
#  CUSTOM CSS – Minimal, theme-adaptive
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --accent:      #7B5E3A;
    --border-soft: rgba(127, 94, 58, 0.25);
}
[data-testid="stMetric"] {
    border-left: 4px solid var(--accent);
    border-radius: 8px;
    padding: 14px 18px !important;
}
[data-testid="stForm"] {
    border: 1px solid var(--border-soft);
    border-radius: 8px;
    padding: 18px 20px;
}
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-soft);
    border-radius: 8px;
    overflow: hidden;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  KONEKSI SUPABASE
# ─────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    # Jika pakai key format baru (sb_publishable_...), fallback ke legacy anon key
    # Pastikan di Streamlit Secrets kamu pakai Legacy anon key bukan publishable key
    return create_client(url, key)

try:
    supabase = get_supabase()
except Exception as e:
    st.error(f"❌ Gagal koneksi ke Supabase: {e}")
    st.info("Pastikan SUPABASE_URL dan SUPABASE_KEY sudah benar di Streamlit Secrets.")
    st.stop()

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def fmt_rp(amount: float) -> str:
    try:
        if amount is None or (isinstance(amount, float) and pd.isna(amount)):
            return "Rp 0"
        return "Rp " + "{:,}".format(int(amount)).replace(",", ".")
    except Exception:
        return "Rp 0"

def load_transactions() -> pd.DataFrame:
    try:
        res = (
            supabase.table("transactions")
            .select("*")
            .order("tanggal", desc=True)
            .order("id", desc=True)
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["tanggal"] = pd.to_datetime(df["tanggal"])
            return df
        return pd.DataFrame(columns=["id","tanggal","tipe","kategori","nominal","keterangan"])
    except Exception as e:
        st.error(f"❌ Gagal memuat transaksi: {e}")
        return pd.DataFrame(columns=["id","tanggal","tipe","kategori","nominal","keterangan"])

def load_inventory() -> pd.DataFrame:
    try:
        res = supabase.table("inventory").select("item_name, quantity").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df.columns = ["Bahan", "Stok"]
            order = ["Kopi", "Susu", "Gelas", "Botol", "Stiker"]
            df["Bahan"] = pd.Categorical(df["Bahan"], categories=order, ordered=True)
            return df.sort_values("Bahan").reset_index(drop=True)
        return pd.DataFrame(columns=["Bahan", "Stok"])
    except Exception as e:
        st.error(f"❌ Gagal memuat inventori: {e}")
        return pd.DataFrame(columns=["Bahan", "Stok"])

def insert_transaction(tanggal, tipe, kategori, nominal, keterangan):
    try:
        supabase.table("transactions").insert({
            "tanggal":    str(tanggal),
            "tipe":       tipe,
            "kategori":   kategori,
            "nominal":    float(nominal),
            "keterangan": keterangan,
        }).execute()
    except Exception as e:
        st.error(f"❌ Gagal menyimpan transaksi: {e}")

def get_stok(item_name: str) -> int:
    try:
        res = (
            supabase.table("inventory")
            .select("quantity")
            .eq("item_name", item_name)
            .single()
            .execute()
        )
        return res.data["quantity"] if res.data else 0
    except Exception:
        return 0

def set_stok(item_name: str, quantity: int):
    try:
        supabase.table("inventory") \
            .update({"quantity": quantity}) \
            .eq("item_name", item_name) \
            .execute()
    except Exception as e:
        st.error(f"❌ Gagal update stok {item_name}: {e}")

def add_stok(item_name: str, delta: int):
    set_stok(item_name, get_stok(item_name) + delta)

def deduct_stok(item_name: str, delta: int):
    set_stok(item_name, get_stok(item_name) - delta)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ☕ Rama Kawula Coffee")
    st.caption("Panel Admin")
    st.markdown("---")
    menu = st.radio(
        "Navigasi",
        ["📊 Dashboard", "💳 Input Transaksi", "📦 Manajemen Stok", "📋 Laporan Keuangan"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("© 2025 Rama Kawula Coffee")

page = menu.split(" ", 1)[1].strip()

# ═══════════════════════════════════════════════════════════
#  1. DASHBOARD
# ═══════════════════════════════════════════════════════════
if page == "Dashboard":
    st.title("📊 Dashboard")
    st.caption("Ringkasan keuangan dan stok hari ini.")

    df = load_transactions()

    total_masuk_cash = df[
        (df["tipe"] == "MASUK") &
        (df["kategori"].isin(["SALDO_AWAL", "PENJUALAN_CASH"]))
    ]["nominal"].sum() if not df.empty else 0

    total_keluar = df[df["tipe"] == "KELUAR"]["nominal"].sum() if not df.empty else 0
    total_qris   = df[(df["tipe"] == "MASUK") & (df["kategori"] == "PENJUALAN_QRIS")]["nominal"].sum() if not df.empty else 0
    laba_cash    = total_masuk_cash - total_keluar

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Keuntungan Cash", fmt_rp(laba_cash))
    col2.metric("📱 Total QRIS", fmt_rp(total_qris))
    col3.metric("🧾 Total Pengeluaran", fmt_rp(total_keluar))
    col4.metric("☕ Total Omset", fmt_rp(total_masuk_cash + total_qris))

    st.markdown("---")
    st.subheader("Grafik Pemasukan vs Pengeluaran (7 Hari Terakhir)")

    if df.empty:
        st.info("Belum ada data transaksi. Silakan tambahkan transaksi terlebih dahulu.")
    else:
        cutoff  = pd.Timestamp(date.today()) - timedelta(days=6)
        df_week = df[df["tanggal"] >= cutoff].copy()
        if df_week.empty:
            st.info("Tidak ada transaksi dalam 7 hari terakhir.")
        else:
            df_week["tgl_str"]  = df_week["tanggal"].dt.strftime("%d/%m")
            masuk_daily  = df_week[df_week["tipe"] == "MASUK"].groupby("tgl_str")["nominal"].sum().rename("Pemasukan")
            keluar_daily = df_week[df_week["tipe"] == "KELUAR"].groupby("tgl_str")["nominal"].sum().rename("Pengeluaran")
            chart_df     = pd.concat([masuk_daily, keluar_daily], axis=1).fillna(0)
            chart_df     = chart_df.reindex(sorted(df_week["tgl_str"].unique())).fillna(0)
            st.bar_chart(chart_df, color=["#A0522D", "#B84A2F"])

    st.markdown("---")
    st.subheader("Status Stok Bahan Baku")
    st.dataframe(load_inventory(), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
#  2. INPUT TRANSAKSI
# ═══════════════════════════════════════════════════════════
elif page == "Input Transaksi":
    st.title("💳 Input Transaksi")

    tab1, tab2, tab3 = st.tabs(["🏦 Saldo Awal", "☕ Penjualan Kopi", "🛒 Pembelian Bahan Baku"])

    with tab1:
        st.markdown("**Catat saldo awal kas.**")
        with st.form("form_saldo_awal", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today())
            nominal    = st.number_input("Jumlah Uang (Rp)", min_value=0, step=1000, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Saldo awal senin pagi")
            submitted  = st.form_submit_button("💾 Simpan Saldo Awal")
        if submitted:
            if nominal <= 0:
                st.error("Jumlah uang harus lebih dari 0.")
            else:
                insert_transaction(tanggal, "MASUK", "SALDO_AWAL", nominal, keterangan)
                st.success(f"✅ Saldo awal {fmt_rp(nominal)} berhasil disimpan!")

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
                insert_transaction(tanggal, "MASUK", kategori, nominal, f"{jumlah_cup} cup | {keterangan}".strip(" |"))
                st.success(f"✅ Penjualan {jumlah_cup} cup ({pembayaran}) senilai {fmt_rp(nominal)} tersimpan!")

    with tab3:
        st.markdown("**Catat pembelian bahan baku.**")
        with st.form("form_bahan_baku", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today(), key="tgl_bahan")
            kategori   = st.selectbox("Kategori Bahan", ["Botol", "Gelas", "Stiker", "Susu", "Kopi", "Lainnya"])
            nama_lain  = st.text_input("Nama Bahan (jika Lainnya)", placeholder="mis. Tisu, Sendok")
            jumlah     = st.number_input("Jumlah", min_value=0, step=1, format="%d")
            nominal    = st.number_input("Total Harga (Rp)", min_value=0, step=500, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Beli di toko X")
            submitted  = st.form_submit_button("💾 Simpan Pembelian")
        if submitted:
            if nominal <= 0:
                st.error("Total harga harus lebih dari 0.")
            else:
                cat_final = nama_lain.strip() if (kategori == "Lainnya" and nama_lain.strip()) else kategori
                insert_transaction(tanggal, "KELUAR", "PEMBELIAN_BAHAN", nominal, f"{cat_final} {jumlah} pcs | {keterangan}".strip(" |"))
                st.success(f"✅ Pembelian {cat_final} senilai {fmt_rp(nominal)} tersimpan!")


# ═══════════════════════════════════════════════════════════
#  3. MANAJEMEN STOK
# ═══════════════════════════════════════════════════════════
elif page == "Manajemen Stok":
    st.title("📦 Manajemen Stok")

    inv_df = load_inventory()

    st.subheader("⚙️ Atur Stok Awal (Override Manual)")
    st.caption("Gunakan bagian ini untuk menyetel jumlah stok secara langsung.")

    with st.form("form_stok_awal", clear_on_submit=False):
        stok_inputs = {}
        items = ["Kopi", "Susu", "Gelas", "Botol", "Stiker"]
        cols  = st.columns(len(items))
        for i, item in enumerate(items):
            row = inv_df[inv_df["Bahan"] == item]
            cur = int(row["Stok"].values[0]) if not row.empty else 0
            with cols[i]:
                stok_inputs[item] = st.number_input(item, min_value=0, value=cur, step=1, format="%d", key=f"stok_awal_{item}")
        submitted_awal = st.form_submit_button("💾 Simpan Stok Awal")

    if submitted_awal:
        for item, qty in stok_inputs.items():
            set_stok(item, qty)
        st.success("✅ Stok awal berhasil diperbarui!")
        st.rerun()

    st.markdown("---")
    st.subheader("🔄 Update Stok Harian")

    pilih_item = st.selectbox("Pilih Item", ["Kopi", "Susu", "Gelas", "Botol", "Stiker"], key="pilih_item_harian")

    if pilih_item == "Kopi":
        st.info("☕ **Mode Produksi Kopi** — stok bahan akan dikurangi sesuai pemakaian.")
        with st.form("form_produksi", clear_on_submit=True):
            tanggal     = st.date_input("Tanggal Produksi", value=date.today(), key="tgl_prod")
            jumlah_buat = st.number_input("Jumlah Buat (Cup)", min_value=0, step=1, format="%d")
            susu_pakai  = st.number_input("Susu Terpakai (ml / unit)", min_value=0, step=1, format="%d")
            kopi_pakai  = st.number_input("Kopi Terpakai (gr / unit)", min_value=0, step=1, format="%d")
            gelas_pakai = st.number_input("Gelas Terpakai (pcs)", min_value=0, step=1, format="%d")
            keterangan  = st.text_input("Keterangan", placeholder="mis. Produksi sore hari")
            submitted_prod = st.form_submit_button("💾 Simpan Produksi")

        if submitted_prod:
            updates = [("Susu", susu_pakai), ("Kopi", kopi_pakai), ("Gelas", gelas_pakai)]
            errors  = []
            for item_name, kurang in updates:
                stok_skrg = get_stok(item_name)
                if stok_skrg < kurang:
                    errors.append(f"Stok **{item_name}** tidak cukup (tersisa {stok_skrg}, dibutuhkan {kurang}).")
            if errors:
                for e in errors:
                    st.error(e)
            else:
                for item_name, kurang in updates:
                    deduct_stok(item_name, kurang)
                st.success(f"✅ Produksi {jumlah_buat} cup dicatat. Susu -{susu_pakai}, Kopi -{kopi_pakai}, Gelas -{gelas_pakai}.")
                st.rerun()
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
                add_stok(pilih_item, jumlah_beli)
                if harga_total > 0:
                    insert_transaction(tanggal, "KELUAR", "RESTOCK", harga_total, f"Restock {pilih_item} {jumlah_beli} pcs | {keterangan}".strip(" |"))
                st.success(f"✅ Restock {pilih_item} +{jumlah_beli} pcs" + (f" | Pengeluaran {fmt_rp(harga_total)} dicatat." if harga_total > 0 else "."))
                st.rerun()

    st.markdown("---")
    st.subheader("📋 Stok Saat Ini")
    st.dataframe(load_inventory(), use_container_width=True, hide_index=True)


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

    st.subheader("🔎 Filter Periode")
    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input("Dari Tanggal", value=date.today() - timedelta(days=6), key="lap_start")
    with col_b:
        end_date = st.date_input("Sampai Tanggal", value=date.today(), key="lap_end")

    if start_date > end_date:
        st.error("Tanggal mulai tidak boleh melebihi tanggal akhir.")
        st.stop()

    df_filtered = df[(df["tanggal"] >= start_date) & (df["tanggal"] <= end_date)].copy()

    st.markdown("---")

    total_m = df_filtered[df_filtered["tipe"] == "MASUK"]["nominal"].sum()
    total_k = df_filtered[df_filtered["tipe"] == "KELUAR"]["nominal"].sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Pemasukan", fmt_rp(total_m))
    c2.metric("Total Pengeluaran", fmt_rp(total_k))
    c3.metric("Saldo Bersih", fmt_rp(total_m - total_k))

    st.markdown("---")
    st.subheader(f"📄 Detail Transaksi ({start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')})")

    if df_filtered.empty:
        st.info("Tidak ada transaksi pada periode yang dipilih.")
    else:
        display_df = df_filtered.drop(columns=["id"]).copy()
        display_df["tanggal"] = display_df["tanggal"].astype(str)
        display_df["nominal"] = display_df["nominal"].apply(fmt_rp)
        display_df.columns    = ["Tanggal", "Tipe", "Kategori", "Nominal", "Keterangan"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("⬇️ Ekspor Data")

    export_df = df_filtered.drop(columns=["id"]).copy() if not df_filtered.empty else df.drop(columns=["id"]).head(0)
    export_df["tanggal"] = export_df["tanggal"].astype(str)
    csv_buf = io.BytesIO()
    export_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")

    st.download_button(
        label="⬇️ Unduh CSV",
        data=csv_buf.getvalue(),
        file_name=f"laporan_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
