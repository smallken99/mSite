from flask import Blueprint,render_template, request,send_file,jsonify
from flask_login import login_required
import pandas as pd
from io import BytesIO
from mSite.models import OrderFormat
from mSite import db
from sqlalchemy import text

inventory = Blueprint("inventory",__name__)



@inventory.route("/inventory", methods=['GET', 'POST'])
@login_required
def inventory_handle():
    return render_template('inventory.html')


# 在你的路由或視圖函式中
@inventory.route('/inventory_available_months', methods=['GET'])
def get_available_months():
    # 查詢所有不重複的 year_month
    query = text('''
    select distinct `year_month` from mSite.inventory_details
    where `status`= '2'
    order by `year_month` desc
    ''')
    result = db.session.execute(query)
    months = [row[0] for row in result]
    return jsonify(months)

@inventory.route('/inventory_stat', methods=['POST'])
def get_statistics():
    # 從前端獲取要查詢的月份列表
    req_data = request.get_json()
    target_months = req_data.get('months', [])

    if not target_months:
        return jsonify([])

    # 動態產生 SQL 的 IN 子句
    # 注意: 這裡使用參數化查詢以策安全，雖然 months 通常是受控的格式
    bind_params = {f'm{i}': month for i, month in enumerate(target_months)}
    months_placeholder = ', '.join([f':m{i}' for i in range(len(target_months))])

    query_str = f'''
    select `year_month` as 'year_month' ,`item_description` as 'item_description',sum(quantity) as 'quantity'   from mSite.inventory_details
    where `status`= '2'  and `year_month` in ({months_placeholder})
    group by `year_month`,`item_description`
    order by sum(quantity) desc
    '''
    
    query = text(query_str)
    result = db.session.execute(query, bind_params)

    # 將結果轉換為 DataFrame
    df = pd.DataFrame(result, columns=['year_month', 'item_description', 'quantity'])

    if df.empty:
        return jsonify([])

    # 以 item 作為索引，將 yymm 和 quantity 轉換為列
    df_pivot = df.pivot(index='item_description', columns='year_month', values='quantity')

    # 將 DataFrame 轉換為列表格式
    data = df_pivot.reset_index().to_dict(orient='records')
 
    new_data = []
    for d in data:
        item_description = d['item_description']
        new_dict = {'item_description': item_description}
        
        # 動態填入各月份的數值
        for month in target_months:
             # pandas pivot 可能產生 NaN，需轉為 0
            val = d.get(month, 0)
            if pd.isna(val):
                val = 0
            new_dict[month] = int(val)
            
        new_data.append(new_dict)

    # 回傳統計資料給前端
    # 根據最新月份(target_months[0])的數量進行排序
    if target_months:
        newest_month = target_months[0]
        new_data.sort(key=lambda x: x.get(newest_month, 0), reverse=True)

    return jsonify(new_data)