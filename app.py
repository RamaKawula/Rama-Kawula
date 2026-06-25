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
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --accent:      #7B5E3A;
    --border-soft: rgba(127, 94, 58, 0.25);
    --danger:      #B84A2F;
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
.delete-warning {
    background-color: #fff3f0;
    border-left: 4px solid #B84A2F;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 8px 0;
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
    return create_client(url, key)

try:
    supabase = get_supabase()
except Exception as e:
    st.error(f"Gagal koneksi ke Supabase: {e}")
    st.info("Pastikan SUPABASE_URL dan SUPABASE_KEY sudah benar di Streamlit Secrets.")
    st.stop()

# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────
# Item stok yang bisa desimal (float)
FLOAT_ITEMS = {"Beans Kopi", "Espresso", "Gula Padat", "Gula Cair"}

ITEMS_STOK = ["Beans Kopi", "Susu", "Espresso", "Gula Padat", "Gula Cair", "Gelas", "Botol", "Stiker"]

SATUAN_LABEL = {
    "Beans Kopi": "gr",
    "Susu":       "ml",
    "Espresso":   "ml",
    "Gula Padat": "kg",
    "Gula Cair":  "ml",
    "Gelas":      "pcs",
    "Botol":      "pcs",
    "Stiker":     "pcs",
}

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

def fmt_stok(val: float, item_name: str) -> str:
    """Format stok: tampilkan desimal hanya jika item float."""
    if item_name in FLOAT_ITEMS:
        return f"{val:.2f}".rstrip("0").rstrip(".")
    return str(int(val))

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
        st.error(f"Gagal memuat transaksi: {e}")
        return pd.DataFrame(columns=["id","tanggal","tipe","kategori","nominal","keterangan"])

def load_inventory() -> pd.DataFrame:
    """Load inventory dengan satuan yang sesuai untuk tiap item."""
    try:
        res = supabase.table("inventory").select("item_name, quantity").execute()
        if res.data:
            df = pd.DataFrame(res.data)
            df.columns = ["Bahan", "Stok"]
            df["Satuan"] = df["Bahan"].map(SATUAN_LABEL).fillna("pcs")

            order = ["Beans Kopi", "Espresso", "Susu", "Gula Padat", "Gula Cair", "Gelas", "Botol", "Stiker"]
            existing   = [o for o in order if o in df["Bahan"].values]
            others     = df[~df["Bahan"].isin(order)]["Bahan"].tolist()
            full_order = existing + others
            df["Bahan"] = pd.Categorical(df["Bahan"], categories=full_order, ordered=True)
            df = df.sort_values("Bahan").reset_index(drop=True)[["Bahan", "Stok", "Satuan"]]
            # Format stok kolom
            df["Stok"] = df.apply(
                lambda r: fmt_stok(float(r["Stok"]), str(r["Bahan"])), axis=1
            )
            return df
        return pd.DataFrame(columns=["Bahan", "Stok", "Satuan"])
    except Exception as e:
        st.error(f"Gagal memuat inventori: {e}")
        return pd.DataFrame(columns=["Bahan", "Stok", "Satuan"])

def load_espresso_log() -> pd.DataFrame:
    try:
        res = (
            supabase.table("transactions")
            .select("*")
            .eq("kategori", "PRODUKSI_ESPRESSO")
            .order("tanggal", desc=True)
            .order("id", desc=True)
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date.astype(str)
            return df[["tanggal", "keterangan"]].rename(
                columns={"tanggal": "Tanggal", "keterangan": "Keterangan"}
            )
        return pd.DataFrame(columns=["Tanggal", "Keterangan"])
    except Exception as e:
        st.error(f"Gagal memuat log espresso: {e}")
        return pd.DataFrame(columns=["Tanggal", "Keterangan"])

def load_gula_cair_log() -> pd.DataFrame:
    try:
        res = (
            supabase.table("transactions")
            .select("*")
            .eq("kategori", "PRODUKSI_GULA_CAIR")
            .order("tanggal", desc=True)
            .order("id", desc=True)
            .execute()
        )
        if res.data:
            df = pd.DataFrame(res.data)
            df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date.astype(str)
            return df[["tanggal", "keterangan"]].rename(
                columns={"tanggal": "Tanggal", "keterangan": "Keterangan"}
            )
        return pd.DataFrame(columns=["Tanggal", "Keterangan"])
    except Exception as e:
        st.error(f"Gagal memuat log gula cair: {e}")
        return pd.DataFrame(columns=["Tanggal", "Keterangan"])

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
        st.error(f"Gagal menyimpan transaksi: {e}")

def update_transaction(trx_id: int, tanggal, tipe, kategori, nominal, keterangan):
    try:
        supabase.table("transactions").update({
            "tanggal":    str(tanggal),
            "tipe":       tipe,
            "kategori":   kategori,
            "nominal":    float(nominal),
            "keterangan": keterangan,
        }).eq("id", trx_id).execute()
        return True
    except Exception as e:
        st.error(f"Gagal mengupdate transaksi: {e}")
        return False

def delete_transaction(trx_id: int):
    try:
        supabase.table("transactions").delete().eq("id", trx_id).execute()
        return True
    except Exception as e:
        st.error(f"Gagal menghapus transaksi: {e}")
        return False

def get_stok(item_name: str) -> float:
    """Ambil stok sebagai float (support desimal untuk Beans, Espresso, Gula Padat, Gula Cair)."""
    try:
        res = (
            supabase.table("inventory")
            .select("quantity")
            .eq("item_name", item_name)
            .single()
            .execute()
        )
        return float(res.data["quantity"]) if res.data else 0.0
    except Exception:
        return 0.0

def set_stok(item_name: str, quantity: float):
    try:
        res = supabase.table("inventory") \
            .update({"quantity": quantity}) \
            .eq("item_name", item_name) \
            .execute()
        if res.data is not None and len(res.data) == 0:
            supabase.table("inventory").insert({
                "item_name": item_name,
                "quantity":  quantity,
            }).execute()
    except Exception as e:
        st.error(f"Gagal update stok {item_name}: {e}")

def add_stok(item_name: str, delta: float):
    set_stok(item_name, round(get_stok(item_name) + delta, 4))

def deduct_stok(item_name: str, delta: float):
    set_stok(item_name, round(get_stok(item_name) - delta, 4))

def delete_stok_item(item_name: str):
    try:
        supabase.table("inventory").delete().eq("item_name", item_name).execute()
        return True
    except Exception as e:
        st.error(f"Gagal menghapus item stok: {e}")
        return False

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Rama Kawula Coffee")
    st.caption("Panel Admin")
    st.markdown("---")
    menu = st.radio(
        "Navigasi",
        ["Dashboard", "Input Transaksi", "Manajemen Stok", "Laporan Keuangan", "Edit & Hapus Data"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("© Rama Kawula Coffee")

page = menu.strip()

# ═══════════════════════════════════════════════════════════
#  1. DASHBOARD
# ═══════════════════════════════════════════════════════════
if page == "Dashboard":
    st.title("Dashboard")
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
    col1.metric("Saldo Kas Bersih", fmt_rp(laba_cash))
    col2.metric("Total QRIS", fmt_rp(total_qris))
    col3.metric("Total Pengeluaran", fmt_rp(total_keluar))
    col4.metric("Total Omset", fmt_rp(total_masuk_cash + total_qris))

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
            df_week["tgl_str"]   = df_week["tanggal"].dt.strftime("%d/%m")
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
    st.title("Input Transaksi")

    tab1, tab2, tab3, tab4 = st.tabs(["Saldo Awal", "Penjualan Cash", "Penjualan QRIS", "Pembelian Bahan Baku"])

    # ── Saldo Awal ──────────────────────────────
    with tab1:
        st.markdown("**Catat saldo awal kas.**")
        with st.form("form_saldo_awal", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today())
            nominal    = st.number_input("Jumlah Uang (Rp)", min_value=0, step=1000, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Saldo awal senin pagi")
            submitted  = st.form_submit_button("Simpan Saldo Awal")
        if submitted:
            if nominal <= 0:
                st.error("Jumlah uang harus lebih dari 0.")
            else:
                insert_transaction(tanggal, "MASUK", "SALDO_AWAL", nominal, keterangan)
                st.success(f"Saldo awal {fmt_rp(nominal)} berhasil disimpan.")

    # ── Penjualan Cash ───────────────────────────
    with tab2:
        st.markdown("**Catat penjualan kopi — pembayaran tunai.**")
        st.caption("Penjualan cash akan masuk ke total pemasukan dan saldo kas.")
        with st.form("form_penjualan_cash", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today(), key="tgl_jual_cash")
            jumlah_cup = st.number_input("Jumlah Cup", min_value=0, step=1, format="%d")
            nominal    = st.number_input("Total Uang (Rp)", min_value=0, step=1000, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Penjualan sore")
            submitted  = st.form_submit_button("Simpan Penjualan Cash")
        if submitted:
            if nominal <= 0:
                st.error("Total uang harus lebih dari 0.")
            else:
                insert_transaction(tanggal, "MASUK", "PENJUALAN_CASH", nominal,
                                   f"{jumlah_cup} cup | {keterangan}".strip(" |"))
                st.success(f"Penjualan cash {jumlah_cup} cup senilai {fmt_rp(nominal)} tersimpan.")

    # ── Penjualan QRIS ───────────────────────────
    with tab3:
        st.markdown("**Catat penjualan kopi — pembayaran QRIS.**")
        st.caption("Penjualan QRIS dicatat terpisah dan tidak masuk ke saldo kas tunai.")
        with st.form("form_penjualan_qris", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today(), key="tgl_jual_qris")
            jumlah_cup = st.number_input("Jumlah Cup", min_value=0, step=1, format="%d")
            nominal    = st.number_input("Total Uang (Rp)", min_value=0, step=1000, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Penjualan pagi")
            submitted  = st.form_submit_button("Simpan Penjualan QRIS")
        if submitted:
            if nominal <= 0:
                st.error("Total uang harus lebih dari 0.")
            else:
                insert_transaction(tanggal, "MASUK", "PENJUALAN_QRIS", nominal,
                                   f"{jumlah_cup} cup | {keterangan}".strip(" |"))
                st.success(f"Penjualan QRIS {jumlah_cup} cup senilai {fmt_rp(nominal)} tersimpan.")

    # ── Pembelian Bahan Baku ─────────────────────
    with tab4:
        st.markdown("**Catat pembelian bahan baku.**")
        with st.form("form_bahan_baku", clear_on_submit=True):
            tanggal    = st.date_input("Tanggal", value=date.today(), key="tgl_bahan")
            kategori   = st.selectbox("Kategori Bahan", ["Beans Kopi", "Botol", "Gelas", "Gula Padat", "Stiker", "Susu", "Lainnya"])
            nama_lain  = st.text_input("Nama Bahan (jika Lainnya)", placeholder="mis. Tisu, Sendok")
            jumlah     = st.number_input("Jumlah", min_value=0.0, step=0.1, format="%.2f")
            nominal    = st.number_input("Total Harga (Rp)", min_value=0, step=500, format="%d")
            keterangan = st.text_input("Keterangan", placeholder="mis. Beli di toko X")
            submitted  = st.form_submit_button("Simpan Pembelian")
        if submitted:
            if nominal <= 0:
                st.error("Total harga harus lebih dari 0.")
            else:
                cat_final = nama_lain.strip() if (kategori == "Lainnya" and nama_lain.strip()) else kategori
                sat_beli  = SATUAN_LABEL.get(cat_final, "pcs")
                insert_transaction(tanggal, "KELUAR", "PEMBELIAN_BAHAN", nominal,
                                   f"{cat_final} {jumlah} {sat_beli} | {keterangan}".strip(" |"))
                st.success(f"Pembelian {cat_final} senilai {fmt_rp(nominal)} tersimpan.")


# ═══════════════════════════════════════════════════════════
#  3. MANAJEMEN STOK
# ═══════════════════════════════════════════════════════════
elif page == "Manajemen Stok":
    st.title("Manajemen Stok")

    inv_df = load_inventory()

    # ── Stok Awal ────────────────────────────────
    st.subheader("Atur Stok Awal (Override Manual)")
    st.caption("Setel jumlah stok secara langsung. Beans Kopi, Espresso, Gula Padat, dan Gula Cair mendukung desimal.")

    with st.form("form_stok_awal", clear_on_submit=False):
        stok_inputs = {}
        # Baris 1: bahan dengan satuan volume/berat (float)
        row1_items = ["Beans Kopi", "Espresso", "Susu", "Gula Padat", "Gula Cair"]
        # Baris 2: bahan satuan pcs (integer)
        row2_items = ["Gelas", "Botol", "Stiker"]

        cols1 = st.columns(len(row1_items))
        for i, item in enumerate(row1_items):
            row = inv_df[inv_df["Bahan"] == item]
            cur_raw = float(str(row["Stok"].values[0]).replace(",", ".")) if not row.empty else 0.0
            label   = f"{item} ({SATUAN_LABEL[item]})"
            is_float = item in FLOAT_ITEMS
            with cols1[i]:
                stok_inputs[item] = st.number_input(
                    label, min_value=0.0, value=cur_raw,
                    step=0.01 if is_float else 1.0,
                    format="%.2f" if is_float else "%.0f",
                    key=f"stok_awal_{item}"
                )

        cols2 = st.columns(len(row2_items))
        for i, item in enumerate(row2_items):
            row = inv_df[inv_df["Bahan"] == item]
            cur_raw = float(str(row["Stok"].values[0]).replace(",", ".")) if not row.empty else 0.0
            label   = f"{item} ({SATUAN_LABEL[item]})"
            with cols2[i]:
                stok_inputs[item] = st.number_input(
                    label, min_value=0.0, value=cur_raw, step=1.0, format="%.0f",
                    key=f"stok_awal_{item}"
                )

        submitted_awal = st.form_submit_button("Simpan Stok Awal")

    if submitted_awal:
        for item, qty in stok_inputs.items():
            set_stok(item, qty)
        st.success("Stok awal berhasil diperbarui.")
        st.rerun()

    st.markdown("---")

    # ── Produksi Harian ──────────────────────────
    st.subheader("Produksi Harian")

    tab_botol, tab_espresso, tab_gula_cair, tab_restock = st.tabs(
        ["Produksi Kopi Botol", "Produksi Espresso", "Produksi Gula Cair", "Restock Bahan"]
    )

    # ─────────────────────────────────────────────
    #  TAB: PRODUKSI KOPI BOTOL
    # ─────────────────────────────────────────────
    with tab_botol:
        st.markdown("**Produksi kopi botol** — mengurangi stok: Espresso, Susu, Gula Cair, Botol, Stiker, Gelas.")
        with st.form("form_produksi_botol", clear_on_submit=True):
            tanggal      = st.date_input("Tanggal Produksi", value=date.today(), key="tgl_prod_botol")
            jumlah_botol = st.number_input("Jumlah Botol Diproduksi (pcs)", min_value=0, step=1, format="%d")

            st.markdown("**Pemakaian per batch produksi:**")
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            with c1:
                espresso_pakai  = st.number_input("Espresso (ml)",   min_value=0.0, step=0.1, format="%.1f", key="bb_espresso")
            with c2:
                susu_pakai      = st.number_input("Susu (ml)",       min_value=0.0, step=0.1, format="%.1f", key="bb_susu")
            with c3:
                gula_cair_pakai = st.number_input("Gula Cair (ml)",  min_value=0.0, step=0.1, format="%.1f", key="bb_gula_cair")
            with c4:
                botol_pakai     = st.number_input("Botol (pcs)",     min_value=0,   step=1,   format="%d",   key="bb_botol")
            with c5:
                stiker_pakai    = st.number_input("Stiker (pcs)",    min_value=0,   step=1,   format="%d",   key="bb_stiker")
            with c6:
                gelas_pakai     = st.number_input("Gelas (pcs)",     min_value=0,   step=1,   format="%d",   key="bb_gelas")

            keterangan      = st.text_input("Keterangan", placeholder="mis. Produksi pagi", key="ket_botol")
            submitted_botol = st.form_submit_button("Simpan Produksi Botol")

        if submitted_botol:
            updates = [
                ("Espresso",   espresso_pakai,  "ml"),
                ("Susu",       susu_pakai,      "ml"),
                ("Gula Cair",  gula_cair_pakai, "ml"),
                ("Botol",      float(botol_pakai),  "pcs"),
                ("Stiker",     float(stiker_pakai), "pcs"),
                ("Gelas",      float(gelas_pakai),  "pcs"),
            ]
            errors = []
            for item_name, kurang, sat in updates:
                if kurang > 0:
                    stok_skrg = get_stok(item_name)
                    stok_label = SATUAN_LABEL.get(item_name, "pcs")
                    if stok_skrg < kurang:
                        errors.append(
                            f"Stok **{item_name}** tidak cukup "
                            f"(tersisa {fmt_stok(stok_skrg, item_name)} {stok_label}, "
                            f"dibutuhkan {kurang} {sat})."
                        )
            if errors:
                for e in errors:
                    st.error(e)
            else:
                for item_name, kurang, _ in updates:
                    if kurang > 0:
                        deduct_stok(item_name, kurang)
                detail = (
                    f"Espresso:{espresso_pakai}ml Susu:{susu_pakai}ml "
                    f"GulaCair:{gula_cair_pakai}ml Botol:{botol_pakai} "
                    f"Stiker:{stiker_pakai} Gelas:{gelas_pakai}"
                )
                insert_transaction(
                    tanggal, "KELUAR", "PRODUKSI_BOTOL", 0,
                    f"Produksi {jumlah_botol} botol | {detail} | {keterangan}".strip(" |")
                )
                st.success(f"Produksi {jumlah_botol} botol berhasil dicatat. Stok bahan telah dikurangi.")
                st.rerun()

    # ─────────────────────────────────────────────
    #  TAB: PRODUKSI ESPRESSO
    # ─────────────────────────────────────────────
    with tab_espresso:
        st.markdown("**Produksi espresso** — mengurangi stok Beans Kopi (gr), menambah stok Espresso (ml).")
        with st.form("form_produksi_espresso", clear_on_submit=True):
            tanggal = st.date_input("Tanggal Produksi", value=date.today(), key="tgl_prod_espresso")

            st.markdown("**Detail produksi:**")
            c1, c2 = st.columns(2)
            with c1:
                beans_dipakai  = st.number_input(
                    "Beans Kopi dipakai (gr)", min_value=0.0, step=0.1, format="%.1f", key="esp_beans"
                )
            with c2:
                espresso_hasil = st.number_input(
                    "Hasil Espresso (ml)", min_value=0.0, step=0.1, format="%.1f", key="esp_hasil"
                )

            keterangan         = st.text_input("Keterangan", placeholder="mis. Produksi espresso pagi", key="ket_espresso")
            submitted_espresso = st.form_submit_button("Simpan Produksi Espresso")

        if submitted_espresso:
            if beans_dipakai <= 0 and espresso_hasil <= 0:
                st.error("Isi jumlah Beans Kopi dan/atau Hasil Espresso.")
            else:
                stok_beans = get_stok("Beans Kopi")
                if beans_dipakai > 0 and stok_beans < beans_dipakai:
                    st.error(
                        f"Stok **Beans Kopi** tidak cukup "
                        f"(tersisa {fmt_stok(stok_beans, 'Beans Kopi')} gr, "
                        f"dibutuhkan {beans_dipakai} gr)."
                    )
                else:
                    if beans_dipakai > 0:
                        deduct_stok("Beans Kopi", beans_dipakai)
                    if espresso_hasil > 0:
                        add_stok("Espresso", espresso_hasil)
                    detail_esp = f"Beans:{beans_dipakai}gr → Espresso:{espresso_hasil}ml"
                    insert_transaction(
                        tanggal, "KELUAR", "PRODUKSI_ESPRESSO", 0,
                        f"{detail_esp} | {keterangan}".strip(" |")
                    )
                    st.success(
                        f"Produksi espresso berhasil dicatat. "
                        f"Beans Kopi -{beans_dipakai} gr, Espresso +{espresso_hasil} ml."
                    )
                    st.rerun()

        st.markdown("---")
        st.markdown("**Riwayat Produksi Espresso**")
        esp_log = load_espresso_log()
        if esp_log.empty:
            st.info("Belum ada riwayat produksi espresso.")
        else:
            st.dataframe(esp_log, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────
    #  TAB: PRODUKSI GULA CAIR
    # ─────────────────────────────────────────────
    with tab_gula_cair:
        st.markdown("**Produksi gula cair** — mengurangi stok Gula Padat (kg), menambah stok Gula Cair (ml).")
        st.caption("Contoh: 1 kg gula padat + air → menghasilkan gula cair sejumlah ml tertentu.")
        with st.form("form_produksi_gula_cair", clear_on_submit=True):
            tanggal = st.date_input("Tanggal Produksi", value=date.today(), key="tgl_prod_gula_cair")

            st.markdown("**Detail produksi:**")
            c1, c2 = st.columns(2)
            with c1:
                gula_padat_dipakai = st.number_input(
                    "Gula Padat dipakai (kg)", min_value=0.0, step=0.01, format="%.2f", key="gc_gula_padat"
                )
            with c2:
                gula_cair_hasil = st.number_input(
                    "Hasil Gula Cair (ml)", min_value=0.0, step=1.0, format="%.1f", key="gc_hasil"
                )

            keterangan           = st.text_input("Keterangan", placeholder="mis. Masak gula cair pagi", key="ket_gula_cair")
            submitted_gula_cair  = st.form_submit_button("Simpan Produksi Gula Cair")

        if submitted_gula_cair:
            if gula_padat_dipakai <= 0 and gula_cair_hasil <= 0:
                st.error("Isi jumlah Gula Padat yang dipakai dan/atau Hasil Gula Cair.")
            else:
                stok_gp = get_stok("Gula Padat")
                if gula_padat_dipakai > 0 and stok_gp < gula_padat_dipakai:
                    st.error(
                        f"Stok **Gula Padat** tidak cukup "
                        f"(tersisa {fmt_stok(stok_gp, 'Gula Padat')} kg, "
                        f"dibutuhkan {gula_padat_dipakai} kg)."
                    )
                else:
                    if gula_padat_dipakai > 0:
                        deduct_stok("Gula Padat", gula_padat_dipakai)
                    if gula_cair_hasil > 0:
                        add_stok("Gula Cair", gula_cair_hasil)
                    detail_gc = f"GulaPadat:{gula_padat_dipakai}kg → GulaCair:{gula_cair_hasil}ml"
                    insert_transaction(
                        tanggal, "KELUAR", "PRODUKSI_GULA_CAIR", 0,
                        f"{detail_gc} | {keterangan}".strip(" |")
                    )
                    st.success(
                        f"Produksi gula cair berhasil dicatat. "
                        f"Gula Padat -{gula_padat_dipakai} kg, Gula Cair +{gula_cair_hasil} ml."
                    )
                    st.rerun()

        st.markdown("---")
        st.markdown("**Riwayat Produksi Gula Cair**")
        gc_log = load_gula_cair_log()
        if gc_log.empty:
            st.info("Belum ada riwayat produksi gula cair.")
        else:
            st.dataframe(gc_log, use_container_width=True, hide_index=True)

    # ─────────────────────────────────────────────
    #  TAB: RESTOCK BAHAN
    # ─────────────────────────────────────────────
    with tab_restock:
        st.markdown("**Restock bahan baku** — menambah stok dan mencatat pengeluaran.")
        with st.form("form_restock", clear_on_submit=True):
            tanggal     = st.date_input("Tanggal Restock", value=date.today(), key="tgl_restock")
            pilih_item  = st.selectbox("Pilih Bahan", ITEMS_STOK, key="pilih_item_restock")
            is_float_item = pilih_item in FLOAT_ITEMS
            jumlah_beli = st.number_input(
                "Jumlah Beli",
                min_value=0.0,
                step=0.01 if is_float_item else 1.0,
                format="%.2f" if is_float_item else "%.0f"
            )
            satuan      = st.text_input(
                "Satuan",
                placeholder="mis. gr, ml, pcs, kg",
                value=SATUAN_LABEL.get(pilih_item, ""),
            )
            harga_total = st.number_input("Harga Total (Rp)", min_value=0, step=500, format="%d")
            keterangan  = st.text_input("Keterangan", placeholder="mis. Beli di toko X")
            submitted_restock = st.form_submit_button("Simpan Restock")

        if submitted_restock:
            if jumlah_beli <= 0:
                st.error("Jumlah beli harus lebih dari 0.")
            else:
                add_stok(pilih_item, jumlah_beli)
                if harga_total > 0:
                    sat_label = f" {satuan}" if satuan.strip() else ""
                    insert_transaction(tanggal, "KELUAR", "RESTOCK", harga_total,
                                       f"Restock {pilih_item} {jumlah_beli}{sat_label} | {keterangan}".strip(" |"))
                st.success(
                    f"Restock {pilih_item} +{jumlah_beli} berhasil."
                    + (f" Pengeluaran {fmt_rp(harga_total)} dicatat." if harga_total > 0 else "")
                )
                st.rerun()

    st.markdown("---")
    st.subheader("Stok Saat Ini")
    st.dataframe(load_inventory(), use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════
#  4. LAPORAN KEUANGAN
# ═══════════════════════════════════════════════════════════
elif page == "Laporan Keuangan":
    st.title("Laporan Keuangan")

    df = load_transactions()

    if df.empty:
        st.info("Belum ada data transaksi.")
        st.stop()

    df["tanggal"] = pd.to_datetime(df["tanggal"]).dt.date

    st.subheader("Filter Periode")
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

    total_cash_masuk = df_filtered[
        (df_filtered["tipe"] == "MASUK") &
        (df_filtered["kategori"].isin(["SALDO_AWAL", "PENJUALAN_CASH"]))
    ]["nominal"].sum()

    total_qris   = df_filtered[
        (df_filtered["tipe"] == "MASUK") &
        (df_filtered["kategori"] == "PENJUALAN_QRIS")
    ]["nominal"].sum()

    total_keluar = df_filtered[df_filtered["tipe"] == "KELUAR"]["nominal"].sum()
    saldo_kas    = total_cash_masuk - total_keluar

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Pemasukan Cash", fmt_rp(total_cash_masuk))
    c2.metric("Pemasukan QRIS", fmt_rp(total_qris))
    c3.metric("Total Pengeluaran", fmt_rp(total_keluar))
    c4.metric("Saldo Kas Bersih", fmt_rp(saldo_kas))

    st.markdown("---")
    st.subheader(f"Detail Transaksi ({start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')})")

    if df_filtered.empty:
        st.info("Tidak ada transaksi pada periode yang dipilih.")
    else:
        display_df = df_filtered.drop(columns=["id"]).copy()
        display_df["tanggal"] = display_df["tanggal"].astype(str)
        display_df["nominal"] = display_df["nominal"].apply(fmt_rp)
        display_df.columns    = ["Tanggal", "Tipe", "Kategori", "Nominal", "Keterangan"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Ekspor Data")

    export_df = df_filtered.drop(columns=["id"]).copy() if not df_filtered.empty else df.drop(columns=["id"]).head(0)
    export_df["tanggal"] = export_df["tanggal"].astype(str)
    csv_buf = io.BytesIO()
    export_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")

    st.download_button(
        label="Unduh CSV",
        data=csv_buf.getvalue(),
        file_name=f"laporan_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )


# ═══════════════════════════════════════════════════════════
#  5. EDIT & HAPUS DATA
# ═══════════════════════════════════════════════════════════
elif page == "Edit & Hapus Data":
    st.title("Edit & Hapus Data")
    st.caption("Gunakan halaman ini untuk mengedit atau menghapus transaksi dan data stok.")

    tab_edit_trx, tab_hapus_trx, tab_edit_stok = st.tabs(
        ["Edit Transaksi", "Hapus Transaksi", "Edit & Hapus Stok"]
    )

    # ══════════════════════════════════════════
    #  TAB: EDIT TRANSAKSI
    # ══════════════════════════════════════════
    with tab_edit_trx:
        st.subheader("Edit Transaksi")
        st.caption("Cari transaksi berdasarkan ID atau filter, lalu ubah datanya.")

        df_all = load_transactions()
        if df_all.empty:
            st.info("Belum ada data transaksi.")
        else:
            df_all["tanggal_str"] = df_all["tanggal"].dt.strftime("%d/%m/%Y")

            col_f1, col_f2 = st.columns([1, 2])
            with col_f1:
                filter_tipe = st.selectbox("Filter Tipe", ["Semua", "MASUK", "KELUAR"], key="edit_filter_tipe")
            with col_f2:
                filter_kat  = st.text_input("Filter Kategori (opsional)", placeholder="mis. PENJUALAN_CASH", key="edit_filter_kat")

            df_show = df_all.copy()
            if filter_tipe != "Semua":
                df_show = df_show[df_show["tipe"] == filter_tipe]
            if filter_kat.strip():
                df_show = df_show[df_show["kategori"].str.contains(filter_kat.strip(), case=False, na=False)]

            if df_show.empty:
                st.info("Tidak ada transaksi yang sesuai filter.")
            else:
                display_edit = df_show[["id", "tanggal_str", "tipe", "kategori", "nominal", "keterangan"]].copy()
                display_edit["nominal"] = display_edit["nominal"].apply(fmt_rp)
                display_edit.columns = ["ID", "Tanggal", "Tipe", "Kategori", "Nominal", "Keterangan"]
                st.dataframe(display_edit, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("**Pilih ID transaksi yang ingin diedit:**")

                trx_id_edit = st.number_input(
                    "ID Transaksi", min_value=1, step=1, format="%d", key="edit_trx_id"
                )

                trx_row = df_all[df_all["id"] == trx_id_edit]
                if not trx_row.empty:
                    trx = trx_row.iloc[0]
                    st.info(f"Mengedit transaksi ID **{trx_id_edit}** — {trx['kategori']} | {fmt_rp(trx['nominal'])} | {trx['keterangan']}")

                    with st.form("form_edit_trx", clear_on_submit=False):
                        e_tanggal    = st.date_input("Tanggal", value=trx["tanggal"].date(), key="edit_tgl")
                        e_tipe       = st.selectbox("Tipe", ["MASUK", "KELUAR"],
                                                    index=0 if trx["tipe"] == "MASUK" else 1, key="edit_tipe")
                        KATEGORI_OPT = [
                            "SALDO_AWAL", "PENJUALAN_CASH", "PENJUALAN_QRIS",
                            "PEMBELIAN_BAHAN", "PRODUKSI_BOTOL", "PRODUKSI_ESPRESSO",
                            "PRODUKSI_GULA_CAIR", "RESTOCK", "LAINNYA"
                        ]
                        cur_kat_idx  = KATEGORI_OPT.index(trx["kategori"]) if trx["kategori"] in KATEGORI_OPT else 8
                        e_kategori   = st.selectbox("Kategori", KATEGORI_OPT, index=cur_kat_idx, key="edit_kat")
                        e_nominal    = st.number_input("Nominal (Rp)", min_value=0, value=int(trx["nominal"]),
                                                       step=500, format="%d", key="edit_nominal")
                        e_keterangan = st.text_input("Keterangan", value=trx["keterangan"] or "", key="edit_ket")
                        submitted_edit = st.form_submit_button("Simpan Perubahan")

                    if submitted_edit:
                        ok = update_transaction(trx_id_edit, e_tanggal, e_tipe, e_kategori, e_nominal, e_keterangan)
                        if ok:
                            st.success(f"Transaksi ID {trx_id_edit} berhasil diperbarui.")
                            st.rerun()
                else:
                    if trx_id_edit > 0:
                        st.warning(f"ID transaksi {trx_id_edit} tidak ditemukan dalam filter aktif.")

    # ══════════════════════════════════════════
    #  TAB: HAPUS TRANSAKSI
    # ══════════════════════════════════════════
    with tab_hapus_trx:
        st.subheader("Hapus Transaksi")
        st.markdown(
            '<div class="delete-warning">⚠️ <strong>Perhatian:</strong> Penghapusan transaksi bersifat permanen '
            'dan tidak dapat dibatalkan. Pastikan data yang dihapus sudah benar.</div>',
            unsafe_allow_html=True,
        )

        df_del = load_transactions()
        if df_del.empty:
            st.info("Belum ada data transaksi.")
        else:
            df_del["tanggal_str"] = df_del["tanggal"].dt.strftime("%d/%m/%Y")

            col_d1, col_d2 = st.columns([1, 2])
            with col_d1:
                del_filter_tipe = st.selectbox("Filter Tipe", ["Semua", "MASUK", "KELUAR"], key="del_filter_tipe")
            with col_d2:
                del_filter_kat  = st.text_input("Filter Kategori (opsional)", key="del_filter_kat")

            df_del_show = df_del.copy()
            if del_filter_tipe != "Semua":
                df_del_show = df_del_show[df_del_show["tipe"] == del_filter_tipe]
            if del_filter_kat.strip():
                df_del_show = df_del_show[df_del_show["kategori"].str.contains(del_filter_kat.strip(), case=False, na=False)]

            if df_del_show.empty:
                st.info("Tidak ada transaksi yang sesuai filter.")
            else:
                display_del = df_del_show[["id", "tanggal_str", "tipe", "kategori", "nominal", "keterangan"]].copy()
                display_del["nominal"] = display_del["nominal"].apply(fmt_rp)
                display_del.columns = ["ID", "Tanggal", "Tipe", "Kategori", "Nominal", "Keterangan"]
                st.dataframe(display_del, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("**Pilih ID transaksi yang ingin dihapus:**")

                trx_id_del = st.number_input(
                    "ID Transaksi", min_value=1, step=1, format="%d", key="del_trx_id"
                )

                trx_del_row = df_del[df_del["id"] == trx_id_del]
                if not trx_del_row.empty:
                    trx_d = trx_del_row.iloc[0]
                    st.warning(
                        f"Anda akan menghapus: **ID {trx_id_del}** | "
                        f"{trx_d['tanggal_str']} | {trx_d['kategori']} | "
                        f"{fmt_rp(trx_d['nominal'])} | {trx_d['keterangan']}"
                    )
                    konfirmasi = st.checkbox(
                        f"Saya yakin ingin menghapus transaksi ID {trx_id_del}", key="del_konfirmasi"
                    )
                    if konfirmasi:
                        if st.button("🗑️ Hapus Sekarang", type="primary", key="btn_hapus_trx"):
                            ok = delete_transaction(trx_id_del)
                            if ok:
                                st.success(f"Transaksi ID {trx_id_del} berhasil dihapus.")
                                st.rerun()
                else:
                    if trx_id_del > 0:
                        st.warning(f"ID transaksi {trx_id_del} tidak ditemukan dalam filter aktif.")

    # ══════════════════════════════════════════
    #  TAB: EDIT & HAPUS STOK
    # ══════════════════════════════════════════
    with tab_edit_stok:
        st.subheader("Edit & Hapus Stok")

        inv_edit = load_inventory()
        if inv_edit.empty:
            st.info("Tidak ada data stok.")
        else:
            st.markdown("**Stok saat ini:**")
            st.dataframe(inv_edit, use_container_width=True, hide_index=True)

        st.markdown("---")

        st.markdown("### Edit Jumlah Stok")
        st.caption("Ubah jumlah stok salah satu bahan secara langsung.")

        all_items_in_db = inv_edit["Bahan"].tolist() if not inv_edit.empty else ITEMS_STOK

        with st.form("form_edit_stok", clear_on_submit=False):
            pilih_edit_item = st.selectbox("Pilih Bahan", all_items_in_db, key="edit_stok_item")
            row_item  = inv_edit[inv_edit["Bahan"] == pilih_edit_item] if not inv_edit.empty else pd.DataFrame()
            cur_stok_str = str(row_item["Stok"].values[0]) if not row_item.empty else "0"
            cur_stok  = float(cur_stok_str.replace(",", "."))
            sat_item  = SATUAN_LABEL.get(str(pilih_edit_item), "pcs")
            is_fi     = str(pilih_edit_item) in FLOAT_ITEMS

            st.caption(f"Stok saat ini: **{cur_stok_str} {sat_item}**")
            new_stok = st.number_input(
                f"Jumlah Baru ({sat_item})",
                min_value=0.0,
                value=cur_stok,
                step=0.01 if is_fi else 1.0,
                format="%.2f" if is_fi else "%.0f",
                key="edit_stok_val"
            )
            submitted_edit_stok = st.form_submit_button("Simpan Perubahan Stok")

        if submitted_edit_stok:
            set_stok(str(pilih_edit_item), new_stok)
            st.success(f"Stok **{pilih_edit_item}** berhasil diubah menjadi {new_stok} {sat_item}.")
            st.rerun()

        st.markdown("---")

        st.markdown("### Hapus Item Stok")
        st.markdown(
            '<div class="delete-warning">⚠️ <strong>Perhatian:</strong> Menghapus item stok akan menghilangkan '
            'data bahan baku tersebut dari database. Gunakan hanya jika bahan sudah tidak digunakan.</div>',
            unsafe_allow_html=True,
        )

        if not inv_edit.empty:
            with st.form("form_hapus_stok", clear_on_submit=True):
                pilih_hapus_item = st.selectbox("Pilih Bahan yang Ingin Dihapus",
                                                all_items_in_db, key="hapus_stok_item")
                konfirmasi_hapus_stok = st.checkbox(
                    "Saya yakin ingin menghapus item stok ini", key="hapus_stok_konfirmasi"
                )
                submitted_hapus_stok = st.form_submit_button("🗑️ Hapus Item Stok", type="primary")

            if submitted_hapus_stok:
                if not konfirmasi_hapus_stok:
                    st.error("Centang konfirmasi terlebih dahulu untuk menghapus.")
                else:
                    ok = delete_stok_item(str(pilih_hapus_item))
                    if ok:
                        st.success(f"Item stok **{pilih_hapus_item}** berhasil dihapus.")
                        st.rerun()
        else:
            st.info("Tidak ada item stok untuk dihapus.")
