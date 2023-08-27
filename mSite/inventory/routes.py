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
@inventory.route('/inventory_stat', methods=['GET'])
def get_statistics():
    query = text('''
    select `year_month` as 'year_month' ,`item_description` as 'item_description',sum(quantity) as 'quantity'   from mSite.inventory_details
    where `status`= '2'  and `year_month` in ('2023-05','2023-06','2023-07')
    group by `year_month`,`item_description`
    order by sum(quantity) desc
    ''')
    result = db.session.execute(query)

    # 將結果轉換為 DataFrame
    df = pd.DataFrame(result, columns=['year_month', 'item_description', 'quantity'])

    # 以 item 作為索引，將 yymm 和 quantity 轉換為列
    df_pivot = df.pivot(index='item_description', columns='year_month', values='quantity')

    # 將 DataFrame 轉換為列表格式
    data = df_pivot.reset_index().to_dict(orient='records')
 
    new_data = []
    for d in data:
        item_description = d['item_description']
        value_2023_05 = d['2023-05'] if not pd.isna(d['2023-05']) else '0'
        value_2023_06 = d['2023-06'] if not pd.isna(d['2023-06']) else '0'
        value_2023_07 = d['2023-07'] if not pd.isna(d['2023-07']) else '0'

        new_dict = {'item_description': item_description, 
                    '2023-05': int(value_2023_05),
                    '2023-06': int(value_2023_06),
                    '2023-07': int(value_2023_07),
                    }
        new_data.append(new_dict)

    # 回傳統計資料給前端
    return jsonify(new_data)