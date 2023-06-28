from flask import Blueprint,render_template, request,send_file,jsonify
from flask_login import login_required
import pandas as pd
from io import BytesIO
from mSite.models import OrderFormat
from mSite import db
from sqlalchemy import text

trans = Blueprint("trans",__name__)



@trans.route("/transform", methods=['GET', 'POST'])
@login_required
def trans_handle():
    return render_template('transform_file.html')

@trans.route('/process', methods=['POST'])
def process():
    file = request.files['file']
    filename = "轉檔後_" + file.filename
    df = pd.read_excel(file, engine='openpyxl')  # Process the uploaded Excel file

    # Perform any required data processing or analysis on the DataFrame (df) here
    # 創建一個空的DataFrame
    newdf = pd.DataFrame(columns=['訂單編號', '發票類型', '載具', '載具顯碼', '載具隱碼', '捐贈對象', '買方統編', '買方名稱', '買方地址',
                             '買方電話', '買方電子信箱', '品名', '課稅別', '數量', '單價(含稅)', '小計金額(含稅)', '商品備註(最多40個字)', '總備註(最多200個字)'])
    # 現在您可以對讀取的數據進行處理        
    orderRecordList = []
    preOrderNo = ''  # 上一筆訂單編號    
    for index, row in df.iterrows():
        orderNo = str(row['訂單編號']).strip()
        # 判斷沒有重覆的資料再繼續轉檔
        if OrderFormat.check_order_is_exists(orderNo) : continue        

        # 發票類型
        invoiceType = 'B2C' if preOrderNo != orderNo else ''

        # 載具
        carrier = '不使用' if preOrderNo != orderNo else ''

        # 買方名稱
        buyerName = row['買家帳號 (單)'] if preOrderNo != orderNo else ''

        # 品名
        productItem = '[' + row['收件者姓名 (單)'] + ']'+row['商品選項名稱 (品)'] if preOrderNo != orderNo else row['商品選項名稱 (品)']

        # 數量
        quantity = int(row['數量'])

        # 單價(含稅)
        unitPrice = int(row['商品活動價格 (品)'])

        # 折扣為負數金額,整筆不用出現
        if unitPrice < 0: continue

        # 小計金額(含稅)
        SubtotalAmount = (unitPrice)*(quantity)

        # 訂單日期時間
        order_datetime = row['訂單成立日期']

        # 添加一行新的數據            
        new_data = {'訂單編號':orderNo, '發票類型': invoiceType, '載具': carrier,'買方名稱': buyerName, 
                    '品名': productItem, '課稅別': '應稅', '數量': quantity , '單價(含稅)': unitPrice, 
                    '小計金額(含稅)': SubtotalAmount}
        # print(row['商品選項名稱'], row['商品原價'], row['數量'])


        # 先保存資料,最後再一起存資料庫
        orderRecordList.append(OrderFormat(orderNo,buyerName,productItem,quantity,unitPrice,SubtotalAmount,order_datetime))

        # 保存在excel資料表
        newdf = pd.concat([newdf, pd.DataFrame([new_data])], ignore_index=True)

        # 有支付運費的情況
        farePrice = int(row['買家支付的運費 (單)']) 
        if (farePrice > 0) and (preOrderNo != orderNo):
            new_data2 = {'訂單編號':orderNo, '品名': '運費', '課稅別': '應稅',
                            '數量': 1 , '單價(含稅)': farePrice, 
                        '小計金額(含稅)':farePrice}
            # 先保存資料,最後再一起存資料庫
            orderRecordList.append(OrderFormat(orderNo,'','運費',1,farePrice,farePrice,order_datetime))                                
            # 保存在excel資料表
            newdf = pd.concat([newdf, pd.DataFrame([new_data2])], ignore_index=True)

        # 保存上一筆資料
        preOrderNo = orderNo
    # 批次新增資料庫
    OrderFormat.save_multiple_orders(orderRecordList)
    # 打印新的DataFrame
    print(newdf.head())

    # Generate a new Excel file with the processed data in memory
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    newdf.to_excel(writer, index=False)
    writer.close()
    output.seek(0)

    # Return the processed Excel file for downloading
    return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='text/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# 在你的路由或視圖函式中
@trans.route('/statistics', methods=['GET'])
def get_statistics():
    query = text('''
    SELECT DATE_FORMAT(order_datetime, '%Y-%m-%d') AS date, SUM(subtotal_tax_included) AS total
    FROM mSite.orderformat
    GROUP BY DATE_FORMAT(order_datetime, '%Y-%m-%d')
    ORDER BY DATE_FORMAT(order_datetime, '%Y-%m-%d') DESC
    LIMIT 30
    ''')
    result = db.session.execute(query)

    # 將結果轉換為字典列表
    statistics = []
    for row in result:
        statistics.append({'date': row.date, 'total': row.total})

    # 回傳統計資料給前端
    return jsonify(statistics)