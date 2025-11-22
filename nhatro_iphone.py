import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from io import BytesIO

# Tạo DB + 30 phòng sẵn (chỉ chạy lần đầu)
db = "nhatro.db"
if not os.path.exists(db):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE phong 
                 (sophong TEXT PRIMARY KEY, ten TEXT, sdt TEXT, trangthai TEXT, coc INTEGER)''')
    c.execute('''CREATE TABLE hoa_don 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, sophong TEXT, thang TEXT, 
                  tong INTEGER, tinhtrang TEXT DEFAULT 'Chưa thu', ngaytao TEXT)''')
    for i in range(1,31):
        c.execute("INSERT INTO phong VALUES (?,?,?, 'Trống', 0)", (f"{i:03d}", "", ""))
    conn.commit()
    conn.close()

st.set_page_config(page_title="Nhà Trọ 30 Phòng", layout="centered")
st.title("QUẢN LÝ NHÀ TRỌ")
st.markdown("**Dùng mượt trên iPhone · Thêm vào Màn hình chính = app thật**")

conn = sqlite3.connect(db)
c = conn.cursor()

# ===== MENU =====
menu = st.sidebar.selectbox("Chọn chức năng", 
    ["Tổng quan", "Danh sách phòng", "Nhập chỉ số", "Hóa đơn & QR", "Công nợ"])

if menu == "Tổng quan":
    c.execute("SELECT COUNT(*) FROM phong WHERE trangthai='Đang thuê'")
    thue = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM phong WHERE trangthai='Trống'")
    trong = c.fetchone()[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Đang thuê", thue)
    col2.metric("Còn trống", trong)
    col3.metric("Tổng", 30)

elif menu == "Danh sách phòng":
    df = pd.read_sql("SELECT sophong AS Phòng, ten AS 'Tên khách', sdt AS 'SĐT', trangthai AS 'Trạng thái', coc AS 'Tiền cọc' FROM phong ORDER BY sophong", conn)
    edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")
    if st.button("Lưu thay đổi"):
        for index, row in edited_df.iterrows():
            c.execute("UPDATE phong SET ten=?, sdt=?, trangthai=?, coc=? WHERE sophong=?", 
                      (row['Tên khách'], row['SĐT'], row['Trạng thái'], row['Tiền cọc'], row['Phòng']))
        conn.commit()
        st.success("Đã lưu danh sách phòng!")

elif menu == "Nhập chỉ số":
    st.header(f"Nhập chỉ số tháng {datetime.now():%m/%Y}")
    sophong = st.selectbox("Chọn phòng", [f"{i:03d}" for i in range(1,31)])
    col1, col2 = st.columns(2)
    with col1:
        dien_moi = st.number_input("Điện mới", 0, 9999, 0)
        nuoc_moi = st.number_input("Nước mới", 0, 999, 0)
    with col2:
        tien_phong = st.number_input("Tiền phòng", value=1500000)
        khac = st.number_input("Wifi + rác + khác", value=150000)

    if st.button("TẠO HÓA ĐƠN", type="primary"):
        # tính tiền điện bậc thang EVN 2025
        sodien = dien_moi
        if sodien <= 50: dien = sodien*1728
        elif sodien <= 100: dien = 50*1728 + (sodien-50)*1786
        elif sodien <= 200: dien = 50*1728 + 50*1786 + (sodien-100)*2074
        else: dien = 50*1728 + 50*1786 + 100*2074 + (sodien-200)*2612

        tong = tien_phong + dien + nuoc_moi*12000 + khac
        thang = datetime.now().strftime("%m/%Y")

        c.execute("INSERT INTO hoa_don (sophong, thang, tong, ngaytao) VALUES (?,?,?,?)",
                  (sophong, thang, int(tong), datetime.now().strftime("%d/%m/%Y")))
        conn.commit()
        st.success(f"Phòng {sophong} → {tong:,} ₫")
        st.balloons()

elif menu == "Hóa đơn & QR":
    thang = st.text_input("Tháng", datetime.now().strftime("%m/%Y"))
    df = pd.read_sql(f"SELECT hd.sophong, hd.tong, hd.tinhtrang, p.ten FROM hoa_don hd JOIN phong p ON hd.sophong = p.sophong WHERE hd.thang='{thang}'", conn)
    for _, row in df.iterrows():
        with st.expander(f"Phòng {row['sophong']} – {row['ten']} – {row['tong']:,}₫ – {row['tinhtrang']}"):
            # QR VietQR động (sửa số TK, tên ngân hàng nếu cần)
            qr_url = f"https://img.vietqr.io/image/MB-0382999999-compact2.png?amount={row['tong']}&addInfo=Phong {row['sophong']} {thang}&accountName=PHAM TRIEU THIEU"
            st.image(qr_url, caption=f"QR chuyển khoản phòng {row['sophong']} (MB Bank - Sửa trong code nếu dùng ngân hàng khác)")
            st.markdown(f"[Quét QR trực tiếp]({qr_url})")

else:  # Công nợ
    thang = datetime.now().strftime("%m/%Y")
    df = pd.read_sql(f"""SELECT p.sophong, p.ten, p.sdt, h.tong, h.tinhtrang 
                         FROM hoa_don h JOIN phong p ON h.sophong=p.sophong 
                         WHERE h.thang='{thang}'""", conn)
    st.dataframe(df, use_container_width=True)
    if st.button("Đánh dấu tất cả đã thu"):
        c.execute(f"UPDATE hoa_don SET tinhtrang='Đã thu' WHERE thang='{thang}'")
        conn.commit()
        st.rerun()

st.markdown("---")
st.markdown("Mở trên **iPhone → Safari → nút Chia sẻ → Thêm vào Màn hình chính** → xong!")
conn.close()
